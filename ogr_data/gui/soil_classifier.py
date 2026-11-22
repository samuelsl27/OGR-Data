"""USCS soil classifier dialog (spec 004)."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import uscs


class _PlasticityCanvas(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(4.0, 4.0), tight_layout=True)
        super().__init__(self.figure)
        ax = self.figure.add_subplot(111)
        ax.set_title("USCS plasticity chart")
        ax.set_xlabel("Liquid limit")
        ax.set_ylabel("Plasticity index")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 60)
        ax.grid(True, alpha=0.3)
        ll = np.linspace(0, 100, 200)
        ax.plot(ll, np.clip(uscs.a_line_pi(ll), 0, 60), color="#c0392b", label="A-line (PI = 0.73 (LL-20))")
        ax.plot(ll, np.clip(uscs.u_line_pi(ll), 0, 60), color="#95a5a6", linestyle=":", label="U-line")
        ax.axvline(50.0, color="#bdc3c7", linestyle="--")
        self.axes = ax
        (self._point,) = ax.plot([], [], "o", color="#2c3e50")
        ax.legend(fontsize=7, loc="upper left")

    def set_point(self, ll: float | None, pi: float | None) -> None:
        if ll is None or pi is None:
            self._point.set_data([], [])
        else:
            self._point.set_data([ll], [pi])
        self.draw_idle()


class SoilClassifierDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Soil classifier — USCS (NRCS criteria)")
        self.resize(980, 560)

        self._fields: dict[str, QDoubleSpinBox] = {}
        form = QFormLayout()
        for key, label, value, lo, hi, dec in [
            ("fines_pct", "Fines, passing No. 200 (%)", 30.0, 0.0, 100.0, 1),
            ("sand_pct", "Sand, of total sample (%)", 50.0, 0.0, 100.0, 1),
            ("cu", "Cu = D60/D10", 0.0, 0.0, 1e6, 2),
            ("cc", "Cc = D30^2/(D10 D60)", 0.0, 0.0, 1e6, 2),
            ("ll", "Liquid limit, LL", 0.0, 0.0, 200.0, 1),
            ("pi", "Plasticity index, PI", 0.0, 0.0, 200.0, 1),
            ("organic_ratio", "LL(oven dry) / LL(air dry)", 1.0, 0.0, 1.5, 3),
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setDecimals(dec)
            spin.setValue(value)
            spin.valueChanged.connect(self._update)
            self._fields[key] = spin
            form.addRow(label, spin)
        self._highly_organic = QCheckBox("Highly organic soil (peat-like)")
        self._highly_organic.toggled.connect(self._update)

        classify_button = QPushButton("Classify")
        classify_button.clicked.connect(self._update)

        inputs = QWidget()
        left = QVBoxLayout(inputs)
        left.addLayout(form)
        left.addWidget(self._highly_organic)
        left.addWidget(classify_button)

        self._symbol = QLineEdit()
        self._symbol.setReadOnly(True)
        self._symbol.setStyleSheet("font-weight: bold; font-size: 18px;")
        self._card = QTextEdit()
        self._card.setReadOnly(True)

        results = QWidget()
        right = QVBoxLayout(results)
        right.addWidget(QLabel("USCS classification"))
        right.addWidget(self._symbol)
        right.addWidget(QLabel("Engineering properties (NRCS NEH 631, figure 3-22)"))
        right.addWidget(self._card, stretch=1)
        right.addWidget(QLabel("Source: " + uscs.uscs_properties_source()))

        self._chart = _PlasticityCanvas()

        splitter = QSplitter()
        splitter.addWidget(inputs)
        splitter.addWidget(self._chart)
        splitter.addWidget(results)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        layout.addWidget(buttons)
        self._update()

    def _update(self) -> None:
        inp = uscs.UsCSInput(
            fines_pct=self._fields["fines_pct"].value(),
            sand_pct=self._fields["sand_pct"].value(),
            cu=self._fields["cu"].value() or None,
            cc=self._fields["cc"].value() or None,
            ll=self._fields["ll"].value() or None,
            pi=self._fields["pi"].value() or None,
            organic_ratio=self._fields["organic_ratio"].value(),
            highly_organic=self._highly_organic.isChecked(),
        )
        self._chart.set_point(inp.ll, inp.pi)
        try:
            result = uscs.classify(inp)
        except ValueError as exc:
            self._symbol.setText("—")
            self._card.setPlainText(str(exc))
            return
        self._symbol.setText(result.symbol)
        card = uscs.uscs_properties(result.symbol)
        text = (
            f"Typical names: {card['typical_names']}\n\n"
            f"Shear strength: {card['shear_strength']}\n"
            f"Compressibility: {card['compressibility']}\n"
            f"Workability as construction material: {card['workability']}\n"
            f"Permeability when compacted: {card['permeability']}\n"
        )
        if result.notes:
            text += "\nNotes:\n" + "\n".join(f"- {n}" for n in result.notes)
        self._card.setPlainText(text)
