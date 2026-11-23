"""Calibration dialog (spec 014), modelled on RSData's (capture 33).

Material Model (source) · New Model Settings (material name, strength
type) · Curve Fit Analysis (algorithm, error summation, error type) ·
Failure States (checkable list over the project) and Failure Data Type.
The fit is previewed live; OK creates a new material.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ..core import calibration as cal
from ..core import fitting
from ..core import units
from ..core.models import CRITERIA
from .i18n import localize, tr


class CalibrationDialog(QDialog):
    def __init__(self, parent, project, current: int, unit: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Calibration"))
        self.resize(560, 720)
        self._project = project
        self._unit = unit
        self._kpa_scale = units.stress_factor(unit) / 1000.0
        self.result: cal.CalibrationResult | None = None
        source = project.materials[current]

        layout = QVBoxLayout(self)
        top = QFormLayout()
        criterion = tr(CRITERIA[source.criterion].label)  # i18n: registry
        top.addRow(tr("Material Model:"), QLabel(f"{source.name} ({criterion})"))
        layout.addLayout(top)

        new_box = QGroupBox(tr("New Model Settings"))
        new_form = QFormLayout(new_box)
        self.name = QLineEdit(project.unique_name("Calibrated Material"))
        self.strength = QComboBox()
        for key, label in cal.STRENGTH_TYPES.items():
            self.strength.addItem(tr(label), key)  # i18n: registry
        self.strength.setCurrentIndex(self.strength.findData("generalized_hoek_brown"))  # RSData default
        new_form.addRow("Material:", self.name)  # i18n: ignore
        new_form.addRow(tr("Strength type:"), self.strength)
        layout.addWidget(new_box)

        fit_box = QGroupBox(tr("Curve Fit Analysis"))
        fit_form = QFormLayout(fit_box)
        self.algorithm = QComboBox()
        for key, label in cal.ALGORITHMS.items():
            self.algorithm.addItem(tr(label), key)  # i18n: registry
        self.algorithm.setCurrentIndex(self.algorithm.findData(fitting.LEVENBERG_MARQUARDT))
        self.summation = QComboBox()
        self.summation.addItem("Vertical")  # i18n: ignore -- the only summation documented (RocData manual)
        self.error_type = QComboBox()
        for value in cal.ERROR_TYPES:
            self.error_type.addItem(tr(value), value)  # i18n: registry
        fit_form.addRow(tr("Algorithm:"), self.algorithm)
        fit_form.addRow(tr("Error Summation:"), self.summation)
        fit_form.addRow(tr("Error Type:"), self.error_type)
        layout.addWidget(fit_box)

        states_box = QGroupBox(tr("Failure States"))
        states_form = QFormLayout(states_box)
        self.states = QListWidget()
        multi = len(project.materials) > 1
        kinds = {"direct_shear": tr("direct shear")}
        for m_index, material in enumerate(project.materials):
            for s_index, state in enumerate(material.failure_states):
                label = f"{material.name}: {state.name}" if multi else state.name
                kind = kinds.get(state.test_type, state.test_type.replace("_", " "))
                item = QListWidgetItem(f"{label}  [{kind}]")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if m_index == current else Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, (m_index, s_index))
                self.states.addItem(item)
        self.states.setMaximumHeight(150)
        self.data_type = QComboBox()
        for value in cal.DATA_TYPES:
            self.data_type.addItem(tr(value), value)  # i18n: registry
        self.sigci = QDoubleSpinBox()
        self.sigci.setRange(0.0, 1e12)
        self.sigci.setDecimals(4)
        self.sigci.setSuffix(f" {unit}")
        params = source.parameters
        self.sigci.setValue(float(params.get("sigci", params.get("compressive_strength", 100000.0))) * self._kpa_scale)
        self.disturbance = QDoubleSpinBox()
        self.disturbance.setRange(0.0, 1.0)
        self.disturbance.setSingleStep(0.1)
        self.disturbance.setValue(float(params.get("d", 0.0)))
        self.phi_b = QDoubleSpinBox()
        self.phi_b.setRange(0.0, 89.0)
        self.phi_b.setSuffix(" deg")
        self.phi_b.setValue(float(params.get("phi_r", 30.0)))
        states_form.addRow(tr("Failure States:"), self.states)
        states_form.addRow(tr("Failure Data Type:"), self.data_type)
        states_form.addRow(tr("sigci (rock mass data):"), self.sigci)
        states_form.addRow(tr("D (rock mass data):"), self.disturbance)
        states_form.addRow("phi b (Barton-Bandis):", self.phi_b)
        self._states_form = states_form
        layout.addWidget(states_box)

        self.output = QLabel()
        self.output.setWordWrap(True)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)
        # spec 025a (B4): with nothing to calibrate against, say so and offer
        # the way out instead of an error the user did not cause
        self.wants_failure_states = False
        self.define_states_button = QPushButton(tr("Define Failure States…"))
        self.define_states_button.clicked.connect(self._ask_for_failure_states)
        self.define_states_button.setVisible(
            not any(cal.has_points(s) for m in project.materials for s in m.failure_states)
        )
        layout.addWidget(self.define_states_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        for combo in (self.strength, self.algorithm, self.error_type, self.data_type):
            combo.currentIndexChanged.connect(self.run)
        for spin in (self.sigci, self.disturbance, self.phi_b):
            spin.valueChanged.connect(self.run)
        self.states.itemChanged.connect(self.run)
        self.run()

    # ------------------------------------------------------------------

    def selected_states(self) -> list:
        out = []
        for i in range(self.states.count()):
            item = self.states.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                m, s = item.data(Qt.ItemDataRole.UserRole)
                out.append(self._project.materials[m].failure_states[s])
        return out

    def settings(self) -> cal.CalibrationSettings:
        return cal.CalibrationSettings(
            strength_type=self.strength.currentData(),
            algorithm=self.algorithm.currentData(),
            error_type=self.error_type.currentData(),
            data_type=self.data_type.currentData(),
            sigci_kpa=self.sigci.value() / self._kpa_scale,
            disturbance=self.disturbance.value(),
            phi_b_deg=self.phi_b.value(),
        )

    def run(self) -> None:
        strength = self.strength.currentData()
        ghb = strength == "generalized_hoek_brown"
        if not ghb and self.data_type.currentIndex() != 0:
            self.data_type.blockSignals(True)
            self.data_type.setCurrentIndex(0)
            self.data_type.blockSignals(False)
        self.data_type.setEnabled(ghb)
        mass = ghb and self.data_type.currentData() == "Rock Mass Data"
        self._states_form.setRowVisible(self.sigci, mass)
        self._states_form.setRowVisible(self.disturbance, mass)
        self._states_form.setRowVisible(self.phi_b, strength == "barton_bandis")
        selected = self.selected_states()
        if not any(cal.has_points(s) for s in selected):
            # a hint, not an error: nothing has been tried yet
            self.result = None
            if self.define_states_button.isVisibleTo(self):
                self.output.setText(tr(
                    "There are no failure states with test points yet. Calibration fits a model to "
                    "them: define them in Failure States > Define Failure States…"
                ))
            else:
                self.output.setText(tr("Select at least one failure state with test points."))
            self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        try:
            self.result = cal.calibrate(selected, self.settings())
        except ValueError as exc:
            self.result = None
            self.output.setText(f'<span style="color:#c0392b">{exc}</span>')  # i18n: ignore -- core message
        else:
            self.output.setText(localize(self._describe(self.result)))
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.result is not None)

    def _ask_for_failure_states(self) -> None:
        """Close and let the window open Define Failure States (spec 025a)."""

        self.wants_failure_states = True
        self.result = None
        self.reject()

    def _describe(self, r: cal.CalibrationResult) -> str:
        scale = units.stress_factor(self._unit)  # MPa -> display
        lines = []
        for key, value in r.fitted.items():
            if key.endswith("_mpa"):
                lines.append(f"{key[:-4]} = {value * scale:.6g} {self._unit}")
            elif key.endswith("_deg") or key == "friction_deg":
                lines.append(f"{key.replace('_deg', '')} = {value:.4f} deg")
            else:
                lines.append(f"{key} = {value:.6g}")
        relative = self.error_type.currentData() == "Relative"
        error = tr("relative") if relative else f"{self._unit}²"
        ssr = r.ssr if relative else r.ssr * scale**2
        if r.data_kind == fitting.TRIAXIAL:
            summary = tr("{0} triaxial points · residuals (sum of squares, vertical, {1}) = {2}")
        else:
            summary = tr("{0} direct shear points · residuals (sum of squares, vertical, {1}) = {2}")
        return (
            "<b>" + " · ".join(lines) + "</b><br>"
            + summary.format(r.n_points, error, f"{ssr:.6g}")
            + f"<br><i>{r.method_note}</i>"
        )
