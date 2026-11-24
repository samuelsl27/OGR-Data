# SPDX-License-Identifier: AGPL-3.0-or-later
"""Help > Keyboard Shortcuts (F1, spec 025c).

The table is read from the menu bar when the dialog opens, so it cannot
drift from the shortcuts the program really has. Non-modal: it can stay
open beside the window.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QVBoxLayout

from .accelerators import plain
from .i18n import tr


def _shortcut_rows(container) -> list[tuple[str, str]]:
    rows = []
    for action in container.actions():
        if action.menu() is not None:
            rows += _shortcut_rows(action.menu())
        elif not action.isSeparator():
            keys = ", ".join(s.toString() for s in action.shortcuts() if not s.isEmpty())
            if keys:
                rows.append((plain(action.text()), keys))
    return rows


class ShortcutsDialog(QDialog):
    def __init__(self, menu_bar, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Keyboard Shortcuts"))
        self.setModal(False)
        self._rows = _shortcut_rows(menu_bar)
        table = QTableWidget(len(self._rows), 2)
        table.setHorizontalHeaderLabels([tr("Action"), tr("Shortcut")])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, (name, keys) in enumerate(self._rows):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(keys))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout = QVBoxLayout(self)
        layout.addWidget(table)
        layout.addWidget(buttons)
        self.resize(420, 420)

    def rows(self) -> list[tuple[str, str]]:
        return list(self._rows)
