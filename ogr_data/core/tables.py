"""Bibliographic tables loader (spec 003). Data lives in ogr_data/data/*.json
with a source citation per table; see the suite bibliography for the
original documents."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


@lru_cache(maxsize=None)
def _load(name: str) -> dict[str, Any]:
    ref = resources.files("ogr_data.data").joinpath(name)
    return json.loads(ref.read_text(encoding="utf-8"))


def rock_strength_grades() -> dict[str, Any]:
    """Table 2 of Hoek ch.11: field estimates of uniaxial compressive strength."""

    return _load("rock_strength_grades.json")


def mi_values() -> dict[str, Any]:
    """Table 3 of Hoek ch.11: values of the constant mi for intact rock."""

    return _load("mi_values.json")


def gsi_chart() -> dict[str, Any]:
    """Hoek & Marinos (2000) general GSI chart (structure x surface)."""

    return _load("gsi_chart.json")


def gsi_range(structure: str, surface: str) -> tuple[float, float] | None:
    """Indicative GSI range for a structure/surface combination, or None."""

    cell = gsi_chart()["cells"].get(f"{structure}|{surface}")
    if cell is None:
        return None
    return float(cell[0]), float(cell[1])


def gsi_quantified() -> dict[str, Any]:
    """Hoek, Carter & Diederichs (2013): quantified GSI chart and Tables 1-3 (spec 022)."""

    return _load("gsi_quantified.json")


def modulus_ratio() -> dict[str, Any]:
    """Practical Rock Engineering (2023) Fig. 13: modulus ratio MR = Ei/sigci (spec 022)."""

    return _load("modulus_ratio.json")


def disturbance_factor() -> dict[str, Any]:
    """Practical Rock Engineering (2023) Fig. 9: disturbance factor D (spec 022)."""

    return _load("disturbance_factor.json")
