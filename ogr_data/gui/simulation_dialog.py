"""Define Test Simulations dialog (spec 013), modelled on RSData's (capture 20).

Name, symbol and color; Test Type, Seepage Condition, Loading Direction,
Maximum Strain, Number of Steps and Cyclic Loading Cycles, plus the
confining stress of triaxial and biaxial tests (display unit).
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from ..core import simulation as sm
from ..core.project import SYMBOLS
from .states_dialog import _ItemsDialog


class TestSimulationsDialog(_ItemsDialog):
    noun = "Test"

    def __init__(self, parent, material_name: str, tests: list, unit: str, initial: int = 0) -> None:
        super().__init__(parent, f"Define Test Simulations - {material_name}", tests, unit, initial)
        self.resize(640, 400)

    def _build_editor(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()

        def combo(options) -> QComboBox:
            widget = QComboBox()
            items = options.items() if isinstance(options, dict) else ((o, o) for o in options)
            for key, label in items:
                widget.addItem(label, key)
            return widget

        self._symbol = combo(SYMBOLS)
        self._test_type = combo(sm.TEST_TYPES)
        self._seepage = combo(sm.SEEPAGE)
        self._loading_dir = combo(sm.LOADING)
        self._confining = QDoubleSpinBox()
        self._confining.setRange(0.0, 1e12)
        self._confining.setDecimals(4)
        self._confining.setSuffix(f" {self._unit}")
        self._max_strain = QDoubleSpinBox()
        self._max_strain.setRange(1e-6, 1.0)
        self._max_strain.setDecimals(6)
        self._max_strain.setSingleStep(0.01)
        self._steps = QSpinBox()
        self._steps.setRange(1, 100000)
        self._cyclic = QCheckBox("Cyclic Loading Cycles:")
        self._cycles = QSpinBox()
        self._cycles.setRange(1, 1000)
        self._cyclic.toggled.connect(self._cycles.setEnabled)
        cyclic_row = QWidget()
        row = QHBoxLayout(cyclic_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._cyclic)
        row.addWidget(self._cycles, stretch=1)
        self._test_type.currentIndexChanged.connect(self._config_changed)
        form.addRow("Symbol:", self._symbol)
        form.addRow("Test Type:", self._test_type)
        form.addRow("Seepage Condition:", self._seepage)
        form.addRow("Loading Direction:", self._loading_dir)
        form.addRow("Confining Stress:", self._confining)
        form.addRow("Maximum Strain:", self._max_strain)
        form.addRow("Number of Steps:", self._steps)
        form.addRow(cyclic_row)
        self._form = form
        layout.addLayout(form)
        self._note = QLabel()
        self._note.setWordWrap(True)
        layout.addWidget(self._note)
        layout.addStretch(1)
        self._config_changed()

    def _config_changed(self) -> None:
        test = sm.TestSimulation(test_type=self._test_type.currentData())
        self._form.setRowVisible(self._confining, test.confined)
        if not test.simulated:
            self._note.setText(f"{sm.TEST_TYPES[test.test_type]}: RSData's inputs for it are not documented; kept in the project but not simulated.")
        elif test.test_type == "biaxial":
            self._note.setText("Biaxial: plane strain (no strain in the second lateral direction).")
        elif test.test_type == "simple_shear":
            self._note.setText(
                "Simple Shear: imposed shear strain (Maximum Strain = gamma), no lateral strains; "
                "the Confining Stress is the initial (isotropic) and, drained, the constant vertical stress."
            )
        else:
            self._note.setText("")

    def _new_item(self, name: str, color: str):
        return sm.TestSimulation(name=name, color=color)

    def _load(self, item: sm.TestSimulation) -> None:
        for widget, value in (
            (self._symbol, item.symbol),
            (self._test_type, item.test_type),
            (self._seepage, item.seepage),
            (self._loading_dir, item.loading),
        ):
            widget.setCurrentIndex(max(0, widget.findData(value)))
        self._confining.setValue(item.confining * self._kpa_scale)
        self._max_strain.setValue(item.max_strain)
        self._steps.setValue(item.steps)
        self._cyclic.setChecked(item.cyclic)
        self._cycles.setValue(item.cycles)
        self._cycles.setEnabled(item.cyclic)
        self._config_changed()

    def _store(self, item: sm.TestSimulation) -> None:
        item.symbol = self._symbol.currentData()
        item.test_type = self._test_type.currentData()
        item.seepage = self._seepage.currentData()
        item.loading = self._loading_dir.currentData()
        item.confining = self._confining.value() / self._kpa_scale
        item.max_strain = self._max_strain.value()
        item.steps = self._steps.value()
        item.cyclic = self._cyclic.isChecked()
        item.cycles = self._cycles.value()
