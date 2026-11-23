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
from .i18n import localize, tr


class _PlasticityCanvas(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(4.0, 4.0), tight_layout=True)
        super().__init__(self.figure)
        ax = self.figure.add_subplot(111)
        ax.set_title(tr("USCS plasticity chart"))
        ax.set_xlabel(tr("Liquid limit"))
        ax.set_ylabel(tr("Plasticity index"))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 60)
        ax.grid(True, alpha=0.3)
        ll = np.linspace(0, 100, 200)
        ax.plot(ll, np.clip(uscs.a_line_pi(ll), 0, 60), color="#c0392b", label=tr("A-line (PI = 0.73 (LL-20))"))
        ax.plot(ll, np.clip(uscs.u_line_pi(ll), 0, 60), color="#95a5a6", linestyle=":", label=tr("U-line"))
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
    def __init__(self, parent=None, on_create=None) -> None:
        super().__init__(parent)
        self.on_create = on_create  # callback(symbol, {"peak_cohesion", "peak_friction"})
        self.symbol = ""
        self.setWindowTitle(tr("Soil classifier — USCS (NRCS criteria)"))
        self.resize(980, 560)

        self._fields: dict[str, QDoubleSpinBox] = {}
        form = QFormLayout()
        for key, label, value, lo, hi, dec in [
            ("fines_pct", tr("Fines, passing No. 200 (%)"), 30.0, 0.0, 100.0, 1),
            ("sand_pct", tr("Sand, of total sample (%)"), 50.0, 0.0, 100.0, 1),
            ("cu", "Cu = D60/D10", 0.0, 0.0, 1e6, 2),
            ("cc", "Cc = D30^2/(D10 D60)", 0.0, 0.0, 1e6, 2),
            ("ll", tr("Liquid limit, LL"), 0.0, 0.0, 200.0, 1),
            ("pi", tr("Plasticity index, PI"), 0.0, 0.0, 200.0, 1),
            ("organic_ratio", tr("LL(oven dry) / LL(air dry)"), 1.0, 0.0, 1.5, 3),
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setDecimals(dec)
            spin.setValue(value)
            spin.valueChanged.connect(self._update)
            self._fields[key] = spin
            form.addRow(label, spin)
        self._highly_organic = QCheckBox(tr("Highly organic soil (peat-like)"))
        self._highly_organic.toggled.connect(self._update)

        classify_button = QPushButton(tr("Classify"))
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
        right.addWidget(QLabel(tr("USCS classification")))
        right.addWidget(self._symbol)
        properties_title = QLabel(tr("Engineering properties (NRCS NEH 631, figure 3-22)"))
        properties_title.setWordWrap(True)
        right.addWidget(properties_title)
        right.addWidget(self._card, stretch=1)
        # spec 025a (B3): long source texts wrap; unwrapped, they widened the
        # results column until the plasticity chart was squeezed to nothing
        source = QLabel(tr("Source: {0}").format(uscs.uscs_properties_source()))
        source.setWordWrap(True)
        right.addWidget(source)
        # spec 018: numeric typical strength of the compacted soil (UFC 3-220-01N)
        strength_title = QLabel(tr("Typical strength, compacted (UFC 3-220-01N Table 8-3.1, USBR data)"))
        strength_title.setWordWrap(True)
        right.addWidget(strength_title)
        self._numeric = QLabel()
        self._numeric.setWordWrap(True)
        right.addWidget(self._numeric)
        self._create = QPushButton(tr("Create Mohr-Coulomb material (c' saturated, phi')"))
        self._create.clicked.connect(self.create_material)
        right.addWidget(self._create)

        self._chart = _PlasticityCanvas()
        self._chart.setMinimumWidth(320)

        splitter = QSplitter()
        splitter.addWidget(inputs)
        splitter.addWidget(self._chart)
        splitter.addWidget(results)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([250, 380, 330])

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        layout.addWidget(buttons)
        self._update()

    def _update(self) -> None:
        ll = self._fields["ll"].value() or None
        pi = self._fields["pi"].value() or None
        self._chart.set_point(ll, pi)
        try:
            inp = uscs.UsCSInput(
                fines_pct=self._fields["fines_pct"].value(),
                sand_pct=self._fields["sand_pct"].value(),
                cu=self._fields["cu"].value() or None,
                cc=self._fields["cc"].value() or None,
                ll=ll,
                pi=pi,
                organic_ratio=self._fields["organic_ratio"].value(),
                highly_organic=self._highly_organic.isChecked(),
            )
            result = uscs.classify(inp)
        except ValueError as exc:
            self._symbol.setText("—")
            self._card.setPlainText(str(exc))
            self.symbol = ""
            self._show_numeric()
            return
        self._symbol.setText(result.symbol)
        self.symbol = result.symbol
        self._show_numeric()
        card = uscs.uscs_properties(result.symbol)
        text = (
            tr("Typical names: {0}").format(card["typical_names"]) + "\n\n"
            + tr("Shear strength: {0}").format(card["shear_strength"]) + "\n"
            + tr("Compressibility: {0}").format(card["compressibility"]) + "\n"
            + tr("Workability as construction material: {0}").format(card["workability"]) + "\n"
            + tr("Permeability when compacted: {0}").format(card["permeability"]) + "\n"
        )
        if result.notes:
            text += "\n" + tr("Notes:") + "\n" + "\n".join(f"- {n}" for n in result.notes)
        self._card.setPlainText(text)

    # ------------------------------------------------------------ spec 018

    def numeric_parameters(self) -> dict | None:
        from ..core import barton

        try:
            return barton.mohr_coulomb_from_symbol(self.symbol) if self.symbol else None
        except ValueError:
            return None

    def _show_numeric(self) -> None:
        from ..core import barton

        row = barton.compacted_properties(self.symbol) if self.symbol else None
        if row is None:
            self._numeric.setText(tr("{0}: not listed in UFC 3-220-01N Table 8-3.1 (no numeric values).").format(self.symbol or tr("No class")))
        else:
            c_comp, c_sat = row["cohesion_compacted_kpa"], row["cohesion_saturated_kpa"]
            fmt = lambda v: "-----" if v is None else localize(f"{v:g} kPa")
            self._numeric.setText(
                tr(
                    "{0}: c' as compacted {1}, c' saturated {2}, phi' {3} deg (effective envelope); max dry unit weight "
                    "{4} g/cm3 (pcf). '>' = greater than the value shown."
                ).format(row["symbol"], fmt(c_comp), fmt(c_sat), row["phi_effective"] or "-----", localize(str(row["max_dry_unit_weight"])))
            )
        self._create.setEnabled(self.numeric_parameters() is not None and self.on_create is not None)

    def create_material(self) -> None:
        params = self.numeric_parameters()
        if params is not None and self.on_create is not None:
            self.on_create(self.symbol, params)
