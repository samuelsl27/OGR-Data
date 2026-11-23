"""OGR Data project files (.ogrdata), spec 007."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Union

from .models import CRITERIA

FORMAT = "ogr-data-project/1"

Params = Mapping[str, Union[float, bool, str]]


def project_dict(
    name: str,
    criterion_key: str,
    params: Params,
    sig3max_mpa: float,
    stress_unit: str = "kPa",
    title: str = "",
    graph_options: dict | None = None,
) -> dict:
    if criterion_key not in CRITERIA:
        raise ValueError(f"unknown criterion {criterion_key!r}")
    return {
        "format": FORMAT,
        "name": name,
        "title": title,
        "criterion": criterion_key,
        "sig3max_mpa": float(sig3max_mpa),
        "stress_unit": stress_unit,
        "graph_options": dict(graph_options or {}),
        "parameters": dict(params),
    }


def save_project(
    path: str | Path,
    name: str,
    criterion_key: str,
    params: Params,
    sig3max_mpa: float,
    stress_unit: str = "kPa",
    title: str = "",
    graph_options: dict | None = None,
) -> None:
    Path(path).write_text(
        json.dumps(
            project_dict(name, criterion_key, params, sig3max_mpa, stress_unit, title, graph_options),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def load_project(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise ValueError(f"unsupported project format {data.get('format')!r}")
    if data["criterion"] not in CRITERIA:
        raise ValueError(f"unknown criterion {data['criterion']!r}")
    return data
