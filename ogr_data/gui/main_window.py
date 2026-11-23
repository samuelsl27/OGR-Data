"""Main window of OGR Data: criterion-driven sidebar + two plots."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core import application
from ..core import criteria_envelopes as ce
from ..core import samplers
from ..core import units
from ..core.graph_options import PlotOptions
from ..core.hoek_brown import HbInput, compute, equivalent_mc, global_strength, hoek_brown_constants
from ..core.models import CRITERIA, Criterion, defaults
from .plots import EnvelopeCanvas
from .themes import THEMES, apply_theme


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OGR Data")
        self.resize(1150, 640)

        self._settings = QSettings("OpenGeoRock", "OGR-Data")
        self._theme = str(self._settings.value("theme", "light"))
        if self._theme not in THEMES:
            self._theme = "light"
        # spec 017: display stress unit (registry and clipboard stay in kPa)
        self._stress_unit = str(self._settings.value("stress_unit", units.DEFAULT_STRESS_UNIT))
        if self._stress_unit not in units.STRESS_FACTORS:
            self._stress_unit = units.DEFAULT_STRESS_UNIT
        # Spec 008: sampler / overlay state (created before the menus so the
        # toggled signals fired by setChecked find it in place).
        self._sampler_mode: str | None = None
        self._dragging = False
        self._curves: dict[str, tuple | None] = {"principal": None, "shear": None}
        self._d1_func = None
        self._overlay_inst: samplers.InstantaneousMC | None = None
        from PySide6.QtWidgets import QApplication

        apply_theme(QApplication.instance(), self._theme)
        self._create_menus()

        self._criterion_combo = QComboBox()
        for key, crit in CRITERIA.items():
            self._criterion_combo.addItem(crit.label, key)
        self._criterion_combo.currentIndexChanged.connect(self._rebuild_form)
        self._criterion_combo.currentIndexChanged.connect(self._update_application)
        self._criterion_combo.currentIndexChanged.connect(self.refresh)

        self._sig3max = QDoubleSpinBox()
        self._sig3max.setRange(0.00001, 1000000000.0)
        self._sig3max.setDecimals(4)
        self._sig3max.setValue(7.5 * self._scale())
        self._sig3max.setSingleStep(0.5 * self._scale())
        self._sig3max.setSuffix(f" {self._stress_unit}")
        self._sig3max.valueChanged.connect(self.refresh)

        # spec 009: sigma3max by application (tunnel / slope)
        self._application_combo = QComboBox()
        for label, app_key in (("Custom", "custom"), ("Tunnel", "tunnel"), ("Slope", "slope")):
            self._application_combo.addItem(label, app_key)
        self._application_combo.currentIndexChanged.connect(self._update_application)
        self._unit_weight = QDoubleSpinBox()
        self._unit_weight.setRange(0.0001, 1.0)
        self._unit_weight.setDecimals(4)
        self._unit_weight.setValue(0.026)
        self._unit_weight.setSingleStep(0.001)
        self._unit_weight.setSuffix(" MN/m3")
        self._unit_weight.valueChanged.connect(self.refresh)
        self._app_depth = QDoubleSpinBox()
        self._app_depth.setRange(0.1, 10000.0)
        self._app_depth.setValue(50.0)
        self._app_depth.setSuffix(" m")
        self._app_depth.valueChanged.connect(self.refresh)
        self._app_fields = QWidget()
        app_form = QFormLayout(self._app_fields)
        app_form.setContentsMargins(0, 0, 0, 0)
        self._depth_label = QLabel("Tunnel depth")
        app_form.addRow("Unit weight", self._unit_weight)
        app_form.addRow(self._depth_label, self._app_depth)
        self._app_fields.setVisible(False)

        self._form_box = QGroupBox("Parameters")
        self._form_layout = QFormLayout(self._form_box)
        self._widgets: dict[str, object] = {}

        self._outputs = QLabel()
        self._outputs.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._outputs.setMinimumWidth(280)
        self._outputs.setStyleSheet("font-family: Consolas, monospace;")

        sidebar = QVBoxLayout()
        sidebar.addWidget(QLabel("Failure criterion"))
        sidebar.addWidget(self._criterion_combo)
        self._classifier_button = QPushButton("Soil classifier (USCS)…")
        self._classifier_button.clicked.connect(self._open_classifier)
        sidebar.addWidget(self._classifier_button)
        self._fit_button = QPushButton("Fit lab data…")
        self._fit_button.clicked.connect(self._open_fit_dialog)
        sidebar.addWidget(self._fit_button)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Material name")
        sidebar.addWidget(self._name_edit)
        # spec 017: display stress unit and project title
        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel("Stress unit"))
        self._unit_combo = QComboBox()
        for unit_name in units.STRESS_FACTORS:
            self._unit_combo.addItem(unit_name)
        self._unit_combo.setCurrentText(self._stress_unit)
        unit_row.addWidget(self._unit_combo)
        sidebar.addLayout(unit_row)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Project title")
        self._title_edit.textChanged.connect(self._update_window_title)
        sidebar.addWidget(self._title_edit)
        copy_row = QHBoxLayout()
        copy_material = QPushButton("Copy material")
        copy_material.clicked.connect(self._copy_material)
        copy_data = QPushButton("Copy data")
        copy_data.clicked.connect(self._copy_data)
        copy_image = QPushButton("Copy plot")
        copy_image.clicked.connect(self._copy_plot_image)
        copy_row.addWidget(copy_material)
        copy_row.addWidget(copy_data)
        copy_row.addWidget(copy_image)
        sidebar.addLayout(copy_row)
        file_row = QHBoxLayout()
        save_button = QPushButton("Save…")
        save_button.clicked.connect(self._save_project)
        load_button = QPushButton("Load…")
        load_button.clicked.connect(self._load_project)
        import_button = QPushButton("Import .roc…")
        import_button.clicked.connect(self._import_roc)
        file_row.addWidget(save_button)
        file_row.addWidget(load_button)
        file_row.addWidget(import_button)
        sidebar.addLayout(file_row)
        sidebar.addWidget(QLabel("Application (sigma3max range)"))
        sidebar.addWidget(self._application_combo)
        self._sig3max_label = QLabel("sig3max (envelope range)")
        sidebar.addWidget(self._sig3max_label)
        sidebar.addWidget(self._sig3max)
        sidebar.addWidget(self._app_fields)
        sidebar.addWidget(self._form_box)
        sidebar.addWidget(QLabel("Computed"))
        sidebar.addWidget(self._outputs, stretch=1)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(360)
        scroll = QScrollArea()
        scroll.setWidget(sidebar_widget)
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(380)

        self._principal = EnvelopeCanvas("Principal Stresses", f"sigma3 ({self._stress_unit})", f"sigma1 ({self._stress_unit})", self._theme, space="principal")
        self._shear = EnvelopeCanvas("Shear - Normal Stresses", f"normal stress ({self._stress_unit})", f"shear stress ({self._stress_unit})", self._theme, space="shear")
        for canvas in (self._principal, self._shear):
            canvas.sampler_handler = self._on_plot_event
            canvas.menu_handler = self._on_canvas_menu

        plots = QSplitter(Qt.Orientation.Horizontal)
        plots.addWidget(self._principal)
        plots.addWidget(self._shear)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(plots)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self.statusBar()

        self._rebuild_form()
        self._overlay_mc_act.setChecked(True)
        self._unit_combo.currentTextChanged.connect(self._set_stress_unit)
        self.refresh()

    # ----------------------------------------------------------------- menus

    def _create_menus(self) -> None:
        bar = QMenuBar(self)
        self.setMenuBar(bar)

        file_menu = bar.addMenu("File")
        file_menu.addAction("Save…", self._save_project)
        file_menu.addAction("Load…", self._load_project)
        file_menu.addAction("Import .roc…", self._import_roc)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        edit_menu = bar.addMenu("Edit")
        edit_menu.addAction("Copy material", self._copy_material)
        edit_menu.addAction("Copy data", self._copy_data)

        analysis_menu = bar.addMenu("Analysis")
        self._stress_sampler_act = QAction("Stress Sampler", self, checkable=True)
        self._mc_sampler_act = QAction("Instantaneous MC Sampler", self, checkable=True)
        sampler_group = QActionGroup(self)
        sampler_group.setExclusive(True)
        sampler_group.addAction(self._stress_sampler_act)
        sampler_group.addAction(self._mc_sampler_act)
        analysis_menu.addAction(self._stress_sampler_act)
        analysis_menu.addAction(self._mc_sampler_act)
        analysis_menu.addSeparator()
        self._overlay_mc_act = QAction("Overlay MC Envelope", self, checkable=True)
        self._overlay_mogi_act = QAction("Overlay Mogi Line", self, checkable=True)
        analysis_menu.addAction(self._overlay_mc_act)
        analysis_menu.addAction(self._overlay_mogi_act)
        self._stress_sampler_act.toggled.connect(self._sampler_mode_changed)
        self._mc_sampler_act.toggled.connect(self._sampler_mode_changed)
        self._overlay_mc_act.toggled.connect(self.refresh)
        self._overlay_mogi_act.toggled.connect(self.refresh)

        view_menu = bar.addMenu("View")
        theme_menu = view_menu.addMenu("Theme")
        for name in THEMES:
            theme_menu.addAction(name.capitalize(), lambda _=False, n=name: self._set_theme(n))
        view_menu.addSeparator()
        view_menu.addAction("Graph Editor…", self._open_graph_editor)

        help_menu = bar.addMenu("Help")
        help_menu.addAction("About OGR Data", self._about)

    def _set_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication

        self._theme = name
        self._settings.setValue("theme", name)
        apply_theme(QApplication.instance(), name)
        for canvas in (self._principal, self._shear):
            canvas.apply_theme(name)

    # ---------------------------------------------------------- spec 017: display units

    def _scale(self) -> float:
        """Display factor for MPa-internal values: display = MPa * scale."""

        return units.stress_factor(self._stress_unit)

    def _kpa_scale(self) -> float:
        """Display factor for registry (kPa) values: display = kPa * scale."""

        return units.stress_factor(self._stress_unit) / 1000.0

    def _sig3max_mpa(self) -> float:
        """Envelope range in internal MPa."""

        return units.from_display(self._sig3max.value(), self._stress_unit)

    def _update_window_title(self) -> None:
        title = self._title_edit.text().strip()
        self.setWindowTitle(f"OGR Data - {title}" if title else "OGR Data")

    def _set_plot_labels(self) -> None:
        u = self._stress_unit
        self._principal.set_axes_labels(f"sigma3 ({u})", f"sigma1 ({u})")
        self._shear.set_axes_labels(f"normal stress ({u})", f"shear stress ({u})")

    def _set_stress_unit(self, unit: str) -> None:
        """Switch the display unit, rescaling widgets in place (spec 017).

        Internal values are untouched: the registry stays in kPa and
        sigma3max in MPa; only the displayed numbers and labels change.
        """

        if unit == self._stress_unit or unit not in units.STRESS_FACTORS:
            return
        old_scale = self._scale()
        self._stress_unit = unit
        self._settings.setValue("stress_unit", unit)
        ratio = self._scale() / old_scale
        for field in self._criterion().fields:
            widget = self._widgets.get(field.key)
            if field.kind == "float" and field.unit == "kPa" and isinstance(widget, QDoubleSpinBox):
                widget.blockSignals(True)
                widget.setValue(widget.value() * ratio)
                widget.setSuffix(f" {unit}")
                widget.blockSignals(False)
        self._sig3max.blockSignals(True)
        self._sig3max.setValue(self._sig3max.value() * ratio)
        self._sig3max.setSuffix(f" {unit}")
        self._sig3max.blockSignals(False)
        self._set_plot_labels()
        self.refresh()

    # ---------------------------------------------------------- spec 016: graph options and export

    def _open_graph_editor(self) -> None:
        from .graph_editor import GraphEditorDialog

        GraphEditorDialog(self).exec()

    def _on_canvas_menu(self, canvas, kind: str) -> None:
        from PySide6.QtWidgets import QApplication, QFileDialog

        if kind == "copy":
            QApplication.clipboard().setPixmap(canvas.grab())
        elif kind == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save graph as image", "", "PNG image (*.png);;JPEG image (*.jpg);;BMP image (*.bmp)"
            )
            if path:
                canvas.save_image(path)
        elif kind == "export":
            self._export_canvas_csv(canvas)
        elif kind == "zoom":
            canvas.zoom_extents()
        elif kind == "editor":
            self._open_graph_editor()

    def _export_canvas_csv(self, canvas) -> None:
        """Export the plot series to CSV, ready to open in Excel (spec 016)."""

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ..core import export as series_export

        path, _ = QFileDialog.getSaveFileName(self, "Export graph to CSV", "", "CSV (*.csv)")
        if not path:
            return
        if not path.endswith(".csv"):
            path += ".csv"
        series = canvas.series_data()
        if canvas.space == "principal":
            labels = {
                "envelope": ("sigma3", "sigma1"),
                "mc": ("MC sigma3", "MC sigma1"),
                "mogi": ("Mogi sigma3", "Mogi sigma1"),
            }
        else:
            labels = {
                "envelope": ("sigma_n", "tau"),
                "mc": ("MC sigma_n", "MC tau"),
            }
        scale = self._scale()
        columns = []
        for key, (x_label, y_label) in labels.items():
            data = series.get(key)
            if data is not None:
                columns.append((x_label, y_label, data[0] * scale, data[1] * scale))
        if not columns:
            QMessageBox.information(self, "Export", "There is no series to export on this plot.")
            return
        series_export.write_series_csv(path, columns, unit=self._stress_unit)

    def _about(self) -> None:
        from .. import __version__

        QMessageBox.about(
            self,
            "About OGR Data",
            f"<b>OGR Data</b> {__version__}<br/>"
            "Rock and soil material properties for the OpenGeoRock suite.<br/>"
            "Design language: OGR-Slip2D (QGIS-inspired).",
        )


    def _open_classifier(self) -> None:
        from .soil_classifier import SoilClassifierDialog

        SoilClassifierDialog(self).exec()

    def _open_fit_dialog(self) -> None:
        from .fit_dialog import FitDialog

        FitDialog(self).exec()

    def apply_fit_parameters(self, result) -> None:
        """Fill the parameter form from a FitResult (spec 006)."""

        from ..core.fitting import DIRECT, TRIAXIAL

        mapping: dict[str, tuple[str, dict[str, float]]] = {
            # criterion to select -> {fit parameter: form field}
            "mohr_coulomb": (
                "mohr_coulomb",
                {"cohesion_mpa": ("peak_cohesion", 1000.0), "friction_deg": ("peak_friction", 1.0)},
            ),
            "hoek_brown": (
                "hoek_brown",
                {"sigci_mpa": ("compressive_strength", 1000.0), "mi": ("mb", 1.0)},
            ),
            "generalized_hoek_brown": (
                "hoek_brown",
                {"mb": ("mb", 1.0), "s": ("s", 1.0)},
            ),
            "barton_bandis": (
                "barton_bandis",
                {"jrc": ("jrc", 1.0), "jcs_mpa": ("jcs", 1000.0)},
            ),
            "power_curve": (
                "power_curve",
                {"a": ("a", 1.0), "b": ("b", 1.0), "d_mpa": ("d", 1000.0)},
            ),
        }
        target, fields = mapping[result.criterion]
        idx = self._criterion_combo.findData(target)
        if idx >= 0:
            self._criterion_combo.setCurrentIndex(idx)
        self._rebuild_form()
        for fit_key, (field_key, scale) in fields.items():
            if fit_key in result.parameters and field_key in self._widgets:
                self._widgets[field_key].setValue(result.parameters[fit_key] * scale)
        if target == "hoek_brown" and result.criterion == "hoek_brown":
            if "s" in self._widgets:
                self._widgets["s"].setValue(1.0)
        if target == "barton_bandis" and "phi_r" in self._widgets and result.fixed:
            if "phi_b_deg" in result.fixed:
                self._widgets["phi_r"].setValue(result.fixed["phi_b_deg"])

    # ------------------------------------------------------------- clipboard

    def _material_name(self) -> str:
        name = self._name_edit.text().strip()
        return name or self._criterion().label

    def _ghb_computed(self) -> dict[str, float]:
        key = self._criterion_combo.currentData()
        if key != "generalized_hoek_brown":
            return {}
        params = self._params()
        inp = HbInput(
            sigci=float(params["sigci"]) / 1000.0,
            gsi=float(params["gsi"]),
            mi=float(params["mi"]),
            disturbance=float(params["d"]),
            sig3max=self._sig3max_mpa(),
        )
        result = compute(inp)
        return {
            "mb": result.mb,
            "s": result.s,
            "a": result.a,
            "sigt_mpa": result.sigt,
            "sigc_mpa": result.sigc,
            "sigcm_mpa": result.sigcm,
            "c_mpa": result.mc.cohesion,
            "phi_deg": result.mc.friction_deg,
            "erm_mpa": result.erm,
        }

    def _copy_material(self) -> None:
        from PySide6.QtWidgets import QApplication

        from ..core import clipboard

        key = self._criterion_combo.currentData()
        text = clipboard.material_text(
            self._material_name(), key, self._params(), self._ghb_computed()
        )
        QApplication.clipboard().setText(text)

    def _copy_data(self) -> None:
        from PySide6.QtWidgets import QApplication

        from ..core import clipboard

        key = self._criterion_combo.currentData()
        QApplication.clipboard().setText(
            clipboard.tabular_data(key, self._params(), self._ghb_computed())
        )

    def _copy_plot_image(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setPixmap(self._principal.grab())

    # ------------------------------------------------------------ projects

    def _save_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ..core import project

        path, _ = QFileDialog.getSaveFileName(self, "Save project", "", "OGR Data project (*.ogrdata)")
        if not path:
            return
        if not path.endswith(".ogrdata"):
            path += ".ogrdata"
        try:
            project.save_project(
                path,
                self._material_name(),
                self._criterion_combo.currentData(),
                self._params(),
                self._sig3max_mpa(),
                stress_unit=self._stress_unit,
                title=self._title_edit.text(),
                graph_options={
                    "principal": self._principal.options.to_dict(),
                    "shear": self._shear.options.to_dict(),
                },
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def _load_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ..core import project

        path, _ = QFileDialog.getOpenFileName(self, "Load project", "", "OGR Data project (*.ogrdata)")
        if not path:
            return
        try:
            data = project.load_project(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Load failed", str(exc))
            return
        self._load_settings_into_window(data)
        self._apply_project(data["criterion"], data["parameters"], data.get("sig3max_mpa"))
        self._name_edit.setText(data.get("name", ""))
        self._title_edit.setText(data.get("title", ""))
        for name, canvas in (("principal", self._principal), ("shear", self._shear)):
            raw = data.get("graph_options", {}).get(name)
            if raw:
                canvas.apply_options(PlotOptions.from_dict(raw))

    def _load_settings_into_window(self, data: dict) -> None:
        """Apply the display unit saved in the project (spec 017)."""

        stress_unit = data.get("stress_unit", units.DEFAULT_STRESS_UNIT)
        if stress_unit in units.STRESS_FACTORS:
            self._unit_combo.blockSignals(True)
            self._unit_combo.setCurrentText(stress_unit)
            self._unit_combo.blockSignals(False)
            self._set_stress_unit(stress_unit)

    def _import_roc(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ..core import roc_import

        path, _ = QFileDialog.getOpenFileName(self, "Import RocData file", "", "RocData (*.roc)")
        if not path:
            return
        try:
            roc = roc_import.parse_roc(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        self._apply_project(roc.criterion, roc.parameters, roc.sig3max_mpa)
        self._name_edit.setText(roc.title)

    def _apply_project(self, criterion: str, parameters: dict, sig3max_mpa: float | None) -> None:
        idx = self._criterion_combo.findData(criterion)
        if idx >= 0:
            self._criterion_combo.setCurrentIndex(idx)
        self._rebuild_form()
        field_units = {f.key: f.unit for f in CRITERIA[criterion].fields}
        for key, value in parameters.items():
            if key in self._widgets and isinstance(self._widgets[key], QDoubleSpinBox):
                scale = self._kpa_scale() if field_units.get(key) == "kPa" else 1.0
                self._widgets[key].setValue(float(value) * scale)
        if sig3max_mpa is not None:
            self._sig3max.setValue(float(sig3max_mpa) * self._scale())

    # ------------------------------------------------------------------ form

    def _criterion(self) -> Criterion:
        return CRITERIA[self._criterion_combo.currentData()]

    def _rebuild_form(self) -> None:
        while self._form_layout.rowCount():
            self._form_layout.removeRow(0)
        self._widgets = {}
        for field in self._criterion().fields:
            if field.kind == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(field.default))
                widget.toggled.connect(self.refresh)
            elif field.kind == "enum":
                widget = QComboBox()
                widget.addItems(field.options)
                widget.currentIndexChanged.connect(self.refresh)
            else:
                widget = QDoubleSpinBox()
                widget.setDecimals(6)
                widget.setRange(-1e9, 1e12)
                if field.unit == "kPa":
                    widget.setValue(float(field.default) * self._kpa_scale())
                else:
                    widget.setValue(float(field.default))
                if field.unit == "deg":
                    widget.setSuffix(" deg")
                elif field.unit == "kPa":
                    widget.setSuffix(f" {self._stress_unit}")
                widget.valueChanged.connect(self.refresh)
            self._widgets[field.key] = widget

            editor: QWidget = widget
            if field.pick:
                editor = QWidget()
                row = QHBoxLayout(editor)
                row.setContentsMargins(0, 0, 0, 0)
                row.addWidget(widget, stretch=1)
                pick_button = QPushButton("Pick…")
                pick_button.clicked.connect(lambda _=False, f=field, w=widget: self._pick(f, w))
                row.addWidget(pick_button)
            self._form_layout.addRow(field.label, editor)

    def _pick(self, field, widget: QDoubleSpinBox) -> None:
        from . import pickers

        picker = {
            "sigci_grades": pickers.sigci_picker,
            "mi_values": pickers.mi_picker,
            "gsi_chart": pickers.gsi_picker,
        }.get(field.pick)
        if picker is None:
            return
        value = picker(self)
        if value is not None:
            widget.setValue(value)

    def _params(self) -> dict:
        params = defaults(self._criterion_combo.currentData())
        for field in self._criterion().fields:
            widget = self._widgets[field.key]
            if field.kind == "bool":
                params[field.key] = widget.isChecked()
            elif field.kind == "enum":
                params[field.key] = widget.currentText()
            elif field.unit == "kPa":
                # spinbox shows the display unit; the registry stays in kPa
                params[field.key] = widget.value() / self._kpa_scale()
            else:
                params[field.key] = widget.value()
        return params

    # ---------------------------------------------------------- spec 009: sig3max by application

    def _rock_mass_strength_mpa(self, key: str, params: dict) -> float | None:
        """Global rock mass strength sigcm (MPa), for HB-family criteria only."""

        if key == "generalized_hoek_brown":
            inp = HbInput(
                sigci=float(params["sigci"]) / 1000.0,
                gsi=float(params["gsi"]),
                mi=float(params["mi"]),
                disturbance=float(params["d"]),
                sig3max=self._sig3max_mpa(),
            )
            return compute(inp).sigcm
        if key == "hoek_brown":
            sigci_mpa, mb, s, a = self._hb_terms(key, params, self._sig3max_mpa())
            inp = HbInput(sigci=sigci_mpa, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=self._sig3max_mpa())
            return global_strength(inp, mb, s, a)
        return None

    def _application_sig3max(self) -> float | None:
        """sigma3max from the application mode, or None for manual (custom)."""

        mode = self._application_combo.currentData()
        if mode == "custom":
            return None
        key = self._criterion_combo.currentData()
        sigcm = self._rock_mass_strength_mpa(key, self._params())
        if sigcm is None or sigcm <= 0.0:
            return None
        if mode == "tunnel":
            return application.sig3max_tunnel(sigcm, self._unit_weight.value(), self._app_depth.value())
        return application.sig3max_slope(sigcm, self._unit_weight.value(), self._app_depth.value())

    def _update_application(self) -> None:
        key = self._criterion_combo.currentData()
        mode = self._application_combo.currentData()
        if mode != "custom" and key not in ("generalized_hoek_brown", "hoek_brown"):
            # sig3max by application needs sigcm (HB family only, as ORMAS)
            self._application_combo.blockSignals(True)
            self._application_combo.setCurrentIndex(0)
            self._application_combo.blockSignals(False)
            mode = "custom"
        custom = mode == "custom"
        self._sig3max.setEnabled(custom)
        self._sig3max_label.setVisible(custom)
        self._app_fields.setVisible(not custom)
        self._depth_label.setText("Tunnel depth" if mode == "tunnel" else "Slope height")
        self._apply_application()
        self.refresh()

    def _apply_application(self) -> None:
        value = self._application_sig3max()
        if value is None:
            return
        if abs(value - self._sig3max_mpa()) > 1e-12:
            self._sig3max.blockSignals(True)
            self._sig3max.setValue(units.to_display(value, self._stress_unit))
            self._sig3max.blockSignals(False)

    # ---------------------------------------------------------- spec 008: overlays and samplers

    def _hb_terms(self, key: str, params: dict, sig3max: float) -> tuple[float, float, float, float]:
        """(sigci_mpa, mb, s, a) of a Hoek-Brown criterion for the current inputs."""

        if key == "generalized_hoek_brown":
            inp = HbInput(
                sigci=float(params["sigci"]) / 1000.0,
                gsi=float(params["gsi"]),
                mi=float(params["mi"]),
                disturbance=float(params["d"]),
                sig3max=sig3max,
            )
            mb, s, a = hoek_brown_constants(inp)
            return inp.sigci, mb, s, a
        # classic Hoek-Brown is the 2002 criterion with a = 0.5
        return float(params["compressive_strength"]) / 1000.0, float(params["mb"]), float(params["s"]), 0.5

    def _overlay_mc_params(self, key: str, params: dict, sig3max: float, normal, shear) -> samplers.InstantaneousMC | None:
        """Equivalent / best-fit MC overlay for curved criteria (RocData 2004 p. 10)."""

        if not self._overlay_mc_act.isChecked():
            return None
        if key in ("generalized_hoek_brown", "hoek_brown"):
            sigci_mpa, mb, s, a = self._hb_terms(key, params, sig3max)
            # Hoek (2002) closed form over [0, sig3max], anchored on sigcm;
            # only sigci and sig3max of inp are used by the formulation.
            inp = HbInput(sigci=sigci_mpa, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max)
            mc = equivalent_mc(inp, mb, s, a)
            return samplers.InstantaneousMC(mc.cohesion, mc.friction_deg, 0.0, 0.0, 0.0)
        if key in ("power_curve", "barton_bandis") and normal is not None:
            return samplers.best_fit_mc(normal, shear)
        return None

    def _sampler_mode_changed(self) -> None:
        if self._stress_sampler_act.isChecked():
            self._sampler_mode = "stress"
        elif self._mc_sampler_act.isChecked():
            self._sampler_mode = "mc"
        else:
            self._sampler_mode = None
        if self._sampler_mode is None:
            self._clear_sampler_marks()
            self.statusBar().clearMessage()

    def _clear_sampler_marks(self) -> None:
        self._principal.clear_sample()
        self._shear.clear_sample()

    def _on_plot_event(self, space: str, kind: str, x: float) -> None:
        if self._sampler_mode is None:
            return
        if kind == "press":
            self._dragging = True
        elif kind == "release":
            self._dragging = False
            return
        elif kind == "move" and not self._dragging:
            return
        self._sample_at(space, x)

    @staticmethod
    def _mc_line_value(inst: samplers.InstantaneousMC, x: float) -> float:
        return inst.cohesion_mpa + x * math.tan(math.radians(inst.friction_deg))

    def _sample_at(self, space: str, x: float) -> None:
        sig3max = self._sig3max_mpa()
        xr = np.linspace(0.0, sig3max, 2)
        if space == "principal":
            curve = self._curves["principal"]
            if curve is None:
                return
            sig3, sig1 = curve
            if self._sampler_mode == "stress":
                s = samplers.sample(sig3, sig1, x)
                text = f"sigma3 = {units.stress_text(s.x, self._stress_unit)}   sigma1 = {units.stress_text(s.y, self._stress_unit)}"
                if self._overlay_inst is not None:
                    text += f"   [MC] sigma1 = {units.stress_text(self._mc_line_value(self._overlay_inst, s.x), self._stress_unit)}"
                self._principal.show_sample(s.x)
                self._shear.show_sample(s.x)
            else:
                slope = self._d1_func(x) if self._d1_func is not None else None
                inst = samplers.instantaneous_mc(sig3, sig1, x, slope=slope)
                t_principal = samplers.mc_tangent_principal(inst, xr)
                t_shear = samplers.mc_tangent_shear(inst, xr)
                # tangency point of the tangent Mohr circle on the shear plot
                sin_phi = math.sin(math.radians(inst.friction_deg))
                centre = (inst.point_y + inst.point_x) / 2.0
                radius = (inst.point_y - inst.point_x) / 2.0
                n_t = centre - radius * sin_phi
                t_t = radius * math.cos(math.radians(inst.friction_deg))
                self._principal.show_sample(inst.point_x, tangent=t_principal, marker=(inst.point_x, inst.point_y))
                self._shear.show_sample(n_t, tangent=t_shear, marker=(n_t, t_t))
                text = (
                    f"c = {units.stress_text(inst.cohesion_mpa, self._stress_unit)}   phi = {inst.friction_deg:.2f} deg   "
                    f"sigma3 = {units.stress_text(inst.point_x, self._stress_unit)}   sigma1 = {units.stress_text(inst.point_y, self._stress_unit)}   "
                    f"sigma_n = {units.stress_text(n_t, self._stress_unit)}   tau = {units.stress_text(t_t, self._stress_unit)}"
                )
            self.statusBar().showMessage(text)
            return

        # shear-space click
        curve = self._curves["shear"]
        if curve is None:
            return
        normal, shear = curve
        if self._sampler_mode == "stress":
            s = samplers.sample(normal, shear, x)
            text = f"sigma_n = {units.stress_text(s.x, self._stress_unit)}   tau = {units.stress_text(s.y, self._stress_unit)}"
            if self._overlay_inst is not None:
                text += f"   [MC] tau = {units.stress_text(self._mc_line_value(self._overlay_inst, s.x), self._stress_unit)}"
            self._shear.show_sample(s.x)
            if self._curves["principal"] is not None:
                self._principal.show_sample(s.x)
        else:
            inst = samplers.instantaneous_mc_shear(normal, shear, x)
            t_shear = samplers.mc_tangent_shear(inst, xr)
            self._shear.show_sample(inst.point_x, tangent=t_shear, marker=(inst.point_x, inst.point_y))
            # converted MC line in principal space (also for shear-space criteria)
            t_principal = samplers.mc_tangent_principal(inst, xr)
            self._principal.show_sample(None, tangent=t_principal)
            text = (
                f"c = {units.stress_text(inst.cohesion_mpa, self._stress_unit)}   phi = {inst.friction_deg:.2f} deg   "
                f"sigma_n = {units.stress_text(inst.point_x, self._stress_unit)}   tau = {units.stress_text(inst.point_y, self._stress_unit)}"
            )
        self.statusBar().showMessage(text)

    # --------------------------------------------------------------- refresh

    def refresh(self) -> None:
        key = self._criterion_combo.currentData()
        if key is None or not self._widgets:
            return
        params = self._params()
        self._apply_application()
        sig3max = self._sig3max_mpa()
        crit = CRITERIA[key]

        self._clear_sampler_marks()
        self._curves = {"principal": None, "shear": None}
        self._d1_func = None
        self._overlay_inst = None

        if crit.envelope == "none":
            self._principal.redraw([], [])
            self._shear.redraw([], [])
            self._outputs.setText("envelope not available for this criterion yet")
            return

        if crit.envelope == "principal":
            curve = ce.principal_curve(key, params, sig3max)
            if curve is None:
                return
            sig3, sig1 = curve
            normal, shear = ce.tangent_shear(sig3, sig1)
            self._curves["principal"] = (sig3, sig1)
            self._curves["shear"] = (normal, shear)
            if key in ("generalized_hoek_brown", "hoek_brown"):
                sigci_mpa, mb, s, a = self._hb_terms(key, params, sig3max)
                self._d1_func = lambda v, sc=sigci_mpa, m=mb, sv=s, av=a: samplers.hb_derivative(v, sc, m, sv, av)

            self._overlay_inst = self._overlay_mc_params(key, params, sig3max, normal, shear)
            if self._overlay_inst is not None:
                (p3, p1), (n_mc, s_mc) = ce.mc_line(
                    self._overlay_inst.cohesion_mpa, self._overlay_inst.friction_deg, sig3max
                )
                self._principal.redraw(sig3, sig1, p3, p1)
                self._shear.redraw(normal, shear, n_mc, s_mc)
            else:
                self._principal.redraw(sig3, sig1)
                self._shear.redraw(normal, shear)

            if key == "generalized_hoek_brown":
                inp = HbInput(
                    sigci=float(params["sigci"]) / 1000.0,
                    gsi=float(params["gsi"]),
                    mi=float(params["mi"]),
                    disturbance=float(params["d"]),
                    sig3max=sig3max,
                )
                result = compute(inp)
                self._outputs.setText(
                    f"mb   = {result.mb:.4f}\n"
                    f"s    = {result.s:.4f}\n"
                    f"a    = {result.a:.4f}\n"
                    f"sigt = {units.stress_text(result.sigt, self._stress_unit)}\n"
                    f"sigc = {units.stress_text(result.sigc, self._stress_unit)}\n"
                    f"sigcm= {units.stress_text(result.sigcm, self._stress_unit)}\n"
                    f"c    = {units.stress_text(result.mc.cohesion, self._stress_unit)}\n"
                    f"phi  = {result.mc.friction_deg:.2f} deg\n"
                    f"Erm  = {units.stress_text(result.erm, self._stress_unit, decimals=2)}"
                )
            else:
                self._outputs.setText("")
        else:
            # shear-space criteria
            curve = ce.shear_curve(key, params, sig3max)
            if curve is None:
                return
            normal, shear = curve
            self._curves["shear"] = (normal, shear)
            self._overlay_inst = self._overlay_mc_params(key, params, sig3max, normal, shear)
            if self._overlay_inst is not None:
                (p3, p1), (n_mc, s_mc) = ce.mc_line(
                    self._overlay_inst.cohesion_mpa, self._overlay_inst.friction_deg, sig3max
                )
                # the equivalent MC line is shown in both spaces
                self._principal.redraw([], [], p3, p1)
                self._shear.redraw(normal, shear, n_mc, s_mc)
            else:
                self._principal.redraw([], [])
                self._shear.redraw(normal, shear)
            self._outputs.setText("")

        if self._overlay_mogi_act.isChecked() and self._curves["principal"] is not None:
            self._principal.show_mogi(*samplers.mogi_line(sig3max))
        else:
            self._principal.clear_mogi()
