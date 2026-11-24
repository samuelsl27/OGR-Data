"""Failure states and stress paths of a material (specs 012 and 021).

Layouts verified in the reference program (private references,
07_estados_y_rutas_verificado.md, captures 44-74, Excel exports):

- FailureState: name, color, symbol, test type and ONE point table (the
  reference program has no Peak/Residual tabs). Triaxial: Sigma3, Sigma1, Exclude. Direct
  Shear: SigmaN, Tau, Exclude. General: StressXX, StressYY, StressZZ,
  TauXY, TauYZ, TauXZ (no Exclude). Exclude removes the point from the
  calibration and from the plots (verified numerically). Drawing (reference
  program, capture 71, and the earlier reference program): triaxial and general
  states as points in sigma1-sigma3 and Mohr circles in tau-sigma; direct
  shear as points in tau-sigma.
- StressPath: test type Uniaxial / Triaxial / Biaxial / Simple Shear; the
  fields and table columns depend on the configuration (columns()).
  Verified semantics (Loading Direction = Axial): the SigmaZZ column is
  the imposed axial stress, the radial stress stays at the Initial
  Effective Lateral Stress; undrained paths carry a Pore Water Pressure
  column and plot effective stresses (sigma - u); K0 has no observable
  effect; q is unsigned; eq = ea - ev/3.

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

# default color of a new state / path in the reference program (captures 31, 32; official help).
DEFAULT_COLOR = "#800000"
# further states/paths of the same material
PALETTE = ("#1f618d", "#117a65", "#b9770e", "#6c3483", "#a04000", "#2e4053")

# Define Failure States, Test Type combo of the reference program (capture 70).
FAILURE_TEST_TYPES: dict[str, str] = {
    "triaxial": "Triaxial Test",
    "direct_shear": "Direct Shear Test",
    "general": "General Test",
}
GENERAL_COLUMNS = ("StressXX", "StressYY", "StressZZ", "TauXY", "TauYZ", "TauXZ")

# Define Stress Paths, Test Type combo of the reference program (capture 59; the
# online help also lists "General", absent from the program).
PATH_TEST_TYPES: dict[str, str] = {
    "uniaxial": "Uniaxial Test",
    "triaxial": "Triaxial Test",
    "biaxial": "Biaxial Test",
    "simple_shear": "Simple Shear Test",
}
SEEPAGE_CONDITIONS = ("Drained", "Undrained")
LOADING_DIRECTIONS = ("None", "Axial", "Lateral")
# the reference program shows "Volumatric" (typo of the program); OGR spells it right.
STRAIN_TYPES = ("None", "Volumetric", "Lateral")


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


def principal_from_tensor(row: Iterable[float]) -> tuple[float, float]:
    """(sigma3, sigma1) of a stress tensor row (XX, YY, ZZ, XY, YZ, XZ).

    Eigenvalues of the symmetric 3x3 tensor; compression positive as entered.
    """

    sxx, syy, szz, txy, tyz, txz = (float(v) for v in row)
    tensor = np.array([[sxx, txy, txz], [txy, syy, tyz], [txz, tyz, szz]])
    values = np.linalg.eigvalsh(tensor)
    return float(values[0]), float(values[-1])


@dataclass
class FailureState:
    name: str = "State 1"
    color: str = DEFAULT_COLOR
    symbol: str = "o"
    test_type: str = "triaxial"
    points: list[TestPoint] = field(default_factory=list)  # triaxial / direct shear
    tensors: list[tuple[float, ...]] = field(default_factory=list)  # general: 6 components
    visible: bool = True

    def __post_init__(self) -> None:
        self.test_type = _choice(self.test_type, FAILURE_TEST_TYPES, "triaxial")
        self.tensors = [tuple(float(v) for v in row[:6]) for row in self.tensors]

    @property
    def columns(self) -> tuple[str, ...]:
        if self.test_type == "direct_shear":
            return ("SigmaN", "Tau")
        if self.test_type == "general":
            return GENERAL_COLUMNS
        return ("Sigma3", "Sigma1")

    def principal_points(self) -> tuple[np.ndarray, np.ndarray] | None:
        """(sigma3, sigma1) in kPa of the included points, or None (direct shear)."""

        if self.test_type == "direct_shear":
            return None
        if self.test_type == "general":
            pairs = [principal_from_tensor(row) for row in self.tensors]
        else:
            pairs = [(p.x, p.y) for p in self.points if not p.exclude]
        return np.array([p[0] for p in pairs], dtype=float), np.array([p[1] for p in pairs], dtype=float)

    def shear_points(self) -> tuple[np.ndarray, np.ndarray] | None:
        """(sigma_n, tau) in kPa of the included direct-shear points, or None."""

        if self.test_type != "direct_shear":
            return None
        pts = [p for p in self.points if not p.exclude]
        return np.array([p.x for p in pts], dtype=float), np.array([p.y for p in pts], dtype=float)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "symbol": self.symbol,
            "test_type": self.test_type,
            "points": [p.to_list() for p in self.points],
            "tensors": [list(row) for row in self.tensors],
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "FailureState":
        return cls(
            name=str(data.get("name", "")) or "State",
            color=str(data.get("color", DEFAULT_COLOR)) or DEFAULT_COLOR,
            symbol=str(data.get("symbol", "o")),
            test_type=str(data.get("test_type", "triaxial")),
            points=[TestPoint.from_any(p) for p in data.get("points", data.get("peak", []))],
            tensors=[tuple(row) for row in data.get("tensors", [])],
            visible=bool(data.get("visible", True)),
        )


def failure_states_from_dicts(items: Iterable[Mapping]) -> list[FailureState]:
    """Load failure states; first-012 files with residual points are split.

    The reference program has one table per state, so a legacy state with "residual"
    points becomes two states: "<name>" and "<name> (residual)".
    """

    out: list[FailureState] = []
    for data in items:
        state = FailureState.from_dict(data)
        out.append(state)
        residual = data.get("residual", [])
        if residual:
            extra = FailureState.from_dict({**data, "name": f"{state.name} (residual)", "points": residual})
            extra.color = next_color(s.color for s in out)
            out.append(extra)
    return out


@dataclass
class PathInvariants:
    """Per-step effective stresses (kPa) and strains of a drawable path.

    p' = (sa + 2 sr)/3 and q = |sa - sr| (the reference program plots q unsigned, verified);
    ev = ea + 2 er, eq = 2 (ea - er)/3 = ea - ev/3 (Machacek 2023; reference
    program verified); s, t: centre and radius of the Mohr circle, the stress point
    on the tau-sigma plane (UTM "Stress Paths and Strength Tests", p. 2).
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
        return np.abs(self.sigma_a - self.sigma_r)

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
    loading: str = "Lateral"  # triaxial / biaxial: Loading Direction (default Lateral, as the reference program)
    lateral_stress: float = 100.0  # initial effective lateral stress, kPa (default of the reference program)
    k0: float = 1.0  # initial effective K0 (default of the reference program; no observable effect)
    strain_type: str = "Lateral"  # uniaxial: Strain Type (default Lateral, as the reference program)
    steps: list[list[float]] = field(default_factory=list)  # rows, columns per columns()
    visible: bool = True

    def __post_init__(self) -> None:
        self.test_type = _choice(self.test_type, PATH_TEST_TYPES, "uniaxial")
        self.seepage = _choice(self.seepage, SEEPAGE_CONDITIONS, "Drained")
        # first-012 files stored Compression/Extension
        self.loading = _choice(self.loading, LOADING_DIRECTIONS, "Lateral")
        if self.strain_type == "Volumatric":  # spelling of the reference program
            self.strain_type = "Volumetric"
        self.strain_type = _choice(self.strain_type, STRAIN_TYPES, "Lateral")
        self.steps = [[float(v) for v in row] for row in self.steps]

    def columns(self) -> tuple[str, ...]:
        """Table columns of the reference program for this configuration (verified)."""

        if self.test_type == "uniaxial":
            return ("EpsilonZZ", "SigmaZZ", "EpsilonXX" if self.strain_type == "Lateral" else "EpsilonV")
        if self.test_type == "simple_shear":
            return ("SigmaZY", "EpsilonZY", "EpsilonZZ")
        # triaxial and biaxial share the layout
        stress = {"Axial": ("SigmaZZ",), "Lateral": ("SigmaXX",), "None": ()}[self.loading]
        last = "EpsilonV" if self.seepage == "Drained" else "Pore Water Pressure"
        return ("EpsilonZZ", *stress, last)

    def stress_columns(self) -> tuple[bool, ...]:
        """Which columns hold stresses (kPa) — for unit display and scaling."""

        return tuple(c.startswith("Sigma") or c == "Pore Water Pressure" for c in self.columns())

    @property
    def drawable(self) -> bool:
        """Configurations whose meaning is verified in the reference program (spec 021).

        Uniaxial and triaxial with Loading Direction = Axial. Not drawn:
        Lateral (the reference program overwrites SigmaXX with sigma'h0 and plots the axial
        stress as 0), None (no stress column), biaxial (plane-strain
        invariants not verified) and simple shear (no normal stresses).
        """

        return self.test_type == "uniaxial" or (self.test_type == "triaxial" and self.loading == "Axial")

    def _column(self, name: str) -> np.ndarray:
        index = self.columns().index(name)
        return np.array([row[index] if index < len(row) else 0.0 for row in self.steps], dtype=float)

    def invariants(self) -> PathInvariants | None:
        """Effective axial/radial stresses and strains per step, or None.

        Uniaxial: radial stress zero (OGR; the reference program plots p and q with a
        hidden radial stress of 100 kPa, a program quirk not reproduced);
        radial strain EpsilonXX or (EpsilonV - EpsilonZZ)/2. Triaxial, Axial
        loading: radial stress = initial effective lateral stress; drained ->
        EpsilonV column; undrained -> Pore Water Pressure u, effective
        stresses sigma - u and no volume change (ev = 0).
        """

        if not self.steps or not self.drawable:
            return None
        eps_a = self._column("EpsilonZZ")
        if self.test_type == "uniaxial":
            sigma_a = self._column("SigmaZZ")
            sigma_r = np.zeros_like(sigma_a)
            if self.strain_type == "Lateral":
                eps_r = self._column("EpsilonXX")
            else:
                eps_r = (self._column("EpsilonV") - eps_a) / 2.0
            return PathInvariants(sigma_a, sigma_r, eps_a, eps_r)
        sigma_a = self._column("SigmaZZ")
        sigma_r = np.full_like(sigma_a, self.lateral_stress)
        if self.seepage == "Drained":
            eps_r = (self._column("EpsilonV") - eps_a) / 2.0
        else:
            u = self._column("Pore Water Pressure")
            sigma_a, sigma_r = sigma_a - u, sigma_r - u
            eps_r = -eps_a / 2.0  # undrained: ev = 0
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
            "steps": [list(row) for row in self.steps],
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
            steps=[list(row) for row in data.get("steps", [])],
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
