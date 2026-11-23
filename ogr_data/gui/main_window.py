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

from ..core import criteria_envelopes as ce
from ..core import samplers
from ..core.hoek_brown import HbInput, compute, equivalent_mc, hoek_brown_constants
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
        self._criterion_combo.currentIndexChanged.connect(self.refresh)

        self._sig3max = QDoubleSpinBox()
        self._sig3max.setRange(0.01, 1000000.0)
        self._sig3max.setValue(7.5)
        self._sig3max.setSingleStep(0.5)
        self._sig3max.setSuffix(" MPa")
        self._sig3max.valueChanged.connect(self.refresh)

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
        sidebar.addWidget(QLabel("sig3max (envelope range)"))
        sidebar.addWidget(self._sig3max)
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

        self._principal = EnvelopeCanvas("Principal Stresses", "sigma3 (MPa)", "sigma1 (MPa)", self._theme, space="principal")
        self._shear = EnvelopeCanvas("Shear - Normal Stresses", "normal stress (MPa)", "shear stress (MPa)", self._theme, space="shear")
        for canvas in (self._principal, self._shear):
            canvas.sampler_handler = self._on_plot_event

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

        help_menu = bar.addMenu("Help")
        help_menu.addAction("About OGR Data", self._about)

    def _set_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication

        self._theme = name
        self._settings.setValue("theme", name)
        apply_theme(QApplication.instance(), name)
        for canvas in (self._principal, self._shear):
            canvas.apply_theme(name)

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
            sig3max=self._sig3max.value(),
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
            project.save_project(path, self._material_name(), self._criterion_combo.currentData(), self._params(), self._sig3max.value())
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
        self._apply_project(data["criterion"], data["parameters"], data.get("sig3max_mpa"))
        self._name_edit.setText(data.get("name", ""))

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
        for key, value in parameters.items():
            if key in self._widgets and isinstance(self._widgets[key], QDoubleSpinBox):
                self._widgets[key].setValue(float(value))
        if sig3max_mpa is not None:
            self._sig3max.setValue(float(sig3max_mpa))

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
                widget.setValue(float(field.default))
                if field.unit == "deg":
                    widget.setSuffix(" deg")
                elif field.unit == "kPa":
                    widget.setSuffix(" kPa")
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
            else:
                params[field.key] = widget.value()
        return params

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
        sig3max = self._sig3max.value()
        xr = np.linspace(0.0, sig3max, 2)
        if space == "principal":
            curve = self._curves["principal"]
            if curve is None:
                return
            sig3, sig1 = curve
            if self._sampler_mode == "stress":
                s = samplers.sample(sig3, sig1, x)
                text = f"sigma3 = {s.x:.4f} MPa   sigma1 = {s.y:.4f} MPa"
                if self._overlay_inst is not None:
                    text += f"   [MC] sigma1 = {self._mc_line_value(self._overlay_inst, s.x):.4f} MPa"
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
                    f"c = {inst.cohesion_mpa:.4f} MPa   phi = {inst.friction_deg:.2f} deg   "
                    f"sigma3 = {inst.point_x:.4f} MPa   sigma1 = {inst.point_y:.4f} MPa   "
                    f"sigma_n = {n_t:.4f} MPa   tau = {t_t:.4f} MPa"
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
            text = f"sigma_n = {s.x:.4f} MPa   tau = {s.y:.4f} MPa"
            if self._overlay_inst is not None:
                text += f"   [MC] tau = {self._mc_line_value(self._overlay_inst, s.x):.4f} MPa"
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
                f"c = {inst.cohesion_mpa:.4f} MPa   phi = {inst.friction_deg:.2f} deg   "
                f"sigma_n = {inst.point_x:.4f} MPa   tau = {inst.point_y:.4f} MPa"
            )
        self.statusBar().showMessage(text)

    # --------------------------------------------------------------- refresh

    def refresh(self) -> None:
        key = self._criterion_combo.currentData()
        if key is None or not self._widgets:
            return
        params = self._params()
        sig3max = self._sig3max.value()
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
                    f"sigt = {result.sigt:.4f} MPa\n"
                    f"sigc = {result.sigc:.4f} MPa\n"
                    f"sigcm= {result.sigcm:.4f} MPa\n"
                    f"c    = {result.mc.cohesion:.4f} MPa\n"
                    f"phi  = {result.mc.friction_deg:.2f} deg\n"
                    f"Erm  = {result.erm:.2f} MPa"
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
