# SPDX-License-Identifier: AGPL-3.0-or-later
"""Numeric field that shows numbers as the reference program does (spec 025e).

A ``QDoubleSpinBox`` pads every value to its fixed decimals
(``10.500000 kPa``) and rounds what is typed to them. This one shows the
value with :func:`ogr_data.core.numbers.format_number` (up to 6
significant figures, no padding; angles with 4 decimals) in the decimal
separator of the language, and keeps 10 decimals underneath, so a value
typed with more digits than shown is the value used and copied.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QDoubleSpinBox, QStyle, QStyleOptionSpinBox

from ..core.numbers import format_number
from .i18n import localize

PRECISION = 10

#: spec 029 RF-1: the longest text format_number gives (6 significant
#: figures in scientific notation, negative); the field is sized for it,
#: not for its range, which with 10 decimals asked for far more than it shows
_WIDEST = -1.23457e8


class NumberSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        super().setDecimals(PRECISION)

    def setDecimals(self, _decimals: int) -> None:  # noqa: N802 (Qt)
        """Ignored: the display is by significant figures and the value keeps full precision."""

        super().setDecimals(PRECISION)

    def textFromValue(self, value: float) -> str:  # noqa: N802 (Qt)
        kind = "angle" if self.suffix().strip() in ("°", "deg") else "general"
        return localize(format_number(value, kind))

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt)
        """As ``QAbstractSpinBox::sizeHint``, measured on the widest text shown (spec 029 RF-1)."""

        fm = self.fontMetrics()
        texts = (localize(format_number(_WIDEST)), self.lineEdit().text())
        fixed = self.prefix() + self.suffix() + " "
        width = max(fm.horizontalAdvance(fixed + text) for text in texts) + 2  # + cursor
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        contents = QSize(width, self.lineEdit().sizeHint().height())
        return self.style().sizeFromContents(QStyle.ContentsType.CT_SpinBox, option, contents, self)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt)
        return self.sizeHint()
