"""Importer for .roc files (spec 007).

Format reverse-engineered from the 11 official example files shipped with
the user's guide of the format (see the suite references). Plain text,
`key: value` lines grouped in sections; criterion codes:
0 = Hoek-Brown (GHB), 1 = Mohr-Coulomb, 2 = Barton-Bandis, 3 = Power Curve.
Units code 0 = MPa (the only one observed); parameters are converted to
the registry units (kPa).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RocPoints:
    test: int
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class RocProject:
    title: str
    units: int
    criterion: str
    parameters: dict[str, float]
    sig3max_mpa: float | None
    lab_data: RocPoints = field(default_factory=lambda: RocPoints(0, ()))
    mass_data: RocPoints = field(default_factory=lambda: RocPoints(0, ()))


_CRITERIA = {
    0: "generalized_hoek_brown",
    1: "mohr_coulomb",
    2: "barton_bandis",
    3: "power_curve",
}

# .roc parameter -> registry field, with scale applied after unit factor.
_PARAM_MAP = {
    "generalized_hoek_brown": [
        ("sigci", "sigci", 1000.0),
        ("GSI", "gsi", 1.0),
        ("mi", "mi", 1.0),
        ("D", "d", 1.0),
    ],
    "mohr_coulomb": [
        ("cohesion", "peak_cohesion", 1000.0),
        ("friction angle", "peak_friction", 1.0),
        ("tensile strength", "peak_tensile", 1000.0),
    ],
    "barton_bandis": [
        ("basic friction angle", "phi_r", 1.0),
        ("joint roughness coefficient (JRC)", "jrc", 1.0),
        ("joint compressive strength (JCS)", "jcs", 1000.0),
    ],
    "power_curve": [
        ("parameter a", "a", 1.0),
        ("parameter b", "b", 1.0),
        ("parameter d", "d", 1000.0),
    ],
}

_SIG3MAX_KEYS = ("sig3max", "signmax")

# first line of every .roc file
FORMAT_TAG = "RocData:"  # rule 9: file-format tag


def _sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "header"
    sections[current] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.endswith(":") and not line.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9")):
            current = line[:-1].strip()
            sections.setdefault(current, [])
            continue
        sections[current].append(line)
    return sections


def _key_value(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        if ": " in line:
            key, _, value = line.partition(": ")
            out[key.strip()] = value.strip()
    return out


def _parse_points(lines: list[str]) -> RocPoints:
    values = _key_value(lines)
    test = int(float(values.get("test", "0")))
    num = int(float(values.get("num", "0")))
    points = []
    for line in lines:
        parts = line.split()
        if len(parts) == 3 and parts[0].isdigit():
            points.append((float(parts[1]), float(parts[2])))
    if num and len(points) != num:
        raise ValueError(f"data block declares {num} points but {len(points)} were found")
    return RocPoints(test, tuple(points))


def parse_roc(path: str | Path) -> RocProject:
    """Parse a .roc file into a RocProject (registry units, kPa)."""

    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.replace("\r", "").split("\n")
    if not lines or lines[0].strip() != FORMAT_TAG:
        raise ValueError(f"{path} is not a .roc file (missing the .roc header)")
    sections = _sections(lines)
    settings = _key_value(sections.get("project settings", []))

    units = int(float(settings.get("units", "0")))
    if units != 0:
        raise ValueError(f"unsupported .roc units code {units} (only 0 = MPa is implemented)")
    criterion_code = int(float(settings.get("failure criterion", "0")))
    criterion = _CRITERIA.get(criterion_code)
    if criterion is None:
        raise ValueError(f"unknown .roc failure criterion code {criterion_code}")

    section_key = {
        "generalized_hoek_brown": "hoek-brown settings",
        "mohr_coulomb": "mohr-coulomb settings",
        "barton_bandis": "barton-bandis settings",
        "power_curve": "power curve settings",
    }[criterion]
    values = _key_value(sections.get(section_key, []))

    parameters: dict[str, float] = {}
    for roc_key, field_key, scale in _PARAM_MAP[criterion]:
        if roc_key in values:
            parameters[field_key] = float(values[roc_key]) * scale
    if criterion == "power_curve" and "a" in parameters and "b" in parameters:
        from .units import power_curve_a_to_kpa

        parameters["a"] = power_curve_a_to_kpa(parameters["a"], parameters["b"])  # spec 026: stresses in MPa in the file

    sig3max = None
    for key in _SIG3MAX_KEYS:
        if key in values:
            sig3max = float(values[key])
            break

    return RocProject(
        title=settings.get("title", Path(path).stem),
        units=units,
        criterion=criterion,
        parameters=parameters,
        sig3max_mpa=sig3max,
        lab_data=_parse_points(sections.get("lab data", [])),
        mass_data=_parse_points(sections.get("rock mass data", [])),
    )
