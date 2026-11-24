"""Define Test Simulations dialog (spec 013), modelled on RSData's.

Fields as in RSData 1.009 (capture 20 and the NorSand / Modified Cam Clay
tutorials): Name, Symbol, Test Type, Seepage Condition, Loading Direction,
Initial Effective Lateral Stress (display unit), Initial Effective K0,
Maximum Strain, Number of Steps and Cyclic Loading Cycles. The General Test
adds the strain direction (OGR design: RSData does not document its inputs).
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from ..core import simulation as sm
from ..core.project import SYMBOLS
from .i18n import tr
from .number_spin import NumberSpinBox
from .states_dialog import _ItemsDialog


class TestSimulationsDialog(_ItemsDialog):
    noun = "Test"

    def empty_hint(self) -> str:
        return tr("No test simulations yet. Click Add, choose the test type and run Tests > Compute (F5).")

    def __init__(self, parent, material_name: str, tests: list, unit: str, initial: int = 0) -> None:
        super().__init__(parent, tr("Define Test Simulations - {0}").format(material_name), tests, unit, initial)
        self.resize(680, 460)

    def _build_editor(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()

        def combo(options) -> QComboBox:
            widget = QComboBox()
            items = options.items() if isinstance(options, dict) else ((o, o) for o in options)
            for key, label in items:
                widget.addItem(tr(label), key)  # i18n: registry
            return widget

        self._symbol = combo(SYMBOLS)
        self._test_type = combo(sm.TEST_TYPES)
        self._seepage = combo(sm.SEEPAGE)
        self._loading_dir = combo(sm.LOADING)
        self._confining = NumberSpinBox()
        self._confining.setRange(0.0, 1e12)
        self._confining.setDecimals(4)
        self._confining.setSuffix(f" {self._unit}")
        self._k0 = NumberSpinBox()
        self._k0.setRange(0.01, 100.0)
        self._k0.setDecimals(4)
        self._k0.setSingleStep(0.05)
        self._max_strain = NumberSpinBox()
        self._max_strain.setRange(1e-6, 1.0)
        self._max_strain.setDecimals(6)
        self._max_strain.setSingleStep(0.01)
        self._steps = QSpinBox()
        self._steps.setRange(1, 100000)
        self._cyclic = QCheckBox(tr("Cyclic Loading Cycles:"))
        self._cycles = QSpinBox()
        self._cycles.setRange(1, 1000)
        self._cyclic.toggled.connect(self._cycles.setEnabled)
        cyclic_row = QWidget()
        row = QHBoxLayout(cyclic_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._cyclic)
        row.addWidget(self._cycles, stretch=1)
        # General Test: strain direction (proportional strain path)
        self._ratio_box = QWidget()
        grid = QGridLayout(self._ratio_box)
        grid.setContentsMargins(0, 0, 0, 0)
        self._ratios: list[QDoubleSpinBox] = []
        for i, name in enumerate(sm.STRAIN_COMPONENTS):
            spin = NumberSpinBox()
            spin.setRange(-1000.0, 1000.0)
            spin.setDecimals(4)
            grid.addWidget(QLabel(name), i // 3 * 2, i % 3)
            grid.addWidget(spin, i // 3 * 2 + 1, i % 3)
            self._ratios.append(spin)
        self._test_type.currentIndexChanged.connect(self._config_changed)
        form.addRow(tr("Symbol:"), self._symbol)
        form.addRow(tr("Test Type:"), self._test_type)
        form.addRow(tr("Seepage Condition:"), self._seepage)
        form.addRow(tr("Loading Direction:"), self._loading_dir)
        form.addRow(tr("Initial Effective Lateral Stress ({0}):").format(self._unit), self._confining)
        form.addRow(tr("Initial Effective K0:"), self._k0)
        form.addRow(tr("Strain direction:"), self._ratio_box)
        form.addRow(tr("Maximum Strain:"), self._max_strain)
        form.addRow(tr("Number of Steps:"), self._steps)
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
        self._form.setRowVisible(self._k0, test.confined)
        self._form.setRowVisible(self._ratio_box, test.test_type == "general")
        notes = {
            "uniaxial": "",
            "triaxial": tr("Initial axial stress = lateral stress / K0."),
            "biaxial": tr(
                "Biaxial: plane strain (no strain in the second lateral direction); initial axial stress = lateral / K0."
            ),
            "simple_shear": tr(
                "Simple Shear: imposed shear strain (Maximum Strain = gamma), no lateral strains; the initial "
                "vertical stress (lateral / K0) is kept constant when drained."
            ),
            "general": tr(
                "General Test (OGR Data; RSData does not document its inputs): proportional strain path in the given "
                "direction, Maximum Strain on its largest component. Undrained keeps the volume (normal components "
                "made deviatoric); pore pressure = change of the mean effective stress."
            ),
        }
        self._note.setText(notes[test.test_type])

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
        self._k0.setValue(item.k0)
        for spin, value in zip(self._ratios, item.strain_ratio):
            spin.setValue(value)
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
        item.k0 = self._k0.value()
        item.strain_ratio = tuple(spin.value() for spin in self._ratios)
        item.max_strain = self._max_strain.value()
        item.steps = self._steps.value()
        item.cyclic = self._cyclic.isChecked()
        item.cycles = self._cycles.value()
