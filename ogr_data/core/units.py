"""Display unit conversion layer (spec 017).

The core computes internally in MPa and the registry (core/models.py) and
the clipboard contract (spec 005) are defined in kPa; both are unchanged.
This module centralizes the conversion between internal MPa values and
the user-selected display unit, applied only at the UI boundary
(spinboxes, output labels, plot axes, status messages).

display value = internal MPa value * factor
"""

from __future__ import annotations

STRESS_FACTORS: dict[str, float] = {
    "MPa": 1.0,
    "kPa": 1000.0,
}

UNIT_WEIGHT_FACTORS: dict[str, float] = {
    "MN/m3": 1.0,
    "kN/m3": 1000.0,
}

DEFAULT_STRESS_UNIT = "kPa"


def stress_factor(unit: str) -> float:
    """Display factor for a stress unit: display = MPa * factor."""

    try:
        return STRESS_FACTORS[unit]
    except KeyError:
        raise ValueError(f"unknown stress unit {unit!r}") from None


def to_display(mpa_value: float, unit: str) -> float:
    """Internal MPa value in the display unit."""

    return mpa_value * stress_factor(unit)


def from_display(display_value: float, unit: str) -> float:
    """Display-unit value as internal MPa."""

    return display_value / stress_factor(unit)


def stress_text(mpa_value: float, unit: str, decimals: int | None = None) -> str:
    """Formatted stress for UI messages: '<value> <unit>'.

    Without ``decimals``, the screen format of spec 025e (up to 6
    significant figures, no padding zeros).
    """

    from .numbers import format_number

    shown = to_display(mpa_value, unit)
    text = format_number(shown) if decimals is None else f"{shown:.{decimals}f}"
    return f"{text} {unit}"
