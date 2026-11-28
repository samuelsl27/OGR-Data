# SPDX-License-Identifier: AGPL-3.0-or-later
"""Layout pieces of the sidebar that follows its splitter (spec 029)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFormLayout, QScrollArea


def responsive_form(form: QFormLayout) -> QFormLayout:
    """Fields take the width there is; a row that does not fit puts its label above (spec 029 RF-3, RF-4).

    Cutting the label or squeezing the field below its minimum is what made
    «Ángulo de rozamiento de pic» and «0,01(» (UX review, 2026-11-28).
    """

    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    return form


class SidebarScroll(QScrollArea):
    """Vertical scroll area as wide as its content needs, never scrolled sideways (spec 029 RF-4, RF-5).

    A plain ``QScrollArea`` lets the splitter shrink it to nothing and then
    shows a horizontal bar; this one tells the splitter the content's own
    minimum and preferred widths, plus the vertical bar's.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _chrome(self) -> int:
        return 2 * self.frameWidth() + self.verticalScrollBar().sizeHint().width()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt)
        hint = super().minimumSizeHint()
        if self.widget() is not None:
            hint.setWidth(self.widget().minimumSizeHint().width() + self._chrome())
        return hint

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt)
        hint = super().sizeHint()
        if self.widget() is not None:
            hint.setWidth(self.widget().sizeHint().width() + self._chrome())
        return hint
