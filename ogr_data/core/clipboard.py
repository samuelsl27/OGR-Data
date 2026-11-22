"""Clipboard contract for material transfer (spec 005).

Open contract shared with OGR Slip2D and OGR FEM2D: a Unicode text
starting with "OGR-DATA-MATERIAL:" followed by JSON. Parameters travel in
kPa (registry units). Anything without the prefix is not ours.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Union

from .models import CRITERIA

FORMAT = "ogr-material/1"
PREFIX = "OGR-DATA-MATERIAL:"

Params = Mapping[str, Union[float, bool, str]]


@dataclass(frozen=True)
class MaterialPayload:
    name: str
    criterion: str
    parameters: dict[str, Union[float, bool, str]]
    computed: dict[str, float]


def material_text(
    name: str,
    criterion_key: str,
    params: Params,
    computed: Mapping[str, float] | None = None,
) -> str:
    """Serialize a material to the clipboard contract."""

    if criterion_key not in CRITERIA:
        raise ValueError(f"unknown criterion {criterion_key!r}")
    payload = {
        "format": FORMAT,
        "name": name,
        "criterion": criterion_key,
        "criterion_label": CRITERIA[criterion_key].label,
        "units": "kPa, deg",
        "parameters": dict(params),
        "computed": dict(computed or {}),
    }
    return PREFIX + json.dumps(payload, sort_keys=True)


def parse_material(text: str) -> MaterialPayload | None:
    """Parse clipboard text; None if it is not an OGR material."""

    if not text.startswith(PREFIX):
        return None
    try:
        payload = json.loads(text[len(PREFIX):])
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid OGR material payload: {exc}") from exc
    if payload.get("format") != FORMAT:
        raise ValueError(f"unsupported material format {payload.get('format')!r}")
    criterion = payload["criterion"]
    if criterion not in CRITERIA:
        raise ValueError(f"unknown criterion {criterion!r}")
    return MaterialPayload(
        name=str(payload.get("name", "")),
        criterion=criterion,
        parameters=dict(payload["parameters"]),
        computed={k: float(v) for k, v in dict(payload.get("computed", {})).items()},
    )


def tabular_data(
    criterion_key: str,
    params: Params,
    computed: Mapping[str, float] | None = None,
) -> str:
    """Tab-separated name/value summary (paste into Excel)."""

    lines = [f"criterion\t{CRITERIA[criterion_key].label}"]
    for key, value in params.items():
        lines.append(f"{key}\t{value}")
    for key, value in (computed or {}).items():
        lines.append(f"{key}\t{value:.6g}")
    return "\n".join(lines)
