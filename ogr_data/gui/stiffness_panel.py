"""Stiffness group of the sidebar (specs 013 and 013b).

RSData shows a Stiffness tab per material model: Linear Isotropic (Poisson's
Ratio, Young's Modulus) for most models, "CamClay Isotropic" (Elastic
Parameter: Constant Poisson Ratio / Constant Shear Modulus) for Cam-Clay and
Modified Cam-Clay, and the NorSand stiffness (Shear modulus at reference,
Reference pressure for shear modulus, Modulus exponent, Poisson's ratio,
Minimum Shear Modulus). Stresses are stored in kPa and shown in the display unit.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QPushButton, QWidget

from ..core import simulation as sm

# (key, label, is_stress, minimum, maximum, decimals)
_FIELDS = {
    "poisson": ("Poisson's Ratio", False, -0.99, 0.4999, 4),
    "young": ("Young's Modulus", True, 1e-9, 1e15, 4),
    "shear_modulus": ("Shear Modulus", True, 1e-9, 1e15, 4),
    "g_ref": ("Shear modulus at reference", True, 1e-9, 1e15, 4),
    "p_ref": ("Reference pressure for shear modulus", True, 1e-9, 1e12, 4),
    "g_exp": ("Modulus exponent", False, 0.0, 1.0, 4),
    "ns_poisson": ("Poisson's ratio", False, -0.99, 0.4999, 4),
    "g_min": ("Minimum Shear Modulus", True, 0.0, 1e15, 4),
}
_ROWS = {
    "linear": ("poisson", "young"),
    "camclay": ("elastic_parameter", "poisson", "shear_modulus"),
    "norsand": ("g_ref", "p_ref", "g_exp", "ns_poisson", "g_min"),
}


def stiffness_kind(criterion: str) -> str:
    if criterion in ("cam_clay", "modified_cam_clay"):
        return "camclay"
    if criterion == "norsand":
        return "norsand"
    return "linear"


class StiffnessPanel(QGroupBox):
    changed = Signal()

    def __init__(self, kpa_scale: float, unit: str, on_erm=None) -> None:
        super().__init__("Stiffness (Linear Isotropic)")
        self._scale = kpa_scale
        self._unit = unit
        self._kind = "linear"
        self.form = QFormLayout(self)
        self.spins: dict[str, QDoubleSpinBox] = {}
        self.elastic_parameter = QComboBox()
        self.elastic_parameter.addItems(sm.CAM_CLAY_ELASTIC)
        self.elastic_parameter.currentIndexChanged.connect(self._update_rows)
        self.elastic_parameter.currentIndexChanged.connect(self.changed)
        self.form.addRow("Elastic Parameter", self.elastic_parameter)
        for key, (label, stress, lo, hi, decimals) in _FIELDS.items():
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setDecimals(decimals)
            spin.setSingleStep(0.01 if not stress else 100.0)
            value = sm.DEFAULT_STIFFNESS[key]
            spin.setValue(value * kpa_scale if stress else value)
            if stress:
                spin.setSuffix(f" {unit}")
            spin.valueChanged.connect(self.changed)
            self.spins[key] = spin
            if key == "young":
                self.use_erm = QPushButton("Erm")
                self.use_erm.setToolTip("Young's modulus = rock mass modulus Erm (Generalized Hoek-Brown)")
                if on_erm is not None:
                    self.use_erm.clicked.connect(on_erm)
                row = QWidget()
                layout = QHBoxLayout(row)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(spin, stretch=1)
                layout.addWidget(self.use_erm)
                self.form.addRow(label, row)
                self._young_row = row
            else:
                self.form.addRow(label, spin)
        self._update_rows()

    # ------------------------------------------------------------- rows

    def set_criterion(self, criterion: str) -> None:
        self._kind = stiffness_kind(criterion)
        title = {"linear": "Linear Isotropic", "camclay": "CamClay Isotropic", "norsand": "NorSand"}[self._kind]
        self.setTitle(f"Stiffness ({title})")
        self.use_erm.setEnabled(criterion == "generalized_hoek_brown")
        self._update_rows()

    def _row_widget(self, key: str):
        if key == "elastic_parameter":
            return self.elastic_parameter
        if key == "young":
            return self._young_row
        return self.spins[key]

    def _update_rows(self, *_args) -> None:
        shown = set(_ROWS[self._kind])
        if self._kind == "camclay":
            constant_g = self.elastic_parameter.currentText() == "Constant Shear Modulus"
            shown.discard("poisson" if constant_g else "shear_modulus")
        for key in ("elastic_parameter", *_FIELDS):
            self.form.setRowVisible(self._row_widget(key), key in shown)

    # ----------------------------------------------------------- values

    def set_values(self, stiffness: dict) -> None:
        data = sm.stiffness_from(stiffness)
        for widget in (self.elastic_parameter, *self.spins.values()):
            widget.blockSignals(True)
        self.elastic_parameter.setCurrentText(data["elastic_parameter"])
        for key, spin in self.spins.items():
            stress = _FIELDS[key][1]
            spin.setValue(data[key] * self._scale if stress else data[key])
        for widget in (self.elastic_parameter, *self.spins.values()):
            widget.blockSignals(False)
        self._update_rows()

    def values(self) -> dict:
        out = {"type": "Linear Isotropic", "elastic_parameter": self.elastic_parameter.currentText()}
        for key, spin in self.spins.items():
            stress = _FIELDS[key][1]
            out[key] = spin.value() / self._scale if stress else spin.value()
        return out

    def rescale(self, kpa_scale: float, unit: str) -> None:
        ratio = kpa_scale / self._scale
        self._scale, self._unit = kpa_scale, unit
        for key, spin in self.spins.items():
            if _FIELDS[key][1]:
                spin.blockSignals(True)
                spin.setValue(spin.value() * ratio)
                spin.setSuffix(f" {unit}")
                spin.blockSignals(False)
