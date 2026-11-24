"""Graph editor dialog (spec 016): the RSData-style display options.

Edits the two envelope canvases: title and axis (title, label position,
manual or automatic ranges, square axis), graph display (grid) and
series display (visibility, color, width, style per series). Changes
apply live to the real canvases; Cancel restores the state at open.
"""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.graph_options import LINE_STYLES, SERIES_KEYS, PlotOptions, SeriesStyle
from .i18n import parse_number, tr
from .number_spin import NumberSpinBox
from .themes import mpl_colors


def _t(text: str) -> str:
    """Marks an English text that is translated where it is shown (spec 024)."""

    return text


_STYLE_LABELS = {
    "envelope": _t("Envelope"),
    "mc": _t("Equivalent MC"),
    "tangent": _t("MC tangent (sampler)"),
    "mogi": _t("Mogi line"),
}

# combo values (shown translated, compared in English)
_STYLE_NAMES = [_t("default"), _t("solid"), _t("dashed"), _t("dash-dot"), _t("dotted")]


class GraphEditorDialog(QDialog):
    def __init__(self, window) -> None:
        super().__init__(window)
        self.setWindowTitle(tr("Graph Editor"))
        self.resize(520, 460)
        self._window = window
        self._canvases = [(tr("Principal Stress Plot"), window._principal), (tr("Normal/Shear Stress"), window._shear)]
        self._snapshot = {canvas: copy.deepcopy(canvas.options) for _, canvas in self._canvases}

        self._plot_list = QListWidget()
        for label, _ in self._canvases:
            self._plot_list.addItem(label)
        self._plot_list.currentRowChanged.connect(self._load_canvas)
        self._plot_list.setMaximumWidth(180)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_title_axis_tab(), tr("Title and Axis"))
        self._tabs.addTab(self._build_graph_display_tab(), tr("Graph Display"))
        self._tabs.addTab(self._build_series_tab(), tr("Series Display"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self._cancel)

        body = QSplitter()
        body.addWidget(self._plot_list)
        body.addWidget(self._tabs)
        layout = QVBoxLayout(self)
        layout.addWidget(body, stretch=1)
        layout.addWidget(buttons)

        self._plot_list.setCurrentRow(0)

    # ---------------------------------------------------------------- tabs

    def _build_title_axis_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title_box = QGroupBox(tr("Title"))
        title_form = QFormLayout(title_box)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText(tr("default plot title"))
        self._title_edit.textChanged.connect(self._apply)
        title_form.addRow(tr("Title:"), self._title_edit)
        layout.addWidget(title_box)

        axis_box = QGroupBox(tr("Axis Label Position"))
        axis_form = QFormLayout(axis_box)
        self._label_position = QComboBox()
        self._label_position.addItem(tr("Outside"), "Outside")
        self._label_position.addItem(tr("Inside"), "Inside")
        self._label_position.currentIndexChanged.connect(self._apply)
        axis_form.addRow(tr("X-Axis:"), self._label_position)
        axis_form.addRow(tr("Y-Axis:"), self._label_position)
        layout.addWidget(axis_box)

        range_box = QGroupBox(tr("Axis Range"))
        range_layout = QGridLayout(range_box)
        self._default_range = QCheckBox(tr("Use Default Axis Range"))
        self._default_range.setChecked(True)
        self._default_range.toggled.connect(self._apply)
        range_layout.addWidget(self._default_range, 0, 0, 1, 4)
        self._range_edits: dict[str, QLineEdit] = {}
        for row, axis in ((1, "x"), (2, "y")):
            range_layout.addWidget(QLabel(tr("{0}-Axis").format(axis.upper())), row, 0)
            range_layout.addWidget(QLabel(tr("Min:")), row, 1)
            lo = QLineEdit()
            lo.setMaximumWidth(80)
            lo.textChanged.connect(self._apply)
            range_layout.addWidget(lo, row, 2)
            range_layout.addWidget(QLabel(tr("Max:")), row, 3)
            hi = QLineEdit()
            hi.setMaximumWidth(80)
            hi.textChanged.connect(self._apply)
            range_layout.addWidget(hi, row, 4)
            self._range_edits[f"{axis}_lo"] = lo
            self._range_edits[f"{axis}_hi"] = hi
        self._square_axis = QCheckBox(tr("Use Square Axis"))
        self._square_axis.toggled.connect(self._apply)
        range_layout.addWidget(self._square_axis, 3, 0, 1, 4)
        layout.addWidget(range_box)
        layout.addStretch(1)
        return tab

    def _build_graph_display_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._grid = QCheckBox(tr("Show grid"))
        self._grid.toggled.connect(self._apply)
        layout.addWidget(self._grid)
        layout.addStretch(1)
        return tab

    def _build_series_tab(self) -> QWidget:
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.addWidget(QLabel(tr("Series")), 0, 0)
        grid.addWidget(QLabel("Visible"), 0, 1)  # i18n: ignore (same in Spanish)
        grid.addWidget(QLabel("Color"), 0, 2)  # i18n: ignore (same in Spanish)
        grid.addWidget(QLabel(tr("Width")), 0, 3)
        grid.addWidget(QLabel(tr("Style")), 0, 4)
        self._series_controls: dict[str, dict] = {}
        for row, key in enumerate(SERIES_KEYS, start=1):
            grid.addWidget(QLabel(tr(_STYLE_LABELS[key])), row, 0)  # i18n: ignore (keys marked with _t)
            visible = QCheckBox()
            visible.setChecked(True)
            visible.toggled.connect(self._apply)
            grid.addWidget(visible, row, 1)
            color = QPushButton("…")
            color.setFixedWidth(48)
            color.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            grid.addWidget(color, row, 2)
            width = NumberSpinBox()
            width.setRange(0.0, 10.0)
            width.setSingleStep(0.2)
            width.setSpecialValueText(tr("default"))
            width.valueChanged.connect(self._apply)
            grid.addWidget(width, row, 3)
            style = QComboBox()
            for name in _STYLE_NAMES:
                style.addItem(tr(name), name)  # i18n: ignore (keys marked with _t)
            style.currentIndexChanged.connect(self._apply)
            grid.addWidget(style, row, 4)
            self._series_controls[key] = {
                "visible": visible,
                "color": color,
                "width": width,
                "style": style,
            }
        return tab

    # ------------------------------------------------------------ plumbing

    def _canvas(self):
        return self._canvases[self._plot_list.currentRow()][1]

    def _load_canvas(self) -> None:
        canvas = self._canvas()
        options = canvas.options
        self._loading = True
        try:
            self._title_edit.setText(options.title)
            self._label_position.setCurrentIndex(self._label_position.findData("Inside" if options.labels_inside else "Outside"))
            self._default_range.setChecked(options.x_range is None and options.y_range is None)
            # ranges are stored in internal MPa and edited in the display unit
            k = getattr(canvas, "display_scale", 1.0)
            for axis, rng in (("x", options.x_range), ("y", options.y_range)):
                self._range_edits[f"{axis}_lo"].setText("" if rng is None else f"{rng[0] * k:g}")
                self._range_edits[f"{axis}_hi"].setText("" if rng is None else f"{rng[1] * k:g}")
            self._square_axis.setChecked(options.square_axis)
            self._grid.setChecked(options.grid)
            theme_colors = mpl_colors(canvas._theme)
            default_colors = {
                "envelope": getattr(canvas, "material_color", "") or theme_colors["envelope"],
                "mc": theme_colors["mc"],
                "tangent": theme_colors["point"],
                "mogi": theme_colors["mogi"],
            }
            for key, controls in self._series_controls.items():
                style = options.styles[key]
                controls["visible"].setChecked(style.visible)
                controls["width"].setValue(style.linewidth)
                controls["style"].setCurrentIndex(
                    controls["style"].findData(_STYLE_NAMES[LINE_STYLES.index(style.linestyle)] if style.linestyle else "default")
                )
                self._set_color_button(controls["color"], style.color or default_colors[key], style.color)
        finally:
            self._loading = False

    def _set_color_button(self, button: QPushButton, shown: str, value: str) -> None:
        """Show `shown`; store `value` ("" keeps the theme / material default)."""

        button.setStyleSheet(f"background-color: {shown};")
        button.setProperty("color_value", value)
        button.setProperty("color_shown", shown)

    def _pick_color(self, key: str) -> None:
        controls = self._series_controls[key]
        current = controls["color"].property("color_shown") or "#4a90d9"
        chosen = QColorDialog.getColor(QColor(current), self, tr("{0} color").format(tr(_STYLE_LABELS[key])))  # i18n: ignore (_t keys)
        if chosen.isValid():
            self._set_color_button(controls["color"], chosen.name(), chosen.name())
            self._apply()

    def _range_from(self, axis: str):
        if self._default_range.isChecked():
            return None
        try:
            lo = parse_number(self._range_edits[f"{axis}_lo"].text())
            hi = parse_number(self._range_edits[f"{axis}_hi"].text())
        except ValueError:
            return None
        k = getattr(self._canvas(), "display_scale", 1.0)
        lo, hi = lo / k, hi / k
        return (lo, hi) if lo < hi else None

    def _apply(self) -> None:
        if getattr(self, "_loading", False):
            return
        canvas = self._canvas()
        styles = {}
        for key, controls in self._series_controls.items():
            style_name = controls["style"].currentData()
            styles[key] = SeriesStyle(
                visible=controls["visible"].isChecked(),
                color=controls["color"].property("color_value") or "",
                linewidth=controls["width"].value(),
                linestyle=LINE_STYLES[_STYLE_NAMES.index(style_name)] if style_name != "default" else "",
            )
        options = PlotOptions(
            title=self._title_edit.text().strip(),
            grid=self._grid.isChecked(),
            square_axis=self._square_axis.isChecked(),
            labels_inside=self._label_position.currentData() == "Inside",
            x_range=self._range_from("x"),
            y_range=self._range_from("y"),
            styles=styles,
        )
        canvas.apply_options(options)

    def _cancel(self) -> None:
        for canvas, snapshot in self._snapshot.items():
            canvas.apply_options(copy.deepcopy(snapshot))
        self.reject()

    def accept(self) -> None:
        self._apply()
        super().accept()
