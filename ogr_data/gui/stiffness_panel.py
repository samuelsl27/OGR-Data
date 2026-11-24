"""Stiffness group of the sidebar (specs 013 and 013b).

The reference program shows a Stiffness tab per material model: Linear Isotropic (Poisson's
Ratio, Young's Modulus) for most models, "CamClay Isotropic" (Elastic
Parameter: Constant Poisson Ratio / Constant Shear Modulus) for Cam-Clay and
Modified Cam-Clay, and the NorSand stiffness (Shear modulus at reference,
Reference pressure for shear modulus, Modulus exponent, Poisson's ratio,
Minimum Shear Modulus). Stresses are stored in kPa and shown in the display unit.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QWidget

from ..core import simulation as sm
from .i18n import tr
from .number_spin import NumberSpinBox


def _t(text: str) -> str:
    """Marks an English text that is translated where it is shown (spec 024)."""

    return text


# (key, label, is_stress, minimum, maximum, decimals)
_FIELDS = {
    "poisson": (_t("Poisson's Ratio"), False, -0.99, 0.4999, 4),
    "young": (_t("Young's Modulus"), True, 1e-9, 1e15, 4),
    "shear_modulus": (_t("Shear Modulus"), True, 1e-9, 1e15, 4),
    "g_ref": (_t("Shear modulus at reference"), True, 1e-9, 1e15, 4),
    "p_ref": (_t("Reference pressure for shear modulus"), True, 1e-9, 1e12, 4),
    "g_exp": (_t("Modulus exponent"), False, 0.0, 1.0, 4),
    "ns_poisson": (_t("Poisson's ratio"), False, -0.99, 0.4999, 4),
    "g_min": (_t("Minimum Shear Modulus"), True, 0.0, 1e15, 4),
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
        super().__init__(tr("Stiffness ({0})").format(tr(sm.STIFFNESS_TYPES[0])))  # i18n: registry
        self._scale = kpa_scale
        self._unit = unit
        self._kind = "linear"
        self.form = QFormLayout(self)
        self.spins: dict[str, QDoubleSpinBox] = {}
        self.elastic_parameter = QComboBox()
        for option in sm.CAM_CLAY_ELASTIC:
            self.elastic_parameter.addItem(tr(option), option)  # i18n: registry
        self.elastic_parameter.currentIndexChanged.connect(self._update_rows)
        self.elastic_parameter.currentIndexChanged.connect(self.changed)
        self.form.addRow(tr("Elastic Parameter"), self.elastic_parameter)
        for key, (label, stress, lo, hi, decimals) in _FIELDS.items():
            spin = NumberSpinBox()
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
                self.use_erm.setToolTip(tr("Young's modulus = rock mass modulus Erm (Generalized Hoek-Brown)"))
                if on_erm is not None:
                    self.use_erm.clicked.connect(on_erm)
                row = QWidget()
                layout = QHBoxLayout(row)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(spin, stretch=1)
                layout.addWidget(self.use_erm)
                young_label = QLabel(tr(label))  # i18n: ignore (keys marked with _t)
                young_label.setBuddy(spin)  # spec 025f RF-3: the input, not its row
                self.form.addRow(young_label, row)
                self._young_row = row
            else:
                self.form.addRow(tr(label), spin)  # i18n: ignore (keys marked with _t)
        self._update_rows()

    def tab_chain(self) -> list:
        """The panel's inputs in reading order (spec 025f RF-4)."""

        chain = [self.elastic_parameter]
        for key in _FIELDS:
            chain.append(self.spins[key])
            if key == "young":
                chain.append(self.use_erm)
        return chain

    # ------------------------------------------------------------- rows

    def set_criterion(self, criterion: str) -> None:
        self._kind = stiffness_kind(criterion)
        # spec 025f RF-1: help of each stiffness parameter
        from .parameter_tooltip import parameter_tooltip

        for key, (label, stress, *_rest) in _FIELDS.items():
            self.spins[key].setToolTip(parameter_tooltip(criterion, key, tr(label), self._unit if stress else ""))  # i18n: ignore (keys marked with _t)
        title = {"linear": tr(sm.STIFFNESS_TYPES[0]), "camclay": tr("CamClay Isotropic"), "norsand": "NorSand"}[self._kind]  # i18n: registry
        self.setTitle(tr("Stiffness ({0})").format(title))
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
            constant_g = self.elastic_parameter.currentData() == "Constant Shear Modulus"
            shown.discard("poisson" if constant_g else "shear_modulus")
        for key in ("elastic_parameter", *_FIELDS):
            self.form.setRowVisible(self._row_widget(key), key in shown)

    # ----------------------------------------------------------- values

    def set_values(self, stiffness: dict) -> None:
        data = sm.stiffness_from(stiffness)
        for widget in (self.elastic_parameter, *self.spins.values()):
            widget.blockSignals(True)
        self.elastic_parameter.setCurrentIndex(max(0, self.elastic_parameter.findData(data["elastic_parameter"])))
        for key, spin in self.spins.items():
            stress = _FIELDS[key][1]
            spin.setValue(data[key] * self._scale if stress else data[key])
        for widget in (self.elastic_parameter, *self.spins.values()):
            widget.blockSignals(False)
        self._update_rows()

    def values(self) -> dict:
        out = {"type": "Linear Isotropic", "elastic_parameter": self.elastic_parameter.currentData()}
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
