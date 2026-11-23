"""Shared helpers of the operations: units, validation and summaries.

API units (all operations, in and out): stresses in kPa, unit weight in
kN/m3, lengths in m, angles in degrees. The registry already stores kPa
and degrees; sigma3max (MPa in the core), computed values (MPa) and the
application's unit weight (MN/m3) are converted here and only here.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ...core.models import CRITERIA, Criterion
from ...core.project import Material, Project
from ..errors import InvalidArgument, choice, unknown
from ..workspace import get_material, material_index  # noqa: F401 (re-exported for the operations)

UNITS = "kPa (stresses), kN/m3 (unit weight), m, degrees"
MPA_TO_KPA = 1000.0


def number(name: str, value, *, lo: float | None = None, hi: float | None = None, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidArgument(f"{name} must be a number; got {value!r}.")
    value = float(value)
    if not math.isfinite(value):
        raise InvalidArgument(f"{name} must be finite; got {value!r}.")
    if positive and value <= 0.0:
        raise InvalidArgument(f"{name} must be > 0; got {value:g}.")
    if lo is not None and value < lo:
        raise InvalidArgument(f"{name} must be >= {lo:g}; got {value:g}.")
    if hi is not None and value > hi:
        raise InvalidArgument(f"{name} must be <= {hi:g}; got {value:g}.")
    return value


def criterion(key: str) -> Criterion:
    if key not in CRITERIA:
        raise unknown("criterion", key, CRITERIA)
    return CRITERIA[key]


def validate_parameters(key: str, params: dict | None) -> dict:
    """Registry parameters checked against the criterion's fields (names, types, choices)."""

    crit = criterion(key)
    fields = {f.key: f for f in crit.fields}
    out: dict[str, Any] = {}
    for name, value in (params or {}).items():
        if name not in fields:
            raise unknown(f"parameter of {key}", name, fields)
        f = fields[name]
        if f.kind == "bool":
            if not isinstance(value, bool):
                raise InvalidArgument(f"{name} is true/false; got {value!r}.")
            out[name] = value
        elif f.kind == "enum":
            out[name] = choice(name, value, f.options)
        elif f.kind == "table":
            if not isinstance(value, (list, tuple)):
                raise InvalidArgument(f"{name} is a table: a list of rows [{', '.join(f.options)}].")
            rows = []
            for row in value:
                if not isinstance(row, (list, tuple)) or len(row) != len(f.options):
                    raise InvalidArgument(f"each row of {name} has {len(f.options)} values ({', '.join(f.options)}); got {row!r}.")
                rows.append([number(f"{name} value", v) for v in row])
            out[name] = rows
        else:
            out[name] = number(name, value)
    return out


def fields_schema(key: str) -> list[dict]:
    return [
        {"key": f.key, "label": f.label, "unit": f.unit, "kind": f.kind,
         "default": [list(r) for r in f.default] if f.kind == "table" else f.default,
         **({"options": list(f.options)} if f.options else {})}
        for f in CRITERIA[key].fields
    ]


def kpa_dict(values: dict[str, float]) -> dict[str, float]:
    """Core results (``*_mpa`` keys in MPa) as API results (``*_kpa``)."""

    out = {}
    for k, v in values.items():
        if v is None:
            continue
        if k.endswith("_mpa"):
            out[k[:-4] + "_kpa"] = float(v) * MPA_TO_KPA
        else:
            out[k] = float(v)
    return out


def sample(x: np.ndarray, y: np.ndarray, n: int) -> tuple[list[float], list[float]]:
    """About ``n`` evenly spaced points of a core curve (MPa), in kPa."""

    idx = np.unique(np.linspace(0, len(x) - 1, max(2, int(n))).round().astype(int))
    return [float(v) for v in np.asarray(x)[idx] * MPA_TO_KPA], [float(v) for v in np.asarray(y)[idx] * MPA_TO_KPA]


def material_summary(project: Project, index: int) -> dict:
    m = project.materials[index]
    return {"index": index, "name": m.name, "criterion": m.criterion, "selected": index == project.selected}


def material_detail(project: Project, index: int) -> dict:
    m: Material = project.materials[index]
    crit = CRITERIA[m.criterion]
    return {
        "index": index,
        "name": m.name,
        "criterion": m.criterion,
        "criterion_label": crit.label,
        "category": crit.category,
        "envelope": crit.envelope,
        "parameters": {k: v for k, v in m.parameters.items()},
        "parameter_units": {f.key: f.unit for f in crit.fields if f.unit},
        "sig3max_kpa": m.sig3max_mpa * MPA_TO_KPA,
        "application": {
            "mode": m.application.mode,
            "unit_weight_kn_m3": m.application.unit_weight * 1000.0,
            "depth_m": m.application.depth,
        },
        "color": m.color,
        "symbol": m.symbol,
        "visible": m.visible,
        "stiffness": dict(m.stiffness),
        "failure_states": [{"name": s.name, "test_type": s.test_type, "points": len(s.points) + len(s.tensors)} for s in m.failure_states],
        "stress_paths": [{"name": p.name, "test_type": p.test_type, "steps": len(p.steps)} for p in m.stress_paths],
        "test_simulations": [{"name": t.name, "test_type": t.test_type} for t in m.test_simulations],
        "selected": index == project.selected,
    }


def project_summary(handle) -> dict:
    p = handle.project
    return {
        "project_id": handle.id,
        "title": p.title,
        "path": str(handle.path) if handle.path else None,
        "display_stress_unit": p.stress_unit,
        "materials": [material_summary(p, i) for i in range(len(p.materials))],
        "unsaved_changes": handle.history.modified if handle.history is not None else None,
        "undo": handle.history.undo_text if handle.history is not None else "",
        "units": UNITS,
    }


def named(items, name: str, kind: str):
    """Index of the item called ``name`` in ``items`` (by .name), or raise with suggestions."""

    names = [i.name for i in items]
    if name in names:
        return names.index(name)
    raise unknown(kind, name, names)
