"""Main window of OGR Data: sidebar inputs (old-RocData style) + two plots."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core.envelope import shear_normal_envelope
from ..core.hoek_brown import (
    HbInput,
    ModulusMethod,
    compute,
    hoek_brown_constants,
    major_principal_stress,
)
from .plots import EnvelopeCanvas


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OGR Data - Hoek-Brown calculator")
        self.resize(1100, 620)

        self._fields: dict[str, QDoubleSpinBox] = {}
        self._method = QComboBox()
        self._method.addItem("Hoek & Diederichs (2006)", ModulusMethod.HOEK_DIEDERICHS_2006)
        self._method.addItem("Simplified Hoek & Diederichs (2006)", ModulusMethod.HOEK_DIEDERICHS_2006_SIMPLIFIED)
        self._method.addItem("Hoek, Carranza-Torres & Corkum (2002)", ModulusMethod.HOEK_CARRANZA_TORRES_CORKUM_2002)
        self._method.currentIndexChanged.connect(self.refresh)

        sidebar = QVBoxLayout()
        inputs_box = QGroupBox("Input parameters")
        form = QFormLayout(inputs_box)
        for key, label, value, lo, hi, step in [
            ("sigci", "sigci (MPa)", 30.0, 0.01, 100000.0, 1.0),
            ("gsi", "GSI", 50.0, 1.0, 100.0, 1.0),
            ("mi", "mi", 10.0, 0.01, 100.0, 0.5),
            ("disturbance", "D", 0.0, 0.0, 1.0, 0.05),
            ("ei", "Ei (MPa)", 12000.0, 1.0, 100000000.0, 100.0),
            ("sig3max", "sig3max (MPa)", 7.5, 0.01, 100000.0, 0.5),
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setValue(value)
            spin.setSingleStep(step)
            spin.valueChanged.connect(self.refresh)
            self._fields[key] = spin
            form.addRow(label, spin)
        form.addRow("Modulus method", self._method)

        self._outputs = QLabel()
        self._outputs.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._outputs.setMinimumWidth(260)
        self._outputs.setStyleSheet("font-family: Consolas, monospace;")

        sidebar.addWidget(inputs_box)
        sidebar.addWidget(QLabel("Computed parameters"))
        sidebar.addWidget(self._outputs, stretch=1)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(340)

        self._principal = EnvelopeCanvas("Principal Stresses", "sigma3 (MPa)", "sigma1 (MPa)")
        self._shear = EnvelopeCanvas("Shear - Normal Stresses", "normal stress (MPa)", "shear stress (MPa)")

        plots = QSplitter(Qt.Orientation.Horizontal)
        plots.addWidget(self._principal)
        plots.addWidget(self._shear)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(sidebar_widget)
        splitter.addWidget(plots)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.refresh()

    def _input(self) -> HbInput:
        return HbInput(
            sigci=self._fields["sigci"].value(),
            gsi=self._fields["gsi"].value(),
            mi=self._fields["mi"].value(),
            disturbance=self._fields["disturbance"].value(),
            ei=self._fields["ei"].value(),
            sig3max=self._fields["sig3max"].value(),
        )

    def refresh(self) -> None:
        try:
            inp = self._input()
        except ValueError:
            return
        method = self._method.currentData()
        result = compute(inp, method)
        mb, s, a = result.mb, result.s, result.a

        env = shear_normal_envelope(inp, mb, s, a)
        self._principal.redraw(env.sig3, env.sig1)

        # Equivalent Mohr-Coulomb envelope in both spaces.
        phi = math.radians(result.mc.friction_deg)
        c = result.mc.cohesion
        sig3_mc = np.linspace(0.0, inp.sig3max, 2)
        sig1_mc = (2.0 * c * math.cos(phi) / (1.0 - math.sin(phi))) + ((1.0 + math.sin(phi)) / (1.0 - math.sin(phi))) * sig3_mc
        normal_mc = sig3_mc
        shear_mc = c + normal_mc * math.tan(phi)
        self._principal.redraw(env.sig3, env.sig1, sig3_mc, sig1_mc)
        self._shear.redraw(env.normal, env.shear, normal_mc, shear_mc)

        self._outputs.setText(
            f"mb   = {mb:.4f}\n"
            f"s    = {s:.4f}\n"
            f"a    = {a:.4f}\n"
            f"sigt = {result.sigt:.4f} MPa\n"
            f"sigc = {result.sigc:.4f} MPa\n"
            f"sigcm= {result.sigcm:.4f} MPa\n"
            f"c    = {result.mc.cohesion:.4f} MPa\n"
            f"phi  = {result.mc.friction_deg:.2f} deg\n"
            f"Erm  = {result.erm:.2f} MPa"
        )
