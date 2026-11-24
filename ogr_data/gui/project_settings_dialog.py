# SPDX-License-Identifier: AGPL-3.0-or-later
"""File > Project Settings (spec 025b): the project title and the stress unit.

Both left the sidebar, which now holds only the material; a project
settings dialog is where engineering programs usually keep them.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit

from ..core import units
from .i18n import tr


class ProjectSettingsDialog(QDialog):
    def __init__(self, title: str, stress_unit: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Project Settings"))
        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText(tr("Project title"))
        self.title_edit.setMinimumWidth(280)
        self.unit_combo = QComboBox()
        for unit in units.STRESS_FACTORS:
            self.unit_combo.addItem(unit, unit)
        self.unit_combo.setCurrentIndex(max(0, self.unit_combo.findData(stress_unit)))

        form = QFormLayout(self)
        form.addRow(tr("Project title"), self.title_edit)
        form.addRow(tr("Stress unit"), self.unit_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def title(self) -> str:
        return self.title_edit.text().strip()

    def stress_unit(self) -> str:
        return str(self.unit_combo.currentData())
