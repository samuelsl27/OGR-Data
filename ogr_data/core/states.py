"""Failure states and stress paths of a material (spec 012).

The two RSData objects observed in its Define Failure States / Define
Stress Paths dialogs (captures 31_* and 32_* of the RSData analysis):

- FailureState: name, color, symbol, test type and two point tables,
  Peak Points and Residual Points (sigma3, sigma1, Exclude). Drawn as the
  RocData "Plot Test Data" option documents (RocData 3.0 User's Guide,
  pp. 13 and 47-48): triaxial data as points in principal stress space and
  as Mohr circles in shear-normal space; direct shear data only as points
  in shear-normal space.
- StressPath: name, color, test type, seepage condition, loading
  direction (triaxial) or strain type (uniaxial), initial effective
  lateral stress, initial effective K0 and a table of steps whose columns
  depend on the configuration (RSData help "Define Stress Paths" and its
  dialog figure). Here a path is drawn data, not a simulation (spec 013).
  Paths are drawn in sigma1-sigma3, as stress points (Mohr circle tops)
  in tau-sigma, and in the four Stress Path Graphs (axial stress, volumetric
  strain, q-deviatoric strain, q-p).

Official RSData option lists: rocscience.com/help/rsdata, Define Failure
States / Define Stress Paths (saved in Referencias/Ejemplos/RSData_analisis/
ayuda_online). Column layouts not shown there are pending (spec 021).

Stresses are stored in kPa (registry units), strains as given.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

# RSData default color of a new state / path (sampled from captures 31, 32).
DEFAULT_COLOR = "#800000"
# further states/paths of the same material
PALETTE = ("#1f618d", "#117a65", "#b9770e", "#6c3483", "#a04000", "#2e4053")

# RSData failure-state test types are Triaxial, Simple Shear and General
# (official help); only Triaxial has a verified column layout (sigma3,
# sigma1), the other two are pending (spec 021). "Direct Shear Test" is the
# other test data type of RocData's Use Lab Data (guide p. 9), kept as an
# OGR extension: its data plot only in shear-normal space.
FAILURE_TEST_TYPES: dict[str, str] = {
    "triaxial": "Triaxial Test",
    "direct_shear": "Direct Shear Test (RocData)",
}
# Test types of RSData's Define Stress Paths (official help).
PATH_TEST_TYPES: dict[str, str] = {
    "uniaxial": "Uniaxial Test",
    "triaxial": "Triaxial Test",
    "biaxial": "Biaxial Test",
    "simple_shear": "Simple Shear Test",
    "general": "General Test",
}
SEEPAGE_CONDITIONS = ("Drained", "Undrained")
# RSData help: "Lateral, Axial (for triaxial test, biaxial, and general
# test)" and "Lateral, volumetric (for uniaxial test)".
LOADING_DIRECTIONS = ("Lateral", "Axial")
STRAIN_TYPES = ("Lateral", "Volumetric")


def _choice(value, options, default):
    return value if value in options else default


@dataclass
class TestPoint:
    x: float  # sigma3 (triaxial) or normal stress (direct shear), kPa
    y: float  # sigma1 (triaxial) or shear stress (direct shear), kPa
    exclude: bool = False

    def to_list(self) -> list:
        return [self.x, self.y, self.exclude]

    @classmethod
    def from_any(cls, data) -> "TestPoint":
        if isinstance(data, Mapping):
            return cls(float(data["x"]), float(data["y"]), bool(data.get("exclude", False)))
        values = list(data)
        return cls(float(values[0]), float(values[1]), bool(values[2]) if len(values) > 2 else False)


@dataclass
class FailureState:
    name: str = "State 1"
    color: str = DEFAULT_COLOR
    symbol: str = "o"
    test_type: str = "triaxial"
    peak: list[TestPoint] = field(default_factory=list)
    residual: list[TestPoint] = field(default_factory=list)
    visible: bool = True

    def __post_init__(self) -> None:
        self.test_type = _choice(self.test_type, FAILURE_TEST_TYPES, "triaxial")

    @property
    def columns(self) -> tuple[str, str]:
        if self.test_type == "direct_shear":
            return ("Normal Stress", "Shear Stress")
        return ("Sigma3", "Sigma1")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "symbol": self.symbol,
            "test_type": self.test_type,
            "peak": [p.to_list() for p in self.peak],
            "residual": [p.to_list() for p in self.residual],
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "FailureState":
        return cls(
            name=str(data.get("name", "")) or "State",
            color=str(data.get("color", DEFAULT_COLOR)) or DEFAULT_COLOR,
            symbol=str(data.get("symbol", "o")),
            test_type=str(data.get("test_type", "triaxial")),
            peak=[TestPoint.from_any(p) for p in data.get("peak", [])],
            residual=[TestPoint.from_any(p) for p in data.get("residual", [])],
            visible=bool(data.get("visible", True)),
        )


@dataclass
class PathStep:
    """One row of a stress path table: (EpsilonZZ, stress, strain).

    The meaning of the stress and strain columns follows the RSData dialog
    for the path's test type and loading direction / strain type; see
    StressPath.columns().
    """

    eps_zz: float
    stress: float  # kPa: SigmaZZ or SigmaXX
    strain: float  # EpsilonXX or EpsilonV

    def to_list(self) -> list:
        return [self.eps_zz, self.stress, self.strain]


@dataclass
class PathInvariants:
    """Per-step stresses (kPa) and strains of a drawable path (triaxial geometry).

    p, q: Roscoe invariants p' = (sa + 2 sr)/3, q = sa - sr; strains
    ev = ea + 2 er, eq = 2 (ea - er)/3 (Machacek 2023, "Triaxial test");
    s, t: centre and radius of the Mohr circle, the stress point drawn on
    the tau-sigma plane (UTM "Stress Paths and Strength Tests", p. 2).
    """

    sigma_a: np.ndarray
    sigma_r: np.ndarray
    eps_a: np.ndarray
    eps_r: np.ndarray

    @property
    def sigma1(self) -> np.ndarray:
        return np.maximum(self.sigma_a, self.sigma_r)

    @property
    def sigma3(self) -> np.ndarray:
        return np.minimum(self.sigma_a, self.sigma_r)

    @property
    def p(self) -> np.ndarray:
        return (self.sigma_a + 2.0 * self.sigma_r) / 3.0

    @property
    def q(self) -> np.ndarray:
        return self.sigma_a - self.sigma_r

    @property
    def eps_v(self) -> np.ndarray:
        return self.eps_a + 2.0 * self.eps_r

    @property
    def eps_q(self) -> np.ndarray:
        return 2.0 * (self.eps_a - self.eps_r) / 3.0

    @property
    def s(self) -> np.ndarray:
        return (self.sigma1 + self.sigma3) / 2.0

    @property
    def t(self) -> np.ndarray:
        return (self.sigma1 - self.sigma3) / 2.0


@dataclass
class StressPath:
    name: str = "Path 1"
    color: str = DEFAULT_COLOR
    test_type: str = "uniaxial"
    seepage: str = "Drained"
    loading: str = "Lateral"  # triaxial: Loading Direction (Lateral | Axial)
    lateral_stress: float = 100.0  # initial effective lateral stress, kPa (RSData default)
    k0: float = 1.0  # initial effective K0 (RSData default)
    strain_type: str = "Lateral"  # uniaxial: Strain Type (Lateral | Volumetric)
    steps: list[PathStep] = field(default_factory=list)
    visible: bool = True

    def __post_init__(self) -> None:
        self.test_type = _choice(self.test_type, PATH_TEST_TYPES, "uniaxial")
        self.seepage = _choice(self.seepage, SEEPAGE_CONDITIONS, "Drained")
        # files of the first spec-012 version stored Compression/Extension
        self.loading = _choice(self.loading, LOADING_DIRECTIONS, "Lateral")
        self.strain_type = _choice(self.strain_type, STRAIN_TYPES, "Lateral")

    def columns(self) -> tuple[str, str, str]:
        """Table columns of the RSData dialog for this configuration.

        Uniaxial: EpsilonZZ, SigmaZZ, EpsilonXX (capture 32, Strain Type
        Lateral) or EpsilonV (Volumetric). Triaxial, Loading Direction
        Lateral: EpsilonZZ, SigmaXX, EpsilonV (official RSData help figure);
        Axial: EpsilonZZ, SigmaZZ, EpsilonV (provisional, spec 021).
        """

        if self.test_type == "uniaxial":
            return ("EpsilonZZ", "SigmaZZ", "EpsilonXX" if self.strain_type == "Lateral" else "EpsilonV")
        if self.test_type == "triaxial":
            return ("EpsilonZZ", "SigmaXX" if self.loading == "Lateral" else "SigmaZZ", "EpsilonV")
        return ("EpsilonZZ", "SigmaZZ", "EpsilonXX")  # spec 021: not verified

    @property
    def drawable(self) -> bool:
        return self.test_type in ("uniaxial", "triaxial")

    def invariants(self) -> PathInvariants | None:
        """Axial/radial stresses and strains per step, or None if not drawable.

        Uniaxial: radial stress zero; radial strain is EpsilonXX, or
        (EpsilonV - EpsilonZZ)/2 when the table gives volumetric strain.
        Triaxial (provisional interpretation, spec 021): the stress column
        varies while the other principal stress keeps its initial effective
        value: Axial loading -> radial = initial effective lateral stress;
        Lateral loading -> axial = initial effective vertical stress
        sigma'h0 / K0 (K0 = sigma'h / sigma'v). Radial strain from EpsilonV.
        Biaxial, simple shear and general tests: not drawable yet (spec 021).
        """

        if not self.steps or not self.drawable:
            return None
        eps_a = np.array([s.eps_zz for s in self.steps], dtype=float)
        stress = np.array([s.stress for s in self.steps], dtype=float)
        third = np.array([s.strain for s in self.steps], dtype=float)
        if self.test_type == "uniaxial":
            sigma_a, sigma_r = stress, np.zeros_like(stress)
            eps_r = third if self.strain_type == "Lateral" else (third - eps_a) / 2.0
        else:
            if self.loading == "Axial":
                sigma_a, sigma_r = stress, np.full_like(stress, self.lateral_stress)
            else:
                if self.k0 <= 0.0:
                    return None
                sigma_a, sigma_r = np.full_like(stress, self.lateral_stress / self.k0), stress
            eps_r = (third - eps_a) / 2.0
        return PathInvariants(sigma_a, sigma_r, eps_a, eps_r)

    def principal_path(self) -> tuple[np.ndarray, np.ndarray] | None:
        """(sigma3, sigma1) in kPa along the path, or None if not drawable."""

        inv = self.invariants()
        return None if inv is None else (inv.sigma3, inv.sigma1)

    def shear_path(self) -> tuple[np.ndarray, np.ndarray] | None:
        """Stress points (s, t) on the tau-sigma plane: tops of the Mohr circles, kPa."""

        inv = self.invariants()
        return None if inv is None else (inv.s, inv.t)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "test_type": self.test_type,
            "seepage": self.seepage,
            "loading": self.loading,
            "lateral_stress": self.lateral_stress,
            "k0": self.k0,
            "strain_type": self.strain_type,
            "steps": [s.to_list() for s in self.steps],
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "StressPath":
        return cls(
            name=str(data.get("name", "")) or "Path",
            color=str(data.get("color", DEFAULT_COLOR)) or DEFAULT_COLOR,
            test_type=str(data.get("test_type", "uniaxial")),
            seepage=str(data.get("seepage", "Drained")),
            loading=str(data.get("loading", "Lateral")),
            lateral_stress=float(data.get("lateral_stress", 100.0)),
            k0=float(data.get("k0", 1.0)),
            strain_type=str(data.get("strain_type", "Lateral")),
            steps=[PathStep(*(float(v) for v in list(s)[:3])) for s in data.get("steps", [])],
            visible=bool(data.get("visible", True)),
        )


# ------------------------------------------------------------- helpers


def unique_name(base: str, taken: Iterable[str]) -> str:
    taken = set(taken)
    if base not in taken:
        return base
    n = 2
    while f"{base} {n}" in taken:
        n += 1
    return f"{base} {n}"


def next_color(used: Iterable[str]) -> str:
    used = set(used)
    for color in (DEFAULT_COLOR, *PALETTE):
        if color not in used:
            return color
    return PALETTE[len(used) % len(PALETTE)]


def mohr_circle(sig3: float, sig1: float, points: int = 73) -> tuple[np.ndarray, np.ndarray]:
    """Upper half of the Mohr circle of a (sigma3, sigma1) state: (normal, shear)."""

    centre = (sig1 + sig3) / 2.0
    radius = abs(sig1 - sig3) / 2.0
    theta = np.linspace(0.0, math.pi, points)
    return centre - radius * np.cos(theta), radius * np.sin(theta)


# --------------------------------------------------------- table text I/O

_TRUE = {"1", "true", "yes", "x", "y"}


def _number(cell: str, decimal_comma: bool) -> float:
    cell = cell.strip()
    if decimal_comma:
        cell = cell.replace(",", ".")
    return float(cell)


def parse_rows(text: str, numeric_columns: int = 2, flag_column: bool = False) -> list[tuple]:
    """Rows of numbers pasted from Excel or read from CSV/text.

    Separators: tab (Excel), semicolon (CSV with decimal comma), comma or
    whitespace. With tab or semicolon separators a decimal comma is
    accepted. Rows that do not start with `numeric_columns` numbers
    (headers, notes) are skipped. With flag_column, an optional next cell
    is read as a boolean (1/true/yes/x), e.g. Exclude.
    """

    rows: list[tuple] = []
    for line in text.replace("\r", "").split("\n"):
        if not line.strip():
            continue
        if "\t" in line:
            cells, decimal_comma = line.split("\t"), True
        elif ";" in line:
            cells, decimal_comma = line.split(";"), True
        elif "," in line:
            cells, decimal_comma = line.split(","), False
        else:
            cells, decimal_comma = line.split(), False
        if len(cells) < numeric_columns:
            continue
        try:
            values = [_number(c, decimal_comma) for c in cells[:numeric_columns]]
        except ValueError:
            continue
        if flag_column:
            flag = cells[numeric_columns].strip().lower() in _TRUE if len(cells) > numeric_columns else False
            values.append(flag)
        rows.append(tuple(values))
    return rows


def write_rows_csv(path: str | Path, header: Iterable[str], rows: Iterable[Iterable]) -> None:
    """Comma-separated values with a header row (Excel opens it as is)."""

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(header))
    for row in rows:
        writer.writerow([("1" if v else "0") if isinstance(v, bool) else repr(float(v)) for v in row])
    Path(path).write_text(buffer.getvalue(), encoding="utf-8")


def read_rows_csv(path: str | Path, numeric_columns: int = 2, flag_column: bool = False) -> list[tuple]:
    return parse_rows(Path(path).read_text(encoding="utf-8-sig"), numeric_columns, flag_column)
