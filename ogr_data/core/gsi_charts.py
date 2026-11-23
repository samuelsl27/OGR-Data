"""Digitized GSI charts: click on the chart -> GSI (spec 022).

Three charts redrawn from numeric data only (no images are shipped):

- ``general_2000``: Marinos & Hoek (2000), *GSI for jointed rock masses*
  (vector PDF, max. error 1.3 GSI).
- ``flysch_2000``: Marinos & Hoek (2000/2001), *GSI for heterogeneous rock
  masses such as flysch*, types A-H (Practical Rock Engineering ch. 11,
  Table 6; max. error 1.3).
- ``heterogeneous_marinos_2007``: V. Marinos (2007), as published in
  Marinos (2014, JRMGE 6(3), Fig. 3), types I-XI (max. error 1.3).

Data: ``ogr_data/data/gsi_digitized_<chart_id>.json``; digitization,
control points and scripts in ``Referencias/Bibliografia/Rocas/flysch 2000
y heterogénea 2013``. Frame (u, v): u = 0 left edge of VERY GOOD, 1 right
edge of VERY POOR; v = 0 top of the first structure row, 1 bottom of the
last. Each JSON carries the chart texts in English (literal) and Spanish
(technical translation) under ``i18n.<lang>`` with identical keys.

Interpolation (same as the digitization's ``gsi_lib.Interpolator``): linear
between the two isolines that enclose the point, weighted by the
perpendicular distance to each; isolines are extended by half-lines only
for that computation; beyond the outermost isoline the local spacing is
used and the result is clipped to 0-100; inside N/A cells -> None.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from . import tables

CHART_IDS: tuple[str, ...] = ("general_2000", "flysch_2000", "heterogeneous_marinos_2007")
LANGUAGES: tuple[str, ...] = ("en", "es")


def chart(chart_id: str) -> dict[str, Any]:
    if chart_id not in CHART_IDS:
        raise KeyError(f"unknown GSI chart {chart_id!r}; expected one of {CHART_IDS}")
    return tables._load(f"gsi_digitized_{chart_id}.json")


def texts(chart_id: str, lang: str = "en") -> dict[str, Any]:
    """Chart texts (title, columns, rows, types, notes) in ``lang`` ('en' literal, 'es')."""

    i18n = chart(chart_id)["i18n"]
    return i18n[lang] if lang in i18n else i18n[i18n.get("default", "en")]


# ------------------------------------------------------------------ geometry


def _signed_distance(p: tuple[float, float], pts: list[list[float]]) -> tuple[float, float]:
    """Perpendicular distance to the polyline (first/last segments extended) and side (+1/-1/0)."""

    px, py = p
    best = (1e9, 0.0)
    n = len(pts)
    for i in range(n - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        abx, aby = bx - ax, by - ay
        l2 = abx * abx + aby * aby
        if l2 < 1e-16:
            continue
        t = ((px - ax) * abx + (py - ay) * aby) / l2
        if i > 0:
            t = max(t, 0.0)  # only the first segment extends backwards
        if i < n - 2:
            t = min(t, 1.0)  # only the last segment extends forwards
        qx, qy = ax + t * abx, ay + t * aby
        dist = math.hypot(px - qx, py - qy)
        if dist < best[0] - 1e-12:
            cross = abx * (py - ay) - aby * (px - ax)
            best = (dist, math.copysign(1.0, cross) if dist > 1e-12 else 0.0)
    return best


def point_in_polygon(p: tuple[float, float], poly: list[list[float]]) -> bool:
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


class Interpolator:
    """GSI at (u, v) of one digitized chart."""

    def __init__(self, data: dict[str, Any]) -> None:
        lines = sorted(data["isolines"], key=lambda line: -line["gsi"])
        self.values = [float(line["gsi"]) for line in lines]
        self.lines = [line["points"] for line in lines]
        self.na = [zone["polygon"] for zone in data.get("not_applicable", [])]
        # the (0, 0) corner (VERY GOOD, top row) is always on the high-GSI side
        sides = [_signed_distance((0.0, 0.0), pts)[1] for pts in self.lines]
        self.high_side = [s if s != 0 else 1.0 for s in sides]

    def is_na(self, u: float, v: float) -> bool:
        return any(point_in_polygon((u, v), zone) for zone in self.na)

    def gsi(self, u: float, v: float) -> tuple[float | None, str]:
        """(value, how): how is 'on_line', 'interp', 'extrap' or 'na' (value None)."""

        if self.is_na(u, v):
            return None, "na"
        sd = []
        for pts, high in zip(self.lines, self.high_side):
            d, s = _signed_distance((u, v), pts)
            sd.append((d, d < 1e-9 or s == high))  # True -> on the high-GSI side (or on it)
        for value, (d, _) in zip(self.values, sd):
            if d < 1e-9:
                return value, "on_line"
        n = len(sd)
        for i in range(n - 1):
            if not sd[i][1] and sd[i + 1][1]:
                d1, d2 = sd[i][0], sd[i + 1][0]
                return self.values[i] + (self.values[i + 1] - self.values[i]) * d1 / (d1 + d2), "interp"
        if sd[0][1]:  # above the highest isoline
            i, j, sign = 0, 1, 1.0
        else:  # below the lowest
            i, j, sign = n - 1, n - 2, -1.0
        d_i = sd[i][0]
        gap = abs(_signed_distance((u, v), self.lines[j])[0] - d_i) or 1e-6
        value = self.values[i] + sign * abs(self.values[i] - self.values[j]) * d_i / gap
        return min(100.0, max(0.0, value)), "extrap"


@lru_cache(maxsize=None)
def interpolator(chart_id: str) -> Interpolator:
    return Interpolator(chart(chart_id))


def gsi_at(chart_id: str, u: float, v: float) -> float | None:
    """GSI at (u, v) of the chart, None outside the chart or in a not-applicable cell."""

    if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
        return None
    return interpolator(chart_id).gsi(u, v)[0]


# ------------------------------------------------------------------ picking


@dataclass
class ChartPick:
    """What a click on the chart reads."""

    chart_id: str
    u: float
    v: float
    gsi: float | None
    how: str  # 'interp' | 'on_line' | 'extrap' | 'na' | 'outside'
    column: str | None = None  # key
    row: str | None = None  # key
    types: list[str] = field(default_factory=list)  # rock-mass type(s) whose band holds the point
    type_inferred: bool = False  # split of a continuous band at mid-label (not drawn on the chart)
    type_fringe: bool = False  # only in the faded fringe of the band

    def summary(self, lang: str = "en") -> str:
        t = texts(self.chart_id, lang)
        es = lang == "es"
        if self.how == "outside":
            return "Fuera de la carta." if es else "Outside the chart."
        parts = []
        if self.row is not None and not self.types:  # the type already names the structure band
            parts.append(t["rows"][self.row]["label"])
        if self.column is not None:
            parts.append(t["columns"][self.column]["label"])
        if self.types:
            word = "tipo" if es else "type"
            label = f"{word} {', '.join(self.types)}"
            notes = []
            if self.type_inferred:
                notes.append("reparto inferido" if es else "inferred split")
            if self.type_fringe:
                notes.append("orla" if es else "fringe")
            parts.append(label + (f" ({'; '.join(notes)})" if notes else ""))
        if self.gsi is None:
            parts.append(t.get("na_meaning") or t.get("na_label") or "N/A")
        elif self.how == "extrap":
            parts.append("extrapolado" if es else "extrapolated")
        return " — ".join(parts)


def _region_types(data: dict[str, Any], u: float, v: float, shading: str) -> tuple[list[str], bool]:
    for split in (False, True):  # whole regions first, then the inferred split
        for region in data.get("regions", []):
            if region["shading"] != shading or region.get("combined"):
                continue
            if bool(region.get("split_inferred")) != split:
                continue
            if point_in_polygon((u, v), region["polygon"]):
                return [region["label"]], split
    return [], False


def pick(chart_id: str, u: float, v: float) -> ChartPick:
    data = chart(chart_id)
    if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
        return ChartPick(chart_id, u, v, None, "outside")
    value, how = interpolator(chart_id).gsi(u, v)
    column = next((c["key"] for c in data["columns"] if c["u0"] <= u <= c["u1"]), None)
    row = next((r["key"] for r in data["rows"] if r["v0"] <= v <= r["v1"]), None)
    types, inferred = _region_types(data, u, v, "core")
    fringe = False
    if not types:
        types, inferred = _region_types(data, u, v, "fringe")
        fringe = bool(types)
    return ChartPick(chart_id, u, v, value, how, column, row, types, inferred, fringe)


def type_center(chart_id: str, label: str) -> tuple[float, float] | None:
    """Label position of a rock-mass type (e.g. 'C' or 'VII'), for a quick pick by type."""

    for region in chart(chart_id).get("regions", []):
        if region["label"] == label and region.get("label_at"):
            u, v = region["label_at"]
            return float(u), float(v)
    return None


def chart_types(chart_id: str) -> list[str]:
    """Rock-mass types of the chart, in chart order (empty for the general chart)."""

    return list(chart(chart_id).get("type_descriptions", {}).keys())
