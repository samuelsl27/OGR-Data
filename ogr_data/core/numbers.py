# SPDX-License-Identifier: AGPL-3.0-or-later
"""How numbers and symbols are written on screen (spec 025e).

One place for the format of every value the window, the dialogs and the
report show, so the panel and the report cannot disagree:

- up to 6 significant figures, without padding zeros, as RSData 1.009
  shows its fields (``100000``, ``40.5662``, ``0.000233284``); angles with
  4 decimals; never scientific notation for the usual magnitudes, only
  below 1e-4 (``s`` of a very poor rock mass) and above 1e9;
- the noise of a fit (|value| < 1e-12) is 0.

Files, clipboard and CSV never use this: they keep every decimal.

:func:`symbols` writes the ASCII names of the code and of the CSV columns
(``sigma3``, ``phi``, ``deg``) as the screen shows them (σ₃, φ, °). It
does not know languages: it acts on whole words, so the Spanish text of
a label is written the same way.
"""

from __future__ import annotations

import math
import re

SIGNIFICANT = 6
ANGLE_DECIMALS = 4
ZERO = 1e-12


def _strip(text: str) -> str:
    if "." in text and "e" not in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def format_number(value, kind: str = "general") -> str:
    """``value`` as the screen shows it; ``kind`` is "general" or "angle"."""

    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(value):
        return "-"
    if abs(value) < ZERO:
        return "0"
    if kind == "angle":
        return _strip(f"{value:.{ANGLE_DECIMALS}f}")
    magnitude = abs(value)
    if magnitude < 1e-4 or magnitude >= 1e9:
        return f"{value:.{SIGNIFICANT}g}"
    decimals = max(0, SIGNIFICANT - 1 - math.floor(math.log10(magnitude)))
    return _strip(f"{value:.{decimals}f}")


# whole-word replacements, longest first
_SYMBOLS = [
    (r"\bsigma'1\b", "σ'₁"),
    (r"\bsigma'3\b", "σ'₃"),
    (r"\bsigma'a\b", "σ'a"),
    (r"\bsigma3max\b", "σ₃max"),
    (r"\bsig3max\b", "σ₃max"),
    (r"\bsigma1\b", "σ₁"),
    (r"\bsigma3\b", "σ₃"),
    (r"\bsigma_n\b", "σn"),
    (r"\bsigci\b", "σci"),
    (r"\bsigcm\b", "σcm"),
    (r"\bsigt\b", "σt"),
    (r"\bsigc\b", "σc"),
    (r"\bsigma\b", "σ"),
    (r"\bphi_b\b", "φb"),
    (r"\bphi_r\b", "φr"),
    (r"\bphi b\b", "φb"),
    (r"\bphi r\b", "φr"),
    (r"\bphi\b", "φ"),
    (r"\btau\b", "τ"),
    (r" deg\b", "°"),
    (r"\(deg\)", "(°)"),
]
_COMPILED = [(re.compile(pattern), repl) for pattern, repl in _SYMBOLS]


def symbols(text: str) -> str:
    """ASCII names written with their symbols: sigma3 → σ₃, phi → φ, " deg" → "°"."""

    for pattern, repl in _COMPILED:
        text = pattern.sub(repl, text)
    return text
