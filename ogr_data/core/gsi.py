"""Quantified GSI (spec 022).

Hoek, Carter & Diederichs (2013), *Quantification of the Geological
Strength Index chart*, ARMA 13-672 (Referencias/Bibliografia/General/2013-Quantification-of-the-GSI-Chart.pdf):

    GSI = 1.5 JCond89 + RQD/2                          (eq. 1)
    GSI = 2 JCond76 + RQD/2      (JCond89 = 1.3 JCond76, eq. 2)
    GSI = 52 (Jr/Ja)/(1 + Jr/Ja) + RQD/2                (eq. 3)
    RQD = 100 e^(-0.1 lambda) (0.1 lambda + 1)          (eq. 4)
    RQD = 115 - 3.3 Jv  |  RQD = 110 - 2.5 Jv           (eqs. 5, 6)

JCond89 can also be built from the five ratings of Table 1 (persistence,
aperture, roughness, infilling, weathering; 0-6 each, sum 0-30).

The quantified chart (Figure 5) plots A = 1.5 JCond89 (45 -> 0) against
B = RQD/2 (0 -> 40); GSI is A + B, so a point on the chart gives the GSI
directly (chart_gsi). Results are not truncated (the reference program appears to
truncate the displayed value).
"""

from __future__ import annotations

import math

from . import tables

JCOND89_MAX = 30.0
JCOND76_MAX = 25.0
CHART_A_MAX = 45.0  # 1.5 x 30
CHART_B_MAX = 40.0  # the quantified chart spans RQD/2 = 0..40


def _check_rqd(rqd: float) -> float:
    if not 0.0 <= rqd <= 100.0:
        raise ValueError("RQD must be between 0 and 100 %")
    return float(rqd)


def gsi_from_jcond89(jcond89: float, rqd: float) -> float:
    """Eq. 1."""

    if not 0.0 <= jcond89 <= JCOND89_MAX:
        raise ValueError("JCond89 must be between 0 and 30")
    return 1.5 * jcond89 + _check_rqd(rqd) / 2.0


def gsi_from_jcond76(jcond76: float, rqd: float) -> float:
    """Eq. 2, as published (2 JCond76; the exact substitution 1.5 x 1.3 = 1.95)."""

    if not 0.0 <= jcond76 <= JCOND76_MAX:
        raise ValueError("JCond76 must be between 0 and 25")
    return 2.0 * jcond76 + _check_rqd(rqd) / 2.0


def jcond89_from_jr_ja(jr: float, ja: float) -> float:
    """JCond89 = 35 (Jr/Ja)/(1 + Jr/Ja)."""

    if jr <= 0.0 or ja <= 0.0:
        raise ValueError("Jr and Ja must be positive")
    q = jr / ja
    return 35.0 * q / (1.0 + q)


def gsi_from_jr_ja(jr: float, ja: float, rqd: float) -> float:
    """Eq. 3: 52 (Jr/Ja)/(1 + Jr/Ja) + RQD/2 (as published)."""

    if jr <= 0.0 or ja <= 0.0:
        raise ValueError("Jr and Ja must be positive")
    q = jr / ja
    return 52.0 * q / (1.0 + q) + _check_rqd(rqd) / 2.0


def jcond89_from_ratings(persistence: float, aperture: float, roughness: float, infilling: float, weathering: float) -> float:
    """Sum of the Table 1 guideline ratings (each 0-6)."""

    ratings = (persistence, aperture, roughness, infilling, weathering)
    if any(not 0.0 <= r <= 6.0 for r in ratings):
        raise ValueError("each JCond89 guideline rating is between 0 and 6")
    return float(sum(ratings))


def rqd_from_lambda(discontinuities_per_m: float) -> float:
    """Eq. 4 (Priest & Hudson 1976)."""

    if discontinuities_per_m < 0.0:
        raise ValueError("lambda must be >= 0")
    x = 0.1 * discontinuities_per_m
    return 100.0 * math.exp(-x) * (x + 1.0)


def rqd_from_jv(jv: float, palmstrom_2005: bool = True) -> float:
    """Eq. 6 (Palmstrom 2005, default) or eq. 5 (1982), clipped to 0-100."""

    if jv < 0.0:
        raise ValueError("Jv must be >= 0")
    rqd = 110.0 - 2.5 * jv if palmstrom_2005 else 115.0 - 3.3 * jv
    return min(100.0, max(0.0, rqd))


def chart_gsi(a: float, b: float) -> float | None:
    """GSI at a point of the quantified chart: A = 1.5 JCond89, B = RQD/2.

    None outside the chart (A in 0..45, B in 0..40).
    """

    if not (0.0 <= a <= CHART_A_MAX and 0.0 <= b <= CHART_B_MAX):
        return None
    return a + b


def chart_row(b: float) -> dict | None:
    """Structure band of Figure 5 at RQD/2 = b (approximate positions)."""

    for row in tables.gsi_quantified()["chart"]["rows"]:
        if row["y_lo"] <= b <= row["y_hi"]:
            return row
    return None
