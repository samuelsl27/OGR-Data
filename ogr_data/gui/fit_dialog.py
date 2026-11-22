"""Fit lab data dialog (spec 006)."""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import fitting
from ..core.fitting import DIRECT, LEVENBERG_MARQUARDT, LINEAR, SIMPLEX, TRIAXIAL

_DATA_LABELS = {
    TRIAXIAL: ("sigma3 (MPa)", "sigma1 (MPa)"),
    DIRECT: ("normal stress (MPa)", "shear stress (MPa)"),
}

_METHODS = {
    "Linear regression": LINEAR,
    "Levenberg-Marquardt": LEVENBERG_MARQUARDT,
    "Simplex": SIMPLEX,
}


class FitDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fit strength criterion to lab data")
        self.resize(760, 560)
        self._result: fitting.FitResult | None = None

        self._criterion = QComboBox()
        for key in fitting.COMPATIBILITY:
            self._criterion.addItem(key, key)
        self._data_kind = QComboBox()
        self._method = QComboBox()
        self._fixed = QFormLayout()
        self._fixed_widgets: dict[str, QDoubleSpinBox] = {}

        self._criterion.currentIndexChanged.connect(self._refresh_options)
        self._data_kind.currentIndexChanged.connect(self._refresh_options)

        self._table = QTableWidget(8, 2)
        self._table.setHorizontalHeaderLabels(["x", "y"])

        paste_button = QPushButton("Paste from clipboard")
        paste_button.clicked.connect(self._paste)
        add_button = QPushButton("Add row")
        add_button.clicked.connect(lambda: self._table.insertRow(self._table.rowCount()))
        fit_button = QPushButton("Fit")
        fit_button.clicked.connect(self._run_fit)
        self._apply_button = QPushButton("Apply to material")
        self._apply_button.setEnabled(False)
        self._apply_button.clicked.connect(self._apply)

        self._output = QTextEdit()
        self._output.setReadOnly(True)

        options = QFormLayout()
        options.addRow("Criterion", self._criterion)
        options.addRow("Data type", self._data_kind)
        options.addRow("Method", self._method)
        options.addRow(self._fixed)

        table_box = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(paste_button)
        row.addWidget(add_button)
        table_box.addLayout(row)
        table_box.addWidget(self._table)

        actions = QHBoxLayout()
        actions.addWidget(fit_button)
        actions.addWidget(self._apply_button)

        layout = QVBoxLayout(self)
        layout.addLayout(options)
        layout.addLayout(table_box)
        layout.addLayout(actions)
        layout.addWidget(QLabel("Result"))
        layout.addWidget(self._output, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh_options()

    # ------------------------------------------------------------- options

    def _refresh_options(self) -> None:
        key = self._criterion.currentData()
        kinds = fitting.COMPATIBILITY.get(key, ())
        current_kind = self._data_kind.currentData()
        self._data_kind.blockSignals(True)
        self._data_kind.clear()
        for kind in kinds:
            self._data_kind.addItem("Triaxial" if kind == TRIAXIAL else "Direct shear", kind)
        if current_kind in kinds:
            self._data_kind.setCurrentIndex(kinds.index(current_kind))
        self._data_kind.blockSignals(False)

        kind = self._data_kind.currentData()
        x_label, y_label = _DATA_LABELS.get(kind, ("x", "y"))
        self._table.setHorizontalHeaderLabels([x_label, y_label])

        current_method = self._method.currentData()
        self._method.blockSignals(True)
        self._method.clear()
        has_linear = (key, kind) in (
            ("mohr_coulomb", TRIAXIAL),
            ("mohr_coulomb", DIRECT),
            ("hoek_brown", TRIAXIAL),
        )
        for label, value in _METHODS.items():
            if value == LINEAR and not has_linear:
                continue
            self._method.addItem(label, value)
        if current_method and self._method.findData(current_method) >= 0:
            self._method.setCurrentIndex(self._method.findData(current_method))
        self._method.blockSignals(False)

        while self._fixed.rowCount():
            self._fixed.removeRow(0)
        self._fixed_widgets = {}
        for label, name, value in self._fixed_fields(key):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1e12)
            spin.setDecimals(4)
            spin.setValue(value)
            self._fixed_widgets[name] = spin
            self._fixed.addRow(label, spin)

    def _fixed_fields(self, key: str) -> list[tuple[str, str, float]]:
        if key == "generalized_hoek_brown":
            return [("sigci, fixed (MPa)", "sigci_mpa", 30.0), ("D, fixed", "disturbance", 0.0)]
        if key == "barton_bandis":
            return [("phi_b, fixed (deg)", "phi_b_deg", 30.0)]
        return []

    # ---------------------------------------------------------------- data

    def _paste(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = QApplication.clipboard().text()
        rows = [r for r in text.replace("\r", "").split("\n") if r.strip()]
        data = []
        for r in rows:
            cells = r.split("\t") if "\t" in r else r.split()
            if len(cells) >= 2:
                try:
                    data.append((float(cells[0]), float(cells[1])))
                except ValueError:
                    continue
        self._table.setRowCount(len(data))
        for i, (a, b) in enumerate(data):
            self._table.setItem(i, 0, QTableWidgetItem(repr(a)))
            self._table.setItem(i, 1, QTableWidgetItem(repr(b)))

    def _data(self) -> tuple[np.ndarray, np.ndarray]:
        xs, ys = [], []
        for i in range(self._table.rowCount()):
            item_x = self._table.item(i, 0)
            item_y = self._table.item(i, 1)
            if item_x is None or item_y is None or not item_x.text().strip() or not item_y.text().strip():
                continue
            xs.append(float(item_x.text()))
            ys.append(float(item_y.text()))
        return np.array(xs), np.array(ys)

    # ----------------------------------------------------------------- fit

    def _run_fit(self) -> None:
        key = self._criterion.currentData()
        kind = self._data_kind.currentData()
        method = self._method.currentData()
        x, y = self._data()
        fixed = {name: w.value() for name, w in self._fixed_widgets.items()}
        try:
            result = fitting.fit(key, kind, x, y, method, fixed)
        except (ValueError, KeyError) as exc:
            self._output.setPlainText(f"Fit failed: {exc}")
            self._apply_button.setEnabled(False)
            return
        self._result = result
        lines = [f"method: {result.method}", f"residuals: {result.residuals:.6g}", ""]
        for name, value in result.parameters.items():
            lines.append(f"{name} = {value:.6g}")
        if key == "generalized_hoek_brown":
            lines.append("")
            lines.append("Note: apply fills the classic Hoek-Brown criterion (mb, s; a is fixed to 0.5 there).")
        self._output.setPlainText("\n".join(lines))
        self._apply_button.setEnabled(True)

    def _apply(self) -> None:
        if self._result is None:
            return
        window = self.parent()
        if hasattr(window, "apply_fit_parameters"):
            window.apply_fit_parameters(self._result)
        self.accept()
