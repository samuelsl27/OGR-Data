# SPDX-License-Identifier: AGPL-3.0-or-later
"""Results panel of the main window (spec 025b).

Shows what the selected material computes — the Hoek-Brown parameters of a
generalized Hoek-Brown material, the equivalent Mohr-Coulomb c and phi of
the other curved criteria — beside the graphs, so cause (the parameters on
the left) and effect stay in view together. The window computes the rows;
the panel only lays them out. It also echoes the stress sampler.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget

from .i18n import tr

_VALUE_STYLE = "font-family: Consolas, monospace;"


class ResultsPanel(QWidget):
    def __init__(self, copy_action=None, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[str, str]] = []
        self._pairs: list[tuple[QLabel, QLabel]] = []
        self._message = ""

        layout = QVBoxLayout(self)
        self._box = QGroupBox()
        box_layout = QVBoxLayout(self._box)
        self._heading = QLabel()
        self._heading.setWordWrap(True)
        box_layout.addWidget(self._heading)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 4, 0, 4)
        self._grid.setColumnStretch(1, 1)
        box_layout.addWidget(self._grid_host)
        self._note = QLabel()
        self._note.setWordWrap(True)
        box_layout.addWidget(self._note)
        self.copy_button = QPushButton(tr("Copy material"))
        if copy_action is not None:
            self.copy_button.clicked.connect(copy_action)
        box_layout.addWidget(self.copy_button)
        layout.addWidget(self._box)

        # spec 025b RF-8: the sampler's reading, also in the status bar
        self._sampler_box = QGroupBox(tr("Sampler"))
        sampler_layout = QVBoxLayout(self._sampler_box)
        self._sampler = QLabel()
        self._sampler.setWordWrap(True)
        self._sampler.setStyleSheet(_VALUE_STYLE)
        self._sampler.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sampler_layout.addWidget(self._sampler)
        self._sampler_box.setVisible(False)
        layout.addWidget(self._sampler_box)
        layout.addStretch(1)

    # ------------------------------------------------------------- results

    def set_results(self, heading: str, rows: list[tuple[str, str]], note: str = "") -> None:
        """Show ``rows`` of (label, formatted value) under ``heading``."""

        self._rows = list(rows)
        self._message = ""
        self._heading.setText(heading)
        self._fill_grid()
        self._note.setText(note)
        self._note.setVisible(bool(note))

    def set_message(self, heading: str, message: str) -> None:
        """No values to show: say why (a panel never stays silently empty)."""

        self._rows = []
        self._message = message
        self._heading.setText(heading)
        self._fill_grid()
        self._note.setText(message)
        self._note.setVisible(bool(message))

    def _fill_grid(self) -> None:
        # The label pairs are reused, not rebuilt: the panel is refilled at
        # every edit, and widgets waiting for deleteLater were still painted
        # under the new ones.
        while len(self._pairs) < len(self._rows):
            name = QLabel()
            name.setWordWrap(True)  # long Spanish labels wrap instead of widening the dock
            shown = QLabel()
            shown.setStyleSheet(_VALUE_STYLE)
            shown.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            shown.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row = len(self._pairs)
            self._grid.addWidget(name, row, 0)
            self._grid.addWidget(shown, row, 1)
            self._pairs.append((name, shown))
        for index, (name, shown) in enumerate(self._pairs):
            used = index < len(self._rows)
            if used:
                name.setText(self._rows[index][0])
                shown.setText(self._rows[index][1])
            name.setVisible(used)
            shown.setVisible(used)
        self._grid_host.setVisible(bool(self._rows))

    def rows(self) -> list[tuple[str, str]]:
        return list(self._rows)

    def results_text(self) -> str:
        """The panel as plain text: one ``label = value`` line per row, or the message."""

        if not self._rows:
            return self._message
        return "\n".join(f"{label} = {value}" for label, value in self._rows)

    # ------------------------------------------------------------- sampler

    def set_sampler_text(self, text: str) -> None:
        """Show the sampler's reading; empty text hides the section."""

        self._sampler.setText(text.replace("   ", "\n"))
        self._sampler_box.setVisible(bool(text))

    def sampler_text(self) -> str:
        return self._sampler.text() if self._sampler_box.isVisibleTo(self) else ""
