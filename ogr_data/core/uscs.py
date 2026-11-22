"""USCS soil classifier (ASTM D2487) per the NRCS laboratory criteria.

Sources (suite bibliography):
- USDA NRCS NEH Part 631 Ch. 3, Figure 3-17 "USCS laboratory criteria"
  (limits as printed there: gravels Cu > 4, sands Cu > 6, 1 < Cc < 3,
  organic ratio LL(oven dry)/LL(air dry) < 0.7).
- USDA NRCS NEH Part 650 Ch. 4 (A-line equation in text:
  PI = 0.73 (LL - 20); U-line PI = 0.9 (LL - 8)).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
import json
from typing import Any


@dataclass(frozen=True)
class UsCSInput:
    """Laboratory data for classification (percentages by mass)."""

    fines_pct: float  # passing No. 200 sieve
    sand_pct: float  # of total sample, passing No. 4 and retained on No. 200
    cu: float | None = None  # D60/D10, clean coarse-grained soils
    cc: float | None = None  # D30^2 / (D10 D60)
    ll: float | None = None  # liquid limit
    pi: float | None = None  # plasticity index
    organic_ratio: float | None = None  # LL(oven dry) / LL(air dry)
    highly_organic: bool = False  # peat-like: color, odor, fibrous texture

    def __post_init__(self) -> None:
        total = self.fines_pct + self.sand_pct
        if not 0.0 <= self.fines_pct <= 100.0 or not 0.0 <= self.sand_pct <= 100.0:
            raise ValueError("percentages must be in [0, 100]")
        if total > 100.0 + 1e-9:
            raise ValueError("fines + sand exceed 100%")
        if self.ll is not None and self.ll < 0:
            raise ValueError("LL must be non-negative")
        if self.pi is not None and self.pi < 0:
            raise ValueError("PI must be non-negative")


@dataclass(frozen=True)
class UsCSResult:
    symbol: str
    group: str  # "gravel" | "sand" | "silt" | "clay" | "organic" | "peat"
    notes: tuple[str, ...] = ()


def a_line_pi(ll: float) -> float:
    """Plasticity index of the A-line at the given liquid limit."""

    return 0.73 * (ll - 20.0)


def u_line_pi(ll: float) -> float:
    """Plasticity index of the U-line (upper limit) at the given LL."""

    return 0.9 * (ll - 8.0)


def _above_a_line(ll: float, pi: float) -> bool:
    return pi > a_line_pi(ll)


def _fines_symbol(ll: float, pi: float) -> tuple[str, bool, str]:
    """Symbol of the fines fraction (M or C), (borderline PI 4-7, side)."""

    above = _above_a_line(ll, pi)
    if pi < 4.0 and not above:
        return "M", False, "below"
    if above and pi > 7.0:
        return "C", False, "above"
    # Borderline zone PI 4-7 (figure 3-17): dual symbols required.
    return ("C" if above else "M"), True, "above" if above else "below"


def classify(inp: UsCSInput) -> UsCSResult:
    """Classify a soil sample following NRCS figure 3-17."""

    notes: list[str] = []

    if inp.highly_organic:
        return UsCSResult("PT", "peat")

    if inp.fines_pct >= 50.0:
        if inp.ll is None or inp.pi is None:
            raise ValueError("LL and PI are required for fine-grained soils")
        ll, pi = inp.ll, inp.pi
        organic = inp.organic_ratio is not None and inp.organic_ratio < 0.7
        low = ll < 50.0
        above = _above_a_line(ll, pi)
        if low:
            if organic and not above and pi < 4.0:
                return UsCSResult("OL", "organic")
            if above and 4.0 <= pi <= 7.0:
                return UsCSResult("CL-ML", "clay", ("Borderline case: dual symbol (figure 3-17).",))
            if above and pi > 7.0:
                return UsCSResult("CL", "clay")
            return UsCSResult("ML", "silt")
        # high liquid limit
        if organic and not above and pi < 4.0:
            return UsCSResult("OH", "organic")
        if above:
            return UsCSResult("CH", "clay")
        return UsCSResult("MH", "silt")

    # Coarse-grained: fines < 50%.
    gravel_pct_of_coarse = 100.0 * (100.0 - inp.fines_pct - inp.sand_pct) / (100.0 - inp.fines_pct)
    is_gravel = gravel_pct_of_coarse >= 50.0
    base_letter = "G" if is_gravel else "S"

    if inp.fines_pct < 5.0:
        if inp.cu is None or inp.cc is None:
            raise ValueError("Cu and Cc are required for clean coarse-grained soils")
        cu_req = 4.0 if is_gravel else 6.0
        if inp.cu > cu_req and 1.0 < inp.cc < 3.0:
            return UsCSResult(f"{base_letter}W", "gravel" if is_gravel else "sand")
        return UsCSResult(f"{base_letter}P", "gravel" if is_gravel else "sand")

    if inp.fines_pct > 12.0:
        if inp.ll is None or inp.pi is None:
            raise ValueError("LL and PI are required when fines exceed 12%")
        sym, borderline, _ = _fines_symbol(inp.ll, inp.pi)
        if borderline:
            return UsCSResult(
                f"{base_letter}M-{base_letter}C",
                "gravel" if is_gravel else "sand",
                ("Borderline fines (PI 4-7): dual symbol required (figure 3-17).",),
            )
        return UsCSResult(f"{base_letter}{sym}", "gravel" if is_gravel else "sand")

    # 5-12% fines: dual symbols with the clean-gravel/sand base.
    if inp.cu is None or inp.cc is None or inp.ll is None or inp.pi is None:
        raise ValueError("Cu, Cc, LL and PI are required for 5-12% fines (dual symbols)")
    cu_req = 4.0 if is_gravel else 6.0
    well = inp.cu > cu_req and 1.0 < inp.cc < 3.0
    base = f"{base_letter}{'W' if well else 'P'}"
    sym, borderline, _ = _fines_symbol(inp.ll, inp.pi)
    if borderline:
        return UsCSResult(
            f"{base}-{base_letter}M/{base}-{base_letter}C",
            "gravel" if is_gravel else "sand",
            ("Borderline fines (PI 4-7): two dual symbols to consider (figure 3-17).",),
        )
    return UsCSResult(f"{base}-{base_letter}{sym}", "gravel" if is_gravel else "sand")


@lru_cache(maxsize=1)
def _properties() -> dict[str, Any]:
    ref = resources.files("ogr_data.data").joinpath("uscs_properties.json")
    return json.loads(ref.read_text(encoding="utf-8"))


def uscs_properties(symbol: str) -> dict[str, str]:
    """Engineering property card (figure 3-22) for the primary class symbol."""

    primary = symbol.split("-")[0].split("/")[0]
    card = _properties()["classes"].get(primary)
    if card is None:
        raise ValueError(f"unknown USCS class {primary!r}")
    return dict(card)


def uscs_properties_source() -> str:
    return str(_properties()["source"])
