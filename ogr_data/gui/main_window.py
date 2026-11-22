"""Main window of OGR Data: criterion-driven sidebar + two plots."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
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
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core import criteria_envelopes as ce
from ..core.hoek_brown import HbInput, compute
from ..core.models import CRITERIA, Criterion, defaults
from .plots import EnvelopeCanvas


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OGR Data")
        self.resize(1150, 640)

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

        self._principal = EnvelopeCanvas("Principal Stresses", "sigma3 (MPa)", "sigma1 (MPa)")
        self._shear = EnvelopeCanvas("Shear - Normal Stresses", "normal stress (MPa)", "shear stress (MPa)")

        plots = QSplitter(Qt.Orientation.Horizontal)
        plots.addWidget(self._principal)
        plots.addWidget(self._shear)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(plots)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._rebuild_form()
        self.refresh()

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

    # --------------------------------------------------------------- refresh

    def refresh(self) -> None:
        key = self._criterion_combo.currentData()
        if key is None or not self._widgets:
            return
        params = self._params()
        sig3max = self._sig3max.value()
        crit = CRITERIA[key]

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
            self._principal.redraw(sig3, sig1)
            self._shear.redraw(normal, shear)

            # Overlay of the equivalent/best-fit MC line where defined.
            if key == "generalized_hoek_brown":
                inp = HbInput(
                    sigci=float(params["sigci"]) / 1000.0,
                    gsi=float(params["gsi"]),
                    mi=float(params["mi"]),
                    disturbance=float(params["d"]),
                    sig3max=sig3max,
                )
                result = compute(inp)
                (p3, p1), (n_mc, s_mc) = ce.mc_line(result.mc.cohesion, result.mc.friction_deg, sig3max)
                self._principal.redraw(sig3, sig1, p3, p1)
                self._shear.redraw(normal, shear, n_mc, s_mc)
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
            return

        # shear-space criteria
        curve = ce.shear_curve(key, params, sig3max)
        if curve is None:
            return
        normal, shear = curve
        self._principal.redraw([], [])
        self._shear.redraw(normal, shear)
        self._outputs.setText("")
