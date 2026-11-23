"""Barton-Bandis input estimates and typical soil strengths (spec 018).

Barton-Bandis (Hoek, Practical Rock Engineering 2023, chapter on the
shear strength of discontinuities; Referencias/Bibliografia/Rocas):

    phi_r = (phi_b - 20) + 20 r / R                         (eq. 5)
    JRC_n = JRC_0 (L_n / L_0) ** (-0.02 JRC_0)              (eq. 6)
    JCS_n = JCS_0 (L_n / L_0) ** (-0.03 JRC_0)              (eq. 7)

r: Schmidt rebound on wet weathered joint surfaces, R: on dry unweathered
sawn surfaces; JRC_0, JCS_0 at laboratory scale L_0 = 100 mm, JRC_n and
JCS_n at the in-situ block size L_n (Barton and Bandis 1982).

Typical basic friction angles: FHWA-TS-89-045 (1989), after Barton.
Typical strengths of compacted soils by USCS group: UFC 3-220-01N (2005)
Table 8-3.1 (USBR data).
"""

from __future__ import annotations

from . import tables

LAB_SCALE_M = 0.1  # L0 = 100 mm


def phi_r_from_schmidt(phi_b_deg: float, r: float, big_r: float) -> float:
    """Residual friction angle from the basic angle and Schmidt rebounds (eq. 5)."""

    if big_r <= 0 or r < 0:
        raise ValueError("Schmidt rebound numbers must be positive (R > 0)")
    return (phi_b_deg - 20.0) + 20.0 * r / big_r


def _scale_check(length_m: float) -> None:
    if length_m <= 0:
        raise ValueError("lengths must be positive")


def jrc_scaled(jrc0: float, length_m: float, lab_length_m: float = LAB_SCALE_M) -> float:
    """JRC at the in-situ block size (eq. 6)."""

    _scale_check(length_m)
    _scale_check(lab_length_m)
    return jrc0 * (length_m / lab_length_m) ** (-0.02 * jrc0)


def jcs_scaled(jcs0: float, jrc0: float, length_m: float, lab_length_m: float = LAB_SCALE_M) -> float:
    """JCS at the in-situ block size (eq. 7); jcs0 in any stress unit."""

    _scale_check(length_m)
    _scale_check(lab_length_m)
    return jcs0 * (length_m / lab_length_m) ** (-0.03 * jrc0)


# ------------------------------------------------- compacted soils (UFC)

EQUIVALENT_SYMBOLS = {"CL-ML": "ML-CL", "SC-SM": "SM-SC"}


def compacted_properties(symbol: str) -> dict | None:
    """Row of UFC 3-220-01N Table 8-3.1 for a USCS symbol (or its equivalent dual symbol)."""

    rows = {r["symbol"]: r for r in tables.uscs_compacted_properties()["values"]}
    symbol = symbol.strip().upper()
    return rows.get(symbol) or rows.get(EQUIVALENT_SYMBOLS.get(symbol, ""))


def phi_value(text: str | None) -> tuple[float | None, bool]:
    """Numeric friction angle and whether it is a lower bound ('>38' -> 38, True)."""

    if text in (None, ""):
        return None, False
    text = str(text).strip()
    lower_bound = text.startswith(">")
    return float(text.lstrip(">").strip()), lower_bound


def mohr_coulomb_from_symbol(symbol: str, saturated: bool = True) -> dict:
    """Peak cohesion (kPa) and friction angle (deg) for a USCS group (effective envelope)."""

    row = compacted_properties(symbol)
    if row is None:
        raise ValueError(f"USCS group {symbol!r} is not listed in UFC 3-220-01N Table 8-3.1")
    phi, _ = phi_value(row["phi_effective"])
    cohesion = row["cohesion_saturated_kpa" if saturated else "cohesion_compacted_kpa"]
    if phi is None or cohesion is None:
        raise ValueError(f"UFC 3-220-01N Table 8-3.1 gives no strength data for {row['symbol']} (insufficient data)")
    return {"peak_cohesion": float(cohesion), "peak_friction": phi}
