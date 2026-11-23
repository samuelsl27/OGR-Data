"""Estimation of properties without tests (spec 022).

One-click selectors next to the GHB fields, as ORMAS (and the old RocData)
offer them; RSData hides them behind double-click buttons.

- GsiDialog: three tabs — the Hoek & Marinos (2000) chart selector of
  spec 003; the quantified chart of Hoek, Carter & Diederichs (2013,
  Fig. 5) redrawn from its equation GSI = 1.5 JCond89 + RQD/2 (click on it
  to read GSI); and the 2013 calculator (RQD direct / from lambda / from
  Jv; joint condition as JCond89, its Table 1 ratings, JCond76 or Jr/Ja).
- disturbance_picker: D guidelines (Practical Rock Engineering 2023, Fig. 9).
- modulus_ratio_picker: Ei = MR x sigci with the MR table (idem, Fig. 13).
"""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import gsi as qgsi
from ..core import tables
from .pickers import GsiPickerDialog
from .themes import mpl_colors


def _spin(lo: float, hi: float, value: float, decimals: int = 2, step: float = 1.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(lo, hi)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(value)
    return spin


# ------------------------------------------------------------------ GSI


class QuantifiedGsiChart(FigureCanvasQTAgg):
    """Hoek, Carter & Diederichs (2013) Fig. 5, redrawn: A = 1.5 JCond89 (45 -> 0), B = RQD/2."""

    def __init__(self, theme: str = "light", on_pick=None) -> None:
        self.figure = Figure(figsize=(6.4, 4.6), tight_layout=True)
        super().__init__(self.figure)
        self.on_pick = on_pick
        self.point: tuple[float, float] | None = None
        self.axes = self.figure.add_subplot(111)
        colors = mpl_colors(theme)
        self._colors = colors
        data = tables.gsi_quantified()["chart"]
        ax = self.axes
        self.figure.set_facecolor(colors["figure"])
        ax.set_facecolor(colors["figure"])
        ax.set_xlim(qgsi.CHART_A_MAX, 0.0)  # decreasing surface quality to the right
        ax.set_ylim(0.0, qgsi.CHART_B_MAX)
        ax.set_aspect("equal")  # isolines at 45 degrees, as in Fig. 5
        ax.set_xlabel("1.5 JCond89", color=colors["axes"])
        ax.set_ylabel("RQD/2", color=colors["axes"])
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.tick_params(colors=colors["axes"], labelcolor=colors["axes"])
        ax.grid(True, alpha=0.4, color=colors["grid"])
        # GSI isolines: A + B = GSI (eq. 1), every 10
        for value in range(10, 90, 10):
            xs = [max(0.0, value - qgsi.CHART_B_MAX), min(qgsi.CHART_A_MAX, float(value))]
            ys = [value - xs[0], value - xs[1]]
            ax.plot(xs, ys, color=colors["axes"], linewidth=0.9)
            # label near the upper-left end of each line
            lx = min(qgsi.CHART_A_MAX - 1.5, value - 2.0)
            ly = value - lx
            if 0.0 <= ly <= qgsi.CHART_B_MAX:
                ax.text(lx, ly, f"{value}", color=colors["axes"], fontsize=8, ha="center", va="center",
                        rotation=45, backgroundcolor=colors["figure"])
        # structure bands (Fig. 5 rows) and surface condition headings (columns)
        for row in data["rows"]:
            ax.axhline(row["y_lo"], color=colors["grid"], linewidth=1.2)
            ax.text(qgsi.CHART_A_MAX - 0.6, (row["y_lo"] + row["y_hi"]) / 2.0, row["label"], fontsize=7,
                    ha="left", va="center", color=colors["mc"], alpha=0.9)
        for column in data["columns"]:
            ax.text(column["x"], qgsi.CHART_B_MAX + 0.6, column["label"], fontsize=7, rotation=0,
                    ha="center", va="bottom", color=colors["mc"])
        (self._marker,) = ax.plot([], [], marker="o", color=colors["point"], markersize=8, linestyle="None")
        self.mpl_connect("button_press_event", self._click)

    def _click(self, event) -> None:
        if event.inaxes is not self.axes or event.xdata is None:
            return
        self.set_point(float(event.xdata), float(event.ydata))

    def set_point(self, a: float, b: float) -> float | None:
        value = qgsi.chart_gsi(a, b)
        if value is None:
            return None
        self.point = (a, b)
        self._marker.set_data([a], [b])
        self.draw_idle()
        if self.on_pick is not None:
            self.on_pick(a, b, value)
        return value


class GsiDialog(QDialog):
    """GSI: 2000 chart selector, quantified chart (2013) and calculator (2013)."""

    def __init__(self, parent=None, theme: str = "light") -> None:
        super().__init__(parent)
        self.setWindowTitle("Pick GSI")
        self.resize(820, 640)
        self.value: float | None = None
        self._tabs = QTabWidget()

        # 1. Hoek & Marinos (2000) selector (spec 003)
        self._chart2000 = GsiPickerDialog(self)
        self._chart2000.setWindowFlags(Qt.WindowType.Widget)  # embedded as a tab page
        for box in self._chart2000.findChildren(QDialogButtonBox):
            box.hide()
        for label in self._chart2000.findChildren(QLabel):
            label.setWordWrap(True)  # long source note
        for combo in (self._chart2000._structure, self._chart2000._surface):
            combo.currentIndexChanged.connect(self._update_result)
        self._chart2000._value.valueChanged.connect(self._update_result)
        self._tabs.addTab(self._chart2000, "Chart 2000 (Hoek && Marinos)")

        # 2. quantified chart (2013)
        chart_page = QWidget()
        chart_layout = QVBoxLayout(chart_page)
        self._chart = QuantifiedGsiChart(theme, on_pick=self._chart_picked)
        self._chart_label = QLabel("Click on the chart: GSI = 1.5 JCond89 + RQD/2 (Hoek, Carter & Diederichs 2013).")
        self._chart_label.setWordWrap(True)
        chart_layout.addWidget(self._chart, stretch=1)
        chart_layout.addWidget(self._chart_label)
        self._tabs.addTab(chart_page, "Quantified chart 2013")

        # 3. calculator (2013)
        self._tabs.addTab(self._build_calculator(), "Calculator 2013")
        self._tabs.currentChanged.connect(self._update_result)

        self._result = QLabel()
        source = tables.gsi_quantified()["source"]
        note = QLabel(f"Sources: Hoek & Marinos (2000); {source}")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 8pt;")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs, stretch=1)
        layout.addWidget(self._result)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self._update_result()

    # ---------------------------------------------------------- calculator

    def _build_calculator(self) -> QWidget:
        data = tables.gsi_quantified()
        page = QWidget()
        layout = QVBoxLayout(page)

        rqd_box = QGroupBox("RQD (%)")
        rqd_form = QFormLayout(rqd_box)
        self._rqd_mode = QComboBox()
        self._rqd_mode.addItems(["RQD from core logging", "From discontinuities per metre, lambda (eq. 4)", "From volumetric joint count Jv (eq. 6, Palmstrom 2005)", "From volumetric joint count Jv (eq. 5, Palmstrom 1982)"])
        self._rqd = _spin(0.0, 100.0, 30.0)
        self._lambda = _spin(0.0, 200.0, 10.0)
        self._jv = _spin(0.0, 100.0, 10.0)
        self._rqd_value = QLabel()
        rqd_form.addRow("Method", self._rqd_mode)
        rqd_form.addRow("RQD", self._rqd)
        rqd_form.addRow("lambda (1/m)", self._lambda)
        rqd_form.addRow("Jv (joints/m3)", self._jv)
        rqd_form.addRow("RQD used", self._rqd_value)
        self._rqd_form = rqd_form
        layout.addWidget(rqd_box)

        joint_box = QGroupBox("Joint condition")
        joint_layout = QVBoxLayout(joint_box)
        self._joint_mode = QComboBox()
        self._joint_mode.addItems(["JCond89 (eq. 1)", "JCond89 from Table 1 ratings (eq. 1)", "JCond76 (eq. 2)", "Jr / Ja (eq. 3)"])
        joint_layout.addWidget(self._joint_mode)
        self._joint_stack = QStackedWidget()
        # JCond89 direct, with the condition presets of Table 1
        page_j89 = QWidget()
        form = QFormLayout(page_j89)
        self._j89_preset = QComboBox()
        self._j89_preset.addItem("(enter value)", None)
        for c in data["jcond89_conditions"]:
            self._j89_preset.addItem(f'{c["rating"]}: {c["description"]}', c["rating"])
        self._j89 = _spin(0.0, 30.0, 10.0)
        self._j89_preset.currentIndexChanged.connect(lambda: self._j89.setValue(self._j89_preset.currentData()) if self._j89_preset.currentData() is not None else None)
        form.addRow("Condition", self._j89_preset)
        form.addRow("JCond89", self._j89)
        self._joint_stack.addWidget(page_j89)
        # JCond89 from the five guideline ratings
        page_ratings = QWidget()
        form = QFormLayout(page_ratings)
        self._ratings: dict[str, QComboBox] = {}
        for param in data["jcond89_parameters"]:
            combo = QComboBox()
            for label, rating in param["options"]:
                combo.addItem(f"{label}  ({rating})", rating)
            combo.currentIndexChanged.connect(self._update_result)
            self._ratings[param["key"]] = combo
            form.addRow(param["label"], combo)
        self._joint_stack.addWidget(page_ratings)
        # JCond76
        page_j76 = QWidget()
        form = QFormLayout(page_j76)
        self._j76_preset = QComboBox()
        self._j76_preset.addItem("(enter value)", None)
        for c in data["jcond76_conditions"]:
            self._j76_preset.addItem(f'{c["rating"]}: {c["description"]}', c["rating"])
        self._j76 = _spin(0.0, 25.0, 10.0)
        self._j76_preset.currentIndexChanged.connect(lambda: self._j76.setValue(self._j76_preset.currentData()) if self._j76_preset.currentData() is not None else None)
        form.addRow("Condition", self._j76_preset)
        form.addRow("JCond76", self._j76)
        self._joint_stack.addWidget(page_j76)
        # Jr / Ja
        page_q = QWidget()
        form = QFormLayout(page_q)
        self._jr = QComboBox()
        for label, value in data["jr"]:
            self._jr.addItem(f"{label}  ({value:g})", value)
        self._ja = QComboBox()
        for label, value in data["ja"]:
            self._ja.addItem(f"{value:g}: {label}", value)
        self._jr.setCurrentIndex(2)  # Smooth, undulating (2)
        self._ja.setCurrentIndex(1)  # Unaltered (1)
        form.addRow("Jr", self._jr)
        form.addRow("Ja", self._ja)
        self._joint_stack.addWidget(page_q)
        joint_layout.addWidget(self._joint_stack)
        layout.addWidget(joint_box)
        note = QLabel(data["rsdata_note"])
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 8pt;")
        layout.addWidget(note)
        layout.addStretch(1)

        self._joint_mode.currentIndexChanged.connect(self._joint_stack.setCurrentIndex)
        for widget in (self._rqd_mode, self._joint_mode, self._jr, self._ja):
            widget.currentIndexChanged.connect(self._update_result)
        for widget in (self._rqd, self._lambda, self._jv, self._j89, self._j76):
            widget.valueChanged.connect(self._update_result)
        return page

    def rqd(self) -> float:
        mode = self._rqd_mode.currentIndex()
        if mode == 1:
            return qgsi.rqd_from_lambda(self._lambda.value())
        if mode in (2, 3):
            return qgsi.rqd_from_jv(self._jv.value(), palmstrom_2005=mode == 2)
        return self._rqd.value()

    def calculator_gsi(self) -> tuple[float, str]:
        rqd = self.rqd()
        mode = self._joint_mode.currentIndex()
        if mode == 1:
            r = {k: c.currentData() for k, c in self._ratings.items()}
            j = qgsi.jcond89_from_ratings(r["persistence"], r["aperture"], r["roughness"], r["infilling"], r["weathering"])
            return qgsi.gsi_from_jcond89(j, rqd), f"JCond89 = {j:g} (sum of ratings); GSI = 1.5 x {j:g} + {rqd:.2f}/2"
        if mode == 2:
            j = self._j76.value()
            return qgsi.gsi_from_jcond76(j, rqd), f"GSI = 2 x {j:g} + {rqd:.2f}/2"
        if mode == 3:
            jr, ja = self._jr.currentData(), self._ja.currentData()
            return qgsi.gsi_from_jr_ja(jr, ja, rqd), f"Jr/Ja = {jr / ja:.3f}; GSI = 52 (Jr/Ja)/(1 + Jr/Ja) + {rqd:.2f}/2"
        j = self._j89.value()
        return qgsi.gsi_from_jcond89(j, rqd), f"GSI = 1.5 x {j:g} + {rqd:.2f}/2"

    # ------------------------------------------------------------ result

    def _chart_picked(self, a: float, b: float, value: float) -> None:
        row = qgsi.chart_row(b)
        self._chart_label.setText(
            f"1.5 JCond89 = {a:.1f} (JCond89 = {a / 1.5:.1f}), RQD/2 = {b:.1f} (RQD = {2 * b:.0f} %)"
            + (f" — {row['label']}" if row else "")
        )
        self._update_result()

    def _update_result(self) -> None:
        tab = self._tabs.currentIndex()
        if hasattr(self, "_rqd_value"):
            mode = self._rqd_mode.currentIndex()
            for widget, shown in ((self._rqd, mode == 0), (self._lambda, mode == 1), (self._jv, mode in (2, 3))):
                self._rqd_form.setRowVisible(widget, shown)
            self._rqd_value.setText(f"{self.rqd():.2f} %")
        text = ""
        if tab == 0:
            self.value = self._chart2000.gsi()
            text = "" if self.value is None else f"GSI = {self.value:.1f} (chart 2000)"
        elif tab == 1:
            self.value = None if self._chart.point is None else sum(self._chart.point)
            text = "Click on the chart." if self.value is None else f"GSI = {self.value:.1f}"
        else:
            self.value, formula = self.calculator_gsi()
            text = f"{formula} = {self.value:.2f}"
        self._result.setText(f"<b>{text}</b>")

    def accept(self) -> None:
        self._update_result()
        if self.value is not None:
            super().accept()


def gsi_dialog(parent=None, theme: str = "light") -> float | None:
    dlg = GsiDialog(parent, theme)
    return dlg.value if dlg.exec() == QDialog.DialogCode.Accepted else None


# -------------------------------------------------------------- tables


class FilteredTableDialog(QDialog):
    """Table with text search and combo filters; value() returns the row value."""

    def __init__(self, title: str, columns: list[str], rows: list[dict], value_key: str, filters: list[str], source: str, parent=None, extra: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 520)
        self._rows = rows
        self._value_key = value_key
        self._columns = columns
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.textChanged.connect(self._filter)
        self._filters: dict[str, QComboBox] = {}
        top = QHBoxLayout()
        top.addWidget(self._search, stretch=1)
        for key in filters:
            combo = QComboBox()
            combo.addItem(f"All ({key.replace('_', ' ')})", None)
            for value in sorted({str(r[key]) for r in rows if r.get(key)}):
                combo.addItem(value, value)
            combo.currentIndexChanged.connect(lambda _=0: self._filter(self._search.text()))
            self._filters[key] = combo
            top.addWidget(combo)
        self.table = QTableWidget(len(rows), len(columns))
        self.table.setHorizontalHeaderLabels([c for c in columns])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept)
        for i, row in enumerate(rows):
            for j, key in enumerate(columns):
                self.table.setItem(i, j, QTableWidgetItem("" if row.get(key) is None else str(row.get(key))))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table, stretch=1)
        if extra is not None:
            layout.addWidget(extra)
        src = QLabel(f"Source: {source}")
        src.setWordWrap(True)
        src.setStyleSheet("font-size: 8pt;")
        layout.addWidget(src)
        layout.addWidget(buttons)

    def _filter(self, text: str) -> None:
        words = text.lower().split()
        for i, row in enumerate(self._rows):
            visible = all(any(w in str(v).lower() for v in row.values()) for w in words)
            for key, combo in self._filters.items():
                if combo.currentData() is not None and str(row.get(key)) != combo.currentData():
                    visible = False
            self.table.setRowHidden(i, not visible)

    def visible_rows(self) -> int:
        return sum(not self.table.isRowHidden(i) for i in range(len(self._rows)))

    def selected(self) -> dict | None:
        row = self.table.currentRow()
        return None if row < 0 else self._rows[row]

    def value(self) -> float | None:
        row = self.selected()
        return None if row is None else float(row[self._value_key])


def mi_dialog(parent=None) -> FilteredTableDialog:
    data = tables.mi_values()
    rows = [{**v, "mi ± std": f'{v["mi"]} ± {v["std"]}' + (" (est.)" if v["estimated"] else "")} for v in data["values"]]
    return FilteredTableDialog(
        "Pick mi — Hoek-Brown constant for intact rock (Hoek, Table 3)",
        ["rock", "rock_type", "class", "group", "texture", "mi ± std"], rows, "mi", ["rock_type", "texture"],
        data["source"], parent,
    )


def mi_picker(parent=None) -> float | None:
    dlg = mi_dialog(parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None


def disturbance_dialog(parent=None) -> FilteredTableDialog:
    data = tables.disturbance_factor()
    return FilteredTableDialog(
        "Pick D — disturbance factor (Hoek, Practical Rock Engineering 2023, Fig. 9)",
        ["application", "case", "d", "description"], data["values"], "d", ["application"], data["source"], parent,
    )


def disturbance_picker(parent=None) -> float | None:
    dlg = disturbance_dialog(parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None


class ModulusRatioDialog(FilteredTableDialog):
    """Ei = MR x sigci: MR from the table (editable), sigci from the form (kPa)."""

    def __init__(self, sigci_kpa: float, unit: str = "kPa", parent=None) -> None:
        self._sigci_kpa = float(sigci_kpa)
        self._unit = unit
        extra = QWidget()
        form = QFormLayout(extra)
        self.mr = _spin(1.0, 5000.0, 450.0, decimals=1, step=10.0)
        self.ei_label = QLabel()
        form.addRow("MR (modulus ratio)", self.mr)
        form.addRow("Ei = MR x sigci", self.ei_label)
        data = tables.modulus_ratio()
        rows = [
            {**v, "MR range": f'{v["mr_lo"]:g}' + ("" if v["mr_hi"] is None else f'–{v["mr_hi"]:g}') + (" (est.)" if v["estimated"] else ""), "MR used": v["mr_pick"]}
            for v in data["values"]
        ]
        super().__init__(
            "Pick Ei — modulus ratio MR (Hoek, Practical Rock Engineering 2023, Fig. 13)",
            ["rock", "rock_type", "class", "group", "texture", "MR range", "MR used", "note"], rows, "MR used",
            ["rock_type", "texture"], f'{data["source"]} {data["notes"]}', parent, extra,
        )
        self.table.currentCellChanged.connect(self._row_changed)
        self.mr.valueChanged.connect(self._update_ei)
        self._update_ei()

    def _row_changed(self, row: int, *_args) -> None:
        if row >= 0:
            self.mr.setValue(float(self._rows[row]["mr_pick"]))

    def ei_kpa(self) -> float:
        return self.mr.value() * self._sigci_kpa

    def _update_ei(self) -> None:
        from ..core import units

        scale = units.stress_factor(self._unit) / 1000.0
        self.ei_label.setText(f"{self.ei_kpa() * scale:,.0f} {self._unit}")

    def value(self) -> float | None:  # Ei in kPa
        return self.ei_kpa()


def modulus_ratio_picker(sigci_kpa: float, unit: str = "kPa", parent=None) -> float | None:
    dlg = ModulusRatioDialog(sigci_kpa, unit, parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None
