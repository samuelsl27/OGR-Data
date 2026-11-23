"""Table-valued material parameter (spec 013b: tabular hardening laws).

A button in the parameter form showing the number of rows; it opens a table
editor (cut / copy / paste / import / export as in the failure-state tables).
Rows are stored in registry units (kPa for stress columns).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QPushButton, QVBoxLayout

from .states_dialog import PointTable


class TableField(QPushButton):
    changed = Signal()

    def __init__(self, title: str, columns: tuple[str, ...], stress_columns: tuple[bool, ...], rows, scale_unit) -> None:
        super().__init__()
        self._title = title
        self._columns = columns
        self._stress = stress_columns or tuple(False for _ in columns)
        self._scale_unit = scale_unit  # callable -> (kPa display scale, unit)
        self._rows = [list(map(float, r)) for r in rows]
        self.clicked.connect(self.edit)
        self._refresh_text()

    def _refresh_text(self) -> None:
        n = len(self._rows)
        self.setText(f"Edit table ({n} row{'s' if n != 1 else ''})…")

    def value(self) -> list[list[float]]:
        return [list(r) for r in self._rows]

    def setValue(self, rows) -> None:
        self._rows = [list(map(float, r)) for r in rows]
        self._refresh_text()
        self.changed.emit()

    def _headers_scales(self):
        scale, unit = self._scale_unit()
        headers = [f"{c} ({unit})" if s else c for c, s in zip(self._columns, self._stress)]
        scales = [scale if s else 1.0 for s in self._stress]
        return headers, scales

    def editor(self, parent=None) -> tuple[QDialog, PointTable]:
        headers, scales = self._headers_scales()
        dialog = QDialog(parent or self)
        dialog.setWindowTitle(self._title)
        dialog.resize(560, 360)
        table = PointTable(headers, scales)
        table.set_rows(self._rows)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(dialog.accept)
        box.rejected.connect(dialog.reject)
        layout = QVBoxLayout(dialog)
        layout.addWidget(table, stretch=1)
        layout.addWidget(box)
        return dialog, table

    def edit(self) -> None:
        dialog, table = self.editor()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            rows = table.rows()
        except ValueError as exc:
            QMessageBox.warning(self, self._title, str(exc))
            return
        if not rows:
            QMessageBox.warning(self, self._title, "The table needs at least one row.")
            return
        self.setValue(sorted((list(r[: len(self._columns)]) for r in rows), key=lambda r: r[0]))
