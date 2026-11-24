"""Test simulations (spec 013, phases 13a and 13b).

The Tests module of the reference program (Define Test Simulations, capture 20): a simulated
laboratory test on a material — Test Type, Seepage Condition (Drained /
Undrained), Loading Direction (Compression / Tension), Maximum Strain,
Number of Steps and Cyclic Loading Cycles — integrated step by step with
the material's constitutive model. Results feed the Stress Path Graphs.

Conventions: compression positive, stresses in kPa (effective), strains
as engineering components in the order (a, x, y, a-x, x-y, a-y), where a
is the axial (vertical) direction. Internally stresses and strains are
3x3 tensors (tensorial shear strains).

Constitutive models (as in the theory manuals of the reference program, in
Referencias/Bibliografia: Mohr-Coulomb, Hoek-Brown and GHB, Drucker-Prager, Cam-Clay
and Modified Cam-Clay, Softening-Hardening):

- Linear isotropic elasticity from the Stiffness tab (reference program: Poisson's
  Ratio 0.3, Young's Modulus 20000 kPa) for all models except Cam-Clay
  and Modified Cam-Clay, whose bulk modulus is K = v p / kappa (manual
  eq. 8.7) with the Poisson's ratio of the Stiffness tab.
- Isotropic yield functions of the principal stresses, integrated with a
  spectral backward-Euler return (the trial stress keeps its principal
  directions under isotropic elasticity; valid with rotating axes, e.g.
  simple shear) and an active set of surfaces:
  * Mohr-Coulomb / Hoek-Brown / GHB as the six faces f_ij = s_i - S(s_j)
    of the pyramid (edges and apex exact); potentials with the dilation
    angle (MC), the dilation parameter as mb of the potential (HB) or no
    plastic volume change (GHB has no dilation field in the reference program).
  * Drucker-Prager (manual eqs. 4.1-4.2): sqrt(J2) = k + q_phi p with the
    potential sqrt(J2) - q_psi p (q_psi = Dilation Parameter).
  * Tension cut-off s_min >= -T, associated (manual eqs. 4.3, 6.x, 11.11)
    for MC, DP and Softening-Hardening with their Tensile Strength field.
    A tensile strength of 0 is read literally: no tension (as in the reference program).
  * Peak/residual (Set Residual to Peak off): elastic-brittle-plastic, the
    first plastic step drops to the residual surface (as in the reference program).
- Softening-Hardening, deviatoric mechanism (manual §11.1): Mohr-Coulomb
  surface with mobilized friction tan(phi) = tan(phi_f) e_q^p / (e_q^p + A)
  (eq. 11.4, Cone Hardening "Hyperbolic"), mobilized cohesion keeping the
  apex at c / tan(phi_f) (eq. 11.3), hardening variable e_q^p = deviatoric
  plastic strain of this mechanism, solved implicitly (bracketed root).
  Cone Dilation "Mohr-Coulomb": psi = psi_f phi / phi_f (eqs. 11.5-11.6);
  "Compaction-Dilation" (eq. 11.7): dilatancy d = de_v^p / de_q^p =
  M_psi - eta, with M_psi of triaxial compression and eta = q/p at the start
  of the step. Cap: none (vertical and elliptical caps, tabular hardening:
  pending).
- Cam-Clay / Modified Cam-Clay (manual §8): yield q + M p ln(p/pc) = 0 and
  q^2 + M^2 p (p - pc) = 0 (compression positive), associated flow,
  hardening pc_{n+1} = pc_n exp(v de_v^p / (lambda - kappa)) (eq. 8.8),
  start on the surface (OCR = 1) times OCR, or at Po, v0 on the swelling line
  through pc0 on the virgin line v = N - lambda ln p (N = Specific Volume at
  Unit Pressure, kPa). Implicit return in (p, q, pc, dlambda) with the
  exact integration of K = v p / kappa over the step; radial in the
  deviatoric plane (the surfaces do not depend on Lode's angle).
- NorSand: see NorSandModel (FLAC3D formulation with Nova's coupling,
  checked against the Fraser River sand tutorial of the reference program).

Tests (mixed control; one imposed strain component per step):
- Uniaxial: lateral stresses zero.
- Triaxial: lateral effective stresses = initial lateral (drained); undrained:
  no volume change, e_r = -e_a/2, u = s_c - s'_r (cell pressure constant,
  initial u = 0).
- Biaxial (plane strain): e_y = 0; s'_x = initial lateral (drained) or
  e_x = -e_a, u = s_c - s'_x (undrained).
- Simple Shear: imposed shear strain gamma_ax, no lateral strains, vertical
  effective stress = initial vertical (drained) or no vertical strain and
  u = s_c - s'_a (undrained); isotropic start.
- General (OGR design, the reference program does not document its inputs): proportional
  strain path in a given direction; undrained keeps the volume.
- Initial state: Initial Effective Lateral Stress and Initial Effective K0
  (test dialog of the reference program): axial (vertical) = lateral / K0.

Loading Direction Tension imposes negative strains (extension / reverse
shear). Cyclic loading (basic): 0 -> max -> 0 per cycle, Number of Steps
per half cycle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

from .hoek_brown import HbInput, hoek_brown_constants

# Define Test Simulations, Test Type combo of the reference program (capture 20; help).
TEST_TYPES: dict[str, str] = {
    "uniaxial": "Uniaxial Test",
    "triaxial": "Triaxial Test",
    "biaxial": "Biaxial Test",
    "simple_shear": "Simple Shear Test",
    "general": "General Test",
}
SIMULATED_TYPES = ("uniaxial", "triaxial", "biaxial", "simple_shear", "general")
# General Test (OGR design, the reference program does not document its inputs): proportional
# strain path with these components, Maximum Strain on the largest one.
STRAIN_COMPONENTS = ("EpsilonZZ", "EpsilonXX", "EpsilonYY", "GammaZX", "GammaXY", "GammaZY")
SEEPAGE = ("Drained", "Undrained")
LOADING = ("Compression", "Tension")
SIMULATED_CRITERIA = (
    "norsand",
    "mohr_coulomb",
    "hoek_brown",
    "generalized_hoek_brown",
    "drucker_prager",
    "cam_clay",
    "modified_cam_clay",
    "softening_hardening",
)

DEFAULT_COLOR = "#800000"  # default color of a new object in the reference program

# Stiffness tab of the reference program (capture 12; tutorials): Linear Isotropic for most
# models, "CamClay Isotropic" (Elastic Parameter: Constant Poisson Ratio /
# Constant Shear Modulus) for Cam-Clay and MCC, and the NorSand stiffness
# (Shear modulus at reference, Reference pressure, Modulus exponent,
# Poisson's ratio, Minimum Shear Modulus). Stresses in kPa. NorSand defaults:
# G_ref and p_ref of the Fraser River sand tutorial of the reference program are 40000 / 395 kPa;
# OGR uses G_ref = 40000 kPa at p_ref = 100 kPa, m = 0.5 and nu = 0.2 (FLAC3D
# default), G_min = 1 kPa (tutorial).
STIFFNESS_TYPES = ("Linear Isotropic",)
CAM_CLAY_ELASTIC = ("Constant Poisson Ratio", "Constant Shear Modulus")
DEFAULT_STIFFNESS = {
    "type": "Linear Isotropic",
    "poisson": 0.3,
    "young": 20000.0,
    "elastic_parameter": CAM_CLAY_ELASTIC[0],
    "shear_modulus": 10000.0,
    "g_ref": 40000.0,
    "p_ref": 100.0,
    "g_exp": 0.5,
    "ns_poisson": 0.2,
    "g_min": 1.0,
}

# Softening-Hardening options (manual §11; labels of OGR Data)
CONE_DILATION_TYPES = ("Mohr-Coulomb", "Compaction-Dilation")


class SimulationError(ValueError):
    """The test cannot be simulated (model, inputs or convergence)."""


def stiffness_from(data: Mapping | None) -> dict:
    data = dict(data or {})
    out = dict(DEFAULT_STIFFNESS)
    if data.get("type") in STIFFNESS_TYPES:
        out["type"] = data["type"]
    for key, value in DEFAULT_STIFFNESS.items():
        if key in data and key != "type":
            out[key] = str(data[key]) if isinstance(value, str) else float(data[key])
    if out["elastic_parameter"] not in CAM_CLAY_ELASTIC:
        out["elastic_parameter"] = CAM_CLAY_ELASTIC[0]
    return out


# ------------------------------------------------------------------ test


@dataclass
class TestSimulation:
    name: str = "Test 1"
    color: str = DEFAULT_COLOR
    symbol: str = "o"
    test_type: str = "uniaxial"
    seepage: str = "Drained"
    loading: str = "Compression"
    max_strain: float = 0.1
    steps: int = 100
    cyclic: bool = False
    cycles: int = 1
    # reference program: "Initial Effective Lateral Stress (kPa)" and "Initial Effective K0"
    # (tutorials: NorSand Fraser River sand, Modified Cam Clay); the initial
    # axial (vertical) effective stress is lateral / K0. Key kept as "confining".
    confining: float = 100.0
    k0: float = 1.0
    # General Test (OGR): strain direction (EpsilonZZ, EpsilonXX, EpsilonYY,
    # GammaZX, GammaXY, GammaZY); default isotropic compression
    strain_ratio: tuple = (1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
    visible: bool = True

    def __post_init__(self) -> None:
        if self.test_type not in TEST_TYPES:
            self.test_type = "uniaxial"
        if self.seepage not in SEEPAGE:
            self.seepage = "Drained"
        if self.loading not in LOADING:
            self.loading = "Compression"
        self.max_strain = float(self.max_strain)
        self.steps = max(1, int(self.steps))
        self.cycles = max(1, int(self.cycles))
        self.confining = float(self.confining)
        self.k0 = float(self.k0)
        ratio = [float(v) for v in list(self.strain_ratio)[:6]]
        self.strain_ratio = tuple(ratio + [0.0] * (6 - len(ratio)))

    @property
    def simulated(self) -> bool:
        return self.test_type in SIMULATED_TYPES

    @property
    def confined(self) -> bool:
        return self.test_type in ("triaxial", "biaxial", "simple_shear", "general")

    def initial_stress(self) -> np.ndarray:
        """Initial effective stress tensor (kPa): lateral, and lateral / K0 axially."""

        if not self.confined:
            return np.zeros((3, 3))
        if self.k0 <= 0.0:
            raise SimulationError("Initial Effective K0 must be positive")
        return np.diag([self.confining / self.k0, self.confining, self.confining])

    def validate(self) -> None:
        if not self.max_strain > 0.0:
            raise SimulationError("Maximum Strain must be positive")
        if self.max_strain > 1.0:
            raise SimulationError("Maximum Strain must not exceed 1")
        if self.steps > 100000:
            raise SimulationError("too many steps (max 100000)")
        if self.test_type == "general" and max(abs(v) for v in self.strain_ratio) == 0.0:
            raise SimulationError("General Test: the strain direction is zero")

    def history(self) -> np.ndarray:
        """Imposed (axial or shear) strain at the end of each step (start 0 excluded)."""

        sign = 1.0 if self.loading == "Compression" else -1.0
        up = np.linspace(0.0, sign * self.max_strain, self.steps + 1)[1:]
        if not self.cyclic:
            return up
        down = up[::-1][1:]
        cycle = np.concatenate([up, down, [0.0]])
        return np.tile(cycle, self.cycles)

    axial_history = history  # 13a name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "symbol": self.symbol,
            "test_type": self.test_type,
            "seepage": self.seepage,
            "loading": self.loading,
            "max_strain": self.max_strain,
            "steps": self.steps,
            "cyclic": self.cyclic,
            "cycles": self.cycles,
            "confining": self.confining,
            "k0": self.k0,
            "strain_ratio": list(self.strain_ratio),
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "TestSimulation":
        return cls(
            name=str(data.get("name", "")) or "Test",
            color=str(data.get("color", DEFAULT_COLOR)) or DEFAULT_COLOR,
            symbol=str(data.get("symbol", "o")),
            test_type=str(data.get("test_type", "uniaxial")),
            seepage=str(data.get("seepage", "Drained")),
            loading=str(data.get("loading", "Compression")),
            max_strain=float(data.get("max_strain", 0.1)),
            steps=int(data.get("steps", 100)),
            cyclic=bool(data.get("cyclic", False)),
            cycles=int(data.get("cycles", 1)),
            confining=float(data.get("confining", 100.0)),
            k0=float(data.get("k0", 1.0)),
            strain_ratio=tuple(data.get("strain_ratio", (1.0, 1.0, 1.0, 0.0, 0.0, 0.0))),
            visible=bool(data.get("visible", True)),
        )


# --------------------------------------------------------------- tensors

VOIGT = ((0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (0, 2))


def to_matrix(v: np.ndarray, engineering: bool) -> np.ndarray:
    m = np.zeros((3, 3))
    for k, (i, j) in enumerate(VOIGT):
        value = v[k] / 2.0 if (engineering and i != j) else v[k]
        m[i, j] = m[j, i] = value
    return m


def to_voigt(m: np.ndarray, engineering: bool) -> np.ndarray:
    return np.array([m[i, j] * (2.0 if (engineering and i != j) else 1.0) for i, j in VOIGT])


def elastic_matrix(young: float, poisson: float) -> np.ndarray:
    """Isotropic elasticity in principal components (kPa)."""

    lam, mu = _lame(young, poisson)
    return np.full((3, 3), lam) + np.eye(3) * 2.0 * mu


def _lame(young: float, poisson: float) -> tuple[float, float]:
    if young <= 0.0:
        raise SimulationError("Young's modulus must be positive")
    if not -1.0 < poisson < 0.5:
        raise SimulationError("Poisson's ratio must be in (-1, 0.5)")
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    return lam, young / (2.0 * (1.0 + poisson))


# ------------------------------------------------------------- strength

_TINY = 1e-12


@dataclass(frozen=True)
class Strength:
    """Pyramid faces S(x) and potential S_g(x) of MC / HB (kPa)."""

    kind: str  # "mc" | "hb"
    n_phi: float = 1.0
    sc: float = 0.0  # MC uniaxial compressive strength 2 c sqrt(N_phi)
    n_psi: float = 1.0
    sigci: float = 1.0
    mb: float = 1.0
    s: float = 1.0
    a: float = 0.5
    mg: float = 0.0  # HB potential (dilation parameter)

    @classmethod
    def mohr_coulomb(cls, c: float, phi_deg: float, psi_deg: float = 0.0, n_psi: float | None = None) -> "Strength":
        if not 0.0 <= phi_deg < 90.0:
            raise SimulationError("friction angle must be in [0, 90) degrees")
        sin = math.sin(math.radians(phi_deg))
        n_phi = (1.0 + sin) / (1.0 - sin)
        if n_psi is None:
            sin_psi = math.sin(math.radians(max(0.0, psi_deg)))
            n_psi = (1.0 + sin_psi) / (1.0 - sin_psi)
        return cls("mc", n_phi=n_phi, sc=2.0 * c * math.sqrt(n_phi), n_psi=n_psi)

    @classmethod
    def hoek_brown(cls, sigci: float, mb: float, s: float, a: float, mg: float = 0.0) -> "Strength":
        if sigci <= 0.0 or mb <= 0.0 or s < 0.0 or not 0.0 < a < 1.0:
            raise SimulationError("Hoek-Brown needs sigci > 0, mb > 0, s >= 0 and 0 < a < 1")
        return cls("hb", sigci=sigci, mb=mb, s=s, a=a, mg=max(0.0, mg))

    @property
    def apex(self) -> float:
        """Hydrostatic tensile apex of the pyramid (kPa)."""

        if self.kind == "mc":
            return -self.sc / (self.n_phi - 1.0) if self.n_phi > 1.0 + 1e-12 else -math.inf
        return -self.s * self.sigci / self.mb

    def S(self, x: float) -> float:
        if self.kind == "mc":
            return self.n_phi * x + self.sc
        base = max(self.mb * x / self.sigci + self.s, _TINY)
        return x + self.sigci * base**self.a

    def dS(self, x: float) -> float:
        if self.kind == "mc":
            return self.n_phi
        base = max(self.mb * x / self.sigci + self.s, _TINY)
        return 1.0 + self.a * self.mb * base ** (self.a - 1.0)

    def dSg(self, x: float) -> float:
        if self.kind == "mc":
            return self.n_psi
        if self.mg == 0.0:
            return 1.0
        base = max(self.mg * x / self.sigci + self.s, _TINY)
        return 1.0 + self.a * self.mg * base ** (self.a - 1.0)

    def d2Sg(self, x: float) -> float:
        if self.kind == "mc" or self.mg == 0.0:
            return 0.0
        base = max(self.mg * x / self.sigci + self.s, _TINY)
        return self.a * (self.a - 1.0) * self.mg**2 / self.sigci * base ** (self.a - 2.0)

    def deviator_at(self, sigma3: float) -> float:
        """Failure deviator sigma1 - sigma3 at a minor principal stress."""

        return self.S(sigma3) - sigma3

    def surfaces(self) -> list:
        return [PairFace(self, i, j) for i in range(3) for j in range(3) if i != j]


# ------------------------------------------------------- yield surfaces


class PairFace:
    """Pyramid face sigma_i - S(sigma_j) <= 0."""

    deviatoric = True

    def __init__(self, strength: Strength, i: int, j: int) -> None:
        self.st, self.i, self.j = strength, i, j

    def f(self, s: np.ndarray) -> float:
        return s[self.i] - self.st.S(s[self.j])

    def n(self, s: np.ndarray) -> np.ndarray:
        v = np.zeros(3)
        v[self.i] = 1.0
        v[self.j] = -self.st.dS(s[self.j])
        return v

    def m(self, s: np.ndarray) -> np.ndarray:
        v = np.zeros(3)
        v[self.i] = 1.0
        v[self.j] = -self.st.dSg(s[self.j])
        return v

    def dm(self, s: np.ndarray) -> np.ndarray:
        out = np.zeros((3, 3))
        out[self.j, self.j] = -self.st.d2Sg(s[self.j])
        return out


class TensionCutoff:
    """sigma_i >= -T (compression positive), associated (as in the reference program)."""

    deviatoric = False

    def __init__(self, i: int, tensile: float) -> None:
        self.i, self.t = i, max(0.0, tensile)

    def f(self, s: np.ndarray) -> float:
        return -s[self.i] - self.t

    def n(self, s: np.ndarray) -> np.ndarray:
        v = np.zeros(3)
        v[self.i] = -1.0
        return v

    m = n

    def dm(self, s: np.ndarray) -> np.ndarray:
        return np.zeros((3, 3))


_PDEV = np.eye(3) - np.full((3, 3), 1.0 / 3.0)


class DruckerPragerCone:
    """sqrt(J2) - k - q_phi p <= 0, potential sqrt(J2) - q_psi p (manual eqs. 4.1-4.2)."""

    deviatoric = True

    def __init__(self, k: float, q_phi: float, q_psi: float) -> None:
        self.k, self.q_phi, self.q_psi = k, q_phi, q_psi

    @staticmethod
    def _sj(s: np.ndarray) -> tuple[np.ndarray, float]:
        dev = s - s.mean()
        return dev, math.sqrt(max(0.5 * float(dev @ dev), 0.0))

    def f(self, s: np.ndarray) -> float:
        _, j = self._sj(s)
        return j - self.k - self.q_phi * s.mean()

    def _grad(self, s: np.ndarray, coef: float) -> np.ndarray:
        dev, j = self._sj(s)
        unit = dev / (2.0 * j) if j > _TINY else np.zeros(3)
        return unit - coef / 3.0

    def n(self, s: np.ndarray) -> np.ndarray:
        return self._grad(s, self.q_phi)

    def m(self, s: np.ndarray) -> np.ndarray:
        return self._grad(s, self.q_psi)

    def dm(self, s: np.ndarray) -> np.ndarray:
        dev, j = self._sj(s)
        if j <= _TINY:
            return np.zeros((3, 3))
        return _PDEV / (2.0 * j) - np.outer(dev, dev) / (4.0 * j**3)

    @property
    def apex(self) -> float:
        return -self.k / self.q_phi if self.q_phi > 0.0 else -math.inf


def _solve_active(surfaces, D, trial, active, tol, floor=-math.inf):
    """Newton on (sigma, dlambda) for an active set; None if it does not converge."""

    m = len(active)
    # iterates stay in the criterion's domain (Hoek-Brown: above the tensile apex)
    sig = np.maximum(trial, floor)
    dl = np.zeros(m)
    for _ in range(60):
        flows = [surfaces[k].m(sig) for k in active]
        r1 = sig - trial + D @ sum((dl[n] * flows[n] for n in range(m)), np.zeros(3))
        r2 = np.array([surfaces[k].f(sig) for k in active])
        if np.max(np.abs(r1)) < tol and np.max(np.abs(r2)) < tol:
            return sig, dl
        jac = np.zeros((3 + m, 3 + m))
        jac[:3, :3] = np.eye(3)
        for n, k in enumerate(active):
            jac[:3, :3] += dl[n] * D @ surfaces[k].dm(sig)
            jac[:3, 3 + n] = D @ flows[n]
            jac[3 + n, :3] = surfaces[k].n(sig)
        try:
            delta = np.linalg.solve(jac, -np.concatenate([r1, r2]))
        except np.linalg.LinAlgError:
            return None
        if not np.all(np.isfinite(delta)):
            return None
        sig = np.maximum(sig + delta[:3], floor)
        dl = dl + delta[3:]
    return None


def return_map_surfaces(surfaces, apex: float, D: np.ndarray, trial: np.ndarray, scale: float):
    """Principal stresses on or inside the surfaces: (sigma, yielded, [(surface, dlambda)])."""

    scale = max(1.0, float(np.max(np.abs(trial))), scale)
    tol = 1e-10 * scale
    hb_apices = [s.st.apex for s in surfaces if isinstance(s, PairFace) and s.st.kind == "hb"]
    floor = max(hb_apices) * (1.0 - 1e-9) if hb_apices else -math.inf
    values = [s.f(trial) for s in surfaces]
    fmax = max(values)
    if fmax <= tol:
        return trial, False, []
    active = [k for k, v in enumerate(values) if v >= fmax - 1e-9 * scale]
    for _ in range(16):
        if len(active) > 3:
            break
        solved = _solve_active(surfaces, D, trial, active, tol, floor)
        if solved is None:
            if len(active) > 1:
                # degenerate set (e.g. coincident faces): keep the most violated one
                active = [max(active, key=lambda k: surfaces[k].f(trial))]
                solved = _solve_active(surfaces, D, trial, active, tol, floor)
            if solved is None:
                break
        sig, dl = solved
        if np.any(dl < -tol / scale):
            active.pop(int(np.argmin(dl)))
            if not active:
                break
            continue
        violated = [(v, k) for k in range(len(surfaces)) if k not in active and (v := surfaces[k].f(sig)) > tol]
        if not violated:
            return sig, True, [(surfaces[k], d) for k, d in zip(active, dl)]
        active.append(max(violated)[1])
    # robust fallback: every set of up to three surfaces violated by the trial
    # (or by its returns), keeping the admissible return closest in energy
    candidates = [k for k, v in enumerate(values) if v > tol]
    best = None
    Dinv = np.linalg.inv(D)
    from itertools import combinations

    for size in (1, 2, 3):
        for combo in combinations(candidates, size):
            solved = _solve_active(surfaces, D, trial, list(combo), tol, floor)
            if solved is None:
                continue
            sig, dl = solved
            if np.any(dl < -tol / scale) or any(s.f(sig) > tol * 10.0 for s in surfaces):
                continue
            diff = trial - sig
            energy = float(diff @ Dinv @ diff)
            if best is None or energy < best[0]:
                best = (energy, sig, [(surfaces[k], d) for k, d in zip(combo, dl)])
        if best is not None:
            return best[1], True, best[2]
    if math.isinf(apex):
        raise SimulationError("stress state beyond a surface without tensile apex")
    point = np.full(3, apex)
    # plastic multipliers are not split at the apex; report the whole return as deviatoric-free
    return point, True, []


def return_map(model: Strength, D: np.ndarray, trial: np.ndarray) -> tuple[np.ndarray, bool]:
    """13a interface: MC / HB pyramid only."""

    scale = model.sc if model.kind == "mc" else model.sigci
    sig, yielded, _ = return_map_surfaces(model.surfaces(), model.apex, D, trial, scale)
    return sig, yielded


# -------------------------------------------------------- material models


@dataclass(frozen=True, eq=False)
class PlasticSet:
    """Yield surfaces of one strength level (peak or residual).

    key: the defining parameters; equal keys = same strength (no brittle drop).
    """

    surfaces: tuple
    apex: float
    scale: float
    key: tuple = ()


def _pyramid_set(strength: Strength, tensile: float | None, key: tuple) -> PlasticSet:
    surfaces = list(strength.surfaces())
    apex = strength.apex
    if tensile is not None:
        surfaces += [TensionCutoff(i, tensile) for i in range(3)]
        apex = max(apex, -max(0.0, tensile))
    scale = strength.sc if strength.kind == "mc" else strength.sigci
    return PlasticSet(tuple(surfaces), apex, max(scale, 1.0), (strength, tensile))


def _dp_set(k: float, q_phi: float, q_psi: float, tensile: float, key: tuple) -> PlasticSet:
    cone = DruckerPragerCone(k, q_phi, q_psi)
    surfaces = [cone] + [TensionCutoff(i, tensile) for i in range(3)]
    return PlasticSet(tuple(surfaces), max(cone.apex, -max(0.0, tensile)), max(abs(k), 1.0), ("dp", k, q_phi, q_psi, tensile))


class _Elastic:
    def __init__(self, stiffness: Mapping) -> None:
        stiff = stiffness_from(stiffness)
        self.lam, self.mu = _lame(stiff["young"], stiff["poisson"])
        self.D = np.full((3, 3), self.lam) + np.eye(3) * 2.0 * self.mu

    def trial(self, S: np.ndarray, dE: np.ndarray) -> np.ndarray:
        return S + self.lam * np.trace(dE) * np.eye(3) + 2.0 * self.mu * dE


def _spectral(trial: np.ndarray):
    w, V = np.linalg.eigh(trial)
    return w, V


def _rebuild(V: np.ndarray, w: np.ndarray) -> np.ndarray:
    return (V * w) @ V.T


class ElasticModel:
    """Material Type "Elastic" (spec 026): linear elastic at any stress, never yields."""

    def __init__(self, elastic: _Elastic) -> None:
        self.el = elastic

    def initial_state(self, S0: np.ndarray) -> dict:
        return {"failed": False}

    def update(self, S: np.ndarray, state: dict, dE: np.ndarray):
        return self.el.trial(S, dE), state, False

    def peak_violated(self, S: np.ndarray, dE: np.ndarray) -> bool:
        return False


class PerfectBrittleModel:
    """Elastic-perfectly plastic or elastic-brittle-plastic (peak -> residual)."""

    def __init__(self, elastic: _Elastic, peak: PlasticSet, residual: PlasticSet) -> None:
        self.el = elastic
        self.peak, self.residual = peak, residual
        self.brittle = peak.key != residual.key

    def initial_state(self, S0: np.ndarray) -> dict:
        w = np.linalg.eigvalsh(S0)
        if max(s.f(w) for s in self.peak.surfaces) > 1e-9 * max(1.0, self.peak.scale, float(np.max(np.abs(w)))):
            raise SimulationError("the initial stress state (Initial Effective Lateral Stress and K0) is outside the yield surface")
        return {"failed": False}

    def update(self, S: np.ndarray, state: dict, dE: np.ndarray):
        trial = self.el.trial(S, dE)
        w, V = _spectral(trial)
        current = self.residual if state["failed"] else self.peak
        new, yielded, _ = return_map_surfaces(current.surfaces, current.apex, self.el.D, w, current.scale)
        failed = state["failed"]
        if yielded and not failed and self.brittle:
            new, _, _ = return_map_surfaces(self.residual.surfaces, self.residual.apex, self.el.D, w, self.residual.scale)
            failed = True
        return _rebuild(V, new), {"failed": failed}, yielded

    def peak_violated(self, S: np.ndarray, dE: np.ndarray) -> bool:
        w = np.linalg.eigvalsh(self.el.trial(S, dE))
        tol = 1e-10 * max(1.0, self.peak.scale, float(np.max(np.abs(w))))
        return max(s.f(w) for s in self.peak.surfaces) > tol


class VerticalCap:
    """Vertical cap p <= pc (as in the reference program), associated."""

    deviatoric = False

    def __init__(self, pc: float) -> None:
        self.pc = pc

    def f(self, s: np.ndarray) -> float:
        return float(s.mean()) - self.pc

    def n(self, s: np.ndarray) -> np.ndarray:
        return np.full(3, 1.0 / 3.0)

    m = n

    def dm(self, s: np.ndarray) -> np.ndarray:
        return np.zeros((3, 3))


class EllipticalCap:
    """Elliptical cap (as in the reference program), associated, compression positive:
    (q / M_f)^2 + (p + c / tan phi_f) (p - pc) <= 0 for p above the top of the
    ellipse, which touches the ultimate cone q = M_f (p + c / tan phi_f); left
    of the top the cap continues as q <= its maximum (never active before the
    cone). M_f of triaxial compression (Lode dependence not modelled)."""

    deviatoric = False

    def __init__(self, pc: float, m_f: float, offset: float) -> None:
        self.pc, self.M, self.a = pc, m_f, offset
        self.top = 0.5 * (pc - offset)

    def _pq(self, s):
        p = float(s.mean())
        dev = s - p
        return p, dev, math.sqrt(1.5 * float(dev @ dev))

    def f(self, s: np.ndarray) -> float:
        p, _, q = self._pq(s)
        if p >= self.top:
            return (q / self.M) ** 2 + (p + self.a) * (p - self.pc)
        return (q / self.M) ** 2 - (0.5 * (self.pc + self.a)) ** 2

    def n(self, s: np.ndarray) -> np.ndarray:
        p, dev, _ = self._pq(s)
        dp = (2.0 * p + self.a - self.pc) if p >= self.top else 0.0
        return 3.0 / self.M**2 * dev + dp / 3.0

    m = n

    def dm(self, s: np.ndarray) -> np.ndarray:
        p = float(s.mean())
        out = 3.0 / self.M**2 * _PDEV
        if p >= self.top:
            out = out + 2.0 / 9.0 * np.ones((3, 3))
        return out


def _interp_table(rows, x: float, column: int) -> float:
    xs = [float(r[0]) for r in rows]
    ys = [float(r[column]) for r in rows]
    return float(np.interp(x, xs, ys))


def _table(rows, columns: int, name: str) -> list:
    out = sorted((tuple(float(v) for v in list(r)[:columns]) for r in (rows or [])), key=lambda r: r[0])
    if len(out) < 1 or any(len(r) < columns for r in out):
        raise SimulationError(f"Softening-Hardening: the {name} needs at least one row of {columns} values")
    return out


class SofteningHardeningModel:
    """Softening-Hardening model of the reference program (manual §11): cone, cap and tension cut-off.

    Cone (§11.1): Mohr-Coulomb surface with the mobilized friction angle and
    cohesion as functions of the deviatoric plastic strain of the cone,
    "Hyperbolic" (eq. 11.4, cohesion keeping the apex at c / tan phi_f) or
    "Tabular" (piecewise linear (e_q^p, phi, c) table, which can soften).
    Cap (§11.2): "Vertical" p <= pc or "Elliptical" (eq. 11.9), associated,
    pc0 = Initial Mean Stress (raised to the initial mean stress if below);
    hardening "Cam-Clay" pc_{n+1} = pc_n exp(de_v^p / Lambda), so Lambda
    Kappa is Lambda = (lambda - kappa) / v by the Cam-clay hardening rule
    (Wood 1990, eq. 4.21; spec 026), 0 = rigid cap or "Tabular" (e_v^p, pc). The
    cone hardening is implicit (bracketed root); the cap hardening is
    updated at the end of each step (explicit, small steps).
    """

    def __init__(self, elastic: _Elastic, params: Mapping) -> None:
        self.el = elastic
        self.c = float(params["peak_cohesion"])
        self.phi_f = float(params["peak_friction"])
        self.psi_f = float(params.get("dilation_angle", 0.0))
        self.A = float(params.get("hardening_property", 0.005))
        self.tensile = float(params.get("peak_tensile", 0.0))
        self.dilation = str(params.get("cone_dilation_type", CONE_DILATION_TYPES[0]))
        self.tabular = str(params.get("cone_hardening_type", "Hyperbolic")) == "Tabular"
        self.cap = str(params.get("cap_type", "None"))
        if self.cap not in ("Vertical", "Elliptical"):
            self.cap = "None"
        self.cap_tabular = str(params.get("cap_hardening_type", "Cam-Clay")) == "Tabular"
        self.pc0 = float(params.get("initial_mean_stress", 1000.0))
        self.lk = float(params.get("lambda_kappa", 0.0))
        if not 0.0 < self.phi_f < 90.0:
            raise SimulationError("Softening-Hardening needs a failure friction angle in (0, 90) degrees")
        if not self.tabular and self.A <= 0.0:
            raise SimulationError("Softening-Hardening needs a positive Hardening Property (A)")
        self.tan_f = math.tan(math.radians(self.phi_f))
        if self.tabular:
            self.cone_table = _table(params.get("cone_hardening_table"), 3, "cone hardening table")
        if self.cap != "None" and self.cap_tabular:
            self.cap_table = _table(params.get("cap_hardening_table"), 2, "cap hardening table")
        sin = math.sin(math.radians(self.phi_f))
        self.m_f = 6.0 * sin / (3.0 - sin)

    def mobilized(self, kappa: float) -> float:
        """Mobilized friction angle (deg) at deviatoric plastic strain kappa (eq. 11.4 or table)."""

        if self.tabular:
            return _interp_table(self.cone_table, kappa, 1)
        return math.degrees(math.atan(self.tan_f * kappa / (kappa + self.A)))

    def cohesion(self, kappa: float, phi: float) -> float:
        if self.tabular:
            return max(_interp_table(self.cone_table, kappa, 2), 0.0)
        return self.c * math.tan(math.radians(phi)) / self.tan_f  # apex stays at c / tan(phi_f)

    def _set(self, kappa: float, n_psi: float | None, pc: float | None) -> PlasticSet:
        phi = min(max(self.mobilized(kappa), 1e-9), 89.0)
        c_m = self.cohesion(kappa, phi)
        psi = self.psi_f * phi / self.phi_f
        st = Strength.mohr_coulomb(c_m, phi, psi, n_psi=n_psi)
        ps = _pyramid_set(st, self.tensile, ("sh", kappa))
        if self.cap == "None" or pc is None:
            return ps
        cap = VerticalCap(pc) if self.cap == "Vertical" else EllipticalCap(pc, self.m_f, self.c / self.tan_f)
        return PlasticSet(ps.surfaces + (cap,), ps.apex, max(ps.scale, pc), ps.key)

    def _n_psi(self, S: np.ndarray) -> float | None:
        if self.dilation != "Compaction-Dilation":
            return None
        # eq. 11.7: d = de_v^p / de_q^p = M_psi - eta (triaxial compression M_psi),
        # converted to the Mohr-Coulomb face flow N with d = 3 (1 - N) / (2 + N)
        sin = math.sin(math.radians(self.psi_f))
        m_psi = 6.0 * sin / (3.0 - sin)
        p = float(np.trace(S)) / 3.0
        dev = S - p * np.eye(3)
        q = math.sqrt(1.5 * float(np.sum(dev * dev)))
        eta = q / p if p > _TINY else 0.0
        d = max(m_psi - eta, -2.9)
        return (3.0 - 2.0 * d) / (3.0 + d)

    def initial_state(self, S0: np.ndarray) -> dict:
        w = np.linalg.eigvalsh(S0)
        if np.min(w) < -max(0.0, self.tensile) - 1e-9:
            raise SimulationError("the initial stress state violates the tension cut-off")
        state = {"kappa": 0.0}
        if self.cap != "None":
            pc = self.cap_table[0][1] if self.cap_tabular else self.pc0
            p0 = float(w.mean())
            state.update({"pc": max(pc, p0), "ev_cap": 0.0})
        return state

    @staticmethod
    def _dev_norm(eps: np.ndarray) -> float:
        e = eps - eps.mean()
        return math.sqrt(2.0 / 3.0 * float(e @ e))

    def _attempt(self, w: np.ndarray, kappa: float, n_psi, pc):
        ps = self._set(kappa, n_psi, pc)
        new, yielded, contrib = return_map_surfaces(ps.surfaces, ps.apex, self.el.D, w, ps.scale)
        deps_p = sum((dl * s.m(new) for s, dl in contrib if s.deviatoric), np.zeros(3))
        dev_cap = sum((dl * float(np.sum(s.m(new))) for s, dl in contrib if isinstance(s, (VerticalCap, EllipticalCap))), 0.0)
        return new, yielded, self._dev_norm(deps_p), dev_cap

    def _cap_pressure(self, state: dict, dev_cap: float) -> dict:
        if self.cap == "None":
            return {}
        ev = state["ev_cap"] + max(dev_cap, 0.0)
        if self.cap_tabular:
            pc = _interp_table(self.cap_table, ev, 1)
        elif self.lk > 0.0:
            pc = state["pc"] * math.exp(max(dev_cap, 0.0) / self.lk)
        else:
            pc = state["pc"]  # Lambda Kappa = 0: rigid cap
        return {"pc": pc, "ev_cap": ev}

    def update(self, S: np.ndarray, state: dict, dE: np.ndarray):
        trial = self.el.trial(S, dE)
        w, V = _spectral(trial)
        k0 = state["kappa"]
        pc = state.get("pc")
        n_psi = self._n_psi(S)
        new, yielded, dk, dev_cap = self._attempt(w, k0, n_psi, pc)
        if not yielded or dk <= 0.0:
            return _rebuild(V, new), {"kappa": k0, **self._cap_pressure(state, dev_cap)}, yielded

        def g(k):
            return k - k0 - self._attempt(w, k, n_psi, pc)[2]

        # implicit cone hardening: kappa = k0 + dk(kappa); bracket and solve
        lo, hi = k0, k0 + dk
        g_hi = g(hi)
        for _ in range(60):
            if g_hi >= 0.0:
                break
            hi = k0 + 2.0 * (hi - k0)
            g_hi = g(hi)
        else:
            raise _StepFailure()
        from scipy.optimize import brentq

        kappa = brentq(g, lo, hi, xtol=1e-15, rtol=1e-12)
        new, yielded, _, dev_cap = self._attempt(w, kappa, n_psi, pc)
        return _rebuild(V, new), {"kappa": kappa, **self._cap_pressure(state, dev_cap)}, yielded


class CamClayModel:
    """Cam-Clay / Modified Cam-Clay (as in the reference program), drained or undrained strain driven."""

    def __init__(self, params: Mapping, stiffness: Mapping, modified: bool) -> None:
        st = stiffness_from(stiffness)
        self.M = float(params["critical_state_slope"])
        self.lam = float(params["lambda"])
        self.kap = float(params["kappa"])
        self.modified = modified
        value = float(params["specific_volume_unit_pressure"])
        # combo of the reference program "Specific Volume at Unit Pressure": the value is N (virgin
        # line) or Gamma (CSL); manual eqs. 8.3-8.4 relate them.
        if str(params.get("volume_reference", "")).startswith("Critical State Line"):
            value += (self.lam - self.kap) * (math.log(2.0) if modified else 1.0)
        self.N = value
        self.ocr = float(params["ocr"])
        # reference program: "Initial State of Consolidation": OCR or Preconsolidation Pressure (Po)
        self.po = float(params.get("preconsolidation_stress", 0.0))
        self.use_po = str(params.get("initial_consolidation", "OCR")).startswith("Preconsolidation")
        self.nu = float(st["poisson"])
        self.constant_g = st["elastic_parameter"] == "Constant Shear Modulus"
        self.G0 = float(st["shear_modulus"])
        if self.constant_g and self.G0 <= 0.0:
            raise SimulationError("the shear modulus must be positive")
        if self.M <= 0.0 or self.kap <= 0.0 or self.lam <= self.kap:
            raise SimulationError("Cam-Clay needs M > 0 and lambda > kappa > 0")
        if not self.use_po and self.ocr < 1.0:
            raise SimulationError("the overconsolidation ratio must be >= 1")
        if not -1.0 < self.nu < 0.5:
            raise SimulationError("Poisson's ratio must be in (-1, 0.5)")

    # yield function and derivatives (p, q compression positive)
    def F(self, p, q, pc):
        if self.modified:
            return q * q + self.M**2 * p * (p - pc)
        return q + self.M * p * math.log(max(p, _TINY) / pc)

    def Fp(self, p, q, pc):
        if self.modified:
            return self.M**2 * (2.0 * p - pc)
        return self.M * (math.log(max(p, _TINY) / pc) + 1.0)

    def Fq(self, p, q, pc):
        return 2.0 * q if self.modified else 1.0

    def shear_modulus(self, p: float, v: float) -> float:
        if self.constant_g:
            return self.G0
        bulk = v * p / self.kap
        return 3.0 * bulk * (1.0 - 2.0 * self.nu) / (2.0 * (1.0 + self.nu))

    def initial_state(self, S0: np.ndarray) -> dict:
        p0 = float(np.trace(S0)) / 3.0
        if p0 <= 0.0:
            raise SimulationError("Cam-Clay needs a positive initial mean stress (set the initial lateral stress)")
        dev = S0 - p0 * np.eye(3)
        q0 = math.sqrt(1.5 * float(np.sum(dev * dev)))
        # preconsolidation pressure that puts the initial stress on the surface (OCR = 1)
        if self.modified:
            pc_on = p0 + q0 * q0 / (self.M**2 * p0)
        else:
            pc_on = p0 * math.exp(q0 / (self.M * p0))
        # Po below the current state: readjusted to it (as in the reference program)
        pc = max(self.po, pc_on) if self.use_po else self.ocr * pc_on
        v0 = self.N - self.lam * math.log(pc) + self.kap * math.log(pc / p0)
        if v0 <= 1.0:
            raise SimulationError("the initial specific volume is not above 1: check N, lambda and the stresses")
        return {"pc": pc, "v": v0}

    def update(self, S: np.ndarray, state: dict, dE: np.ndarray):
        from scipy.optimize import fsolve

        pc_n, v = state["pc"], state["v"]
        p_n = float(np.trace(S)) / 3.0
        s_n = S - p_n * np.eye(3)
        dev_ = float(np.trace(dE))
        de = dE - dev_ / 3.0 * np.eye(3)
        G = self.shear_modulus(p_n, v)
        p_tr = p_n * math.exp(v * dev_ / self.kap)
        s_tr = s_n + 2.0 * G * de
        q_tr = math.sqrt(1.5 * float(np.sum(s_tr * s_tr)))
        v_new = v * math.exp(-dev_)
        norm = self.M**2 * pc_n**2 if self.modified else self.M * pc_n
        if self.F(p_tr, q_tr, pc_n) <= 1e-10 * norm:
            return p_tr * np.eye(3) + s_tr, {"pc": pc_n, "v": v_new}, False

        def residual(x):
            p, q, pc, dl = x
            p = max(p, _TINY)
            pc = max(pc, _TINY)
            fp = self.Fp(p, q, pc)
            return [
                (p - p_n * math.exp(v * (dev_ - dl * fp) / self.kap)) / pc_n,
                (q - q_tr + 3.0 * G * dl * self.Fq(p, q, pc)) / pc_n,
                (pc - pc_n * math.exp(v * dl * fp / (self.lam - self.kap))) / pc_n,
                self.F(p, q, pc) / norm,
            ]

        x0 = [p_tr, q_tr, pc_n, 0.0]
        sol, info, ier, _ = fsolve(residual, x0, full_output=True, xtol=1e-13)
        converged = ier == 1 and max(abs(r) for r in residual(sol)) <= 1e-9 and sol[0] > 0.0 and sol[3] >= -1e-12
        if converged and sol[1] < -1e-9 and not self.modified:
            # Cam-Clay tip (p = pc, q = 0) is a corner: return to the vertex
            # with the deviatoric plastic strain inside its cone |de_q^p| <= de_v^p / M
            x = (math.log(p_n / pc_n) + v * dev_ / self.kap) / (v / self.kap + v / (self.lam - self.kap))
            if x < 0.0 or q_tr / (3.0 * G) > x / self.M + 1e-15:
                raise _StepFailure()
            p = p_n * math.exp(v * (dev_ - x) / self.kap)
            return p * np.eye(3), {"pc": p, "v": v_new}, True
        if not converged or sol[1] < -1e-9:
            raise _StepFailure()
        p, q, pc, _ = sol
        q = max(q, 0.0)
        s = s_tr * (q / q_tr) if q_tr > _TINY else s_tr
        return p * np.eye(3) + s, {"pc": pc, "v": v_new}, True


class _StepFailure(Exception):
    """A constitutive update did not converge (the driver subdivides the step)."""


def _invariants(S: np.ndarray) -> tuple[float, np.ndarray, float, float]:
    """(p, deviator s, q, sin 3theta) of a compression-positive stress; sin 3theta = +1 in TC."""

    p = float(np.trace(S)) / 3.0
    s = S - p * np.eye(3)
    j2 = 0.5 * float(np.sum(s * s))
    q = math.sqrt(3.0 * j2)
    if j2 <= 1e-30:
        return p, s, q, 1.0
    sin3 = 1.5 * math.sqrt(3.0) * float(np.linalg.det(s)) / j2**1.5
    return p, s, q, max(-1.0, min(1.0, sin3))


class NorSandModel:
    """NorSand (Jefferies 1993; Jefferies and Shuttle 2002, 2005).

    No public theory manual of the reference program's implementation exists;
    the model is assembled from published sources and checked against the
    NorSand tutorial of the reference program (Fraser River sand, undrained
    triaxial, which the reference program compares
    with Jefferies' NorSand spreadsheet):
    - Elasticity, CSL, state parameters, M_i, chi_i, Lode function g(theta)
      and the hardening rule as published for FLAC3D 9.2 (Itasca, NorSand
      model, eqs. 1-19), compression positive, natural logarithms:
      G = G_ref (p / p_ref)^m (>= G_min), K = 2 (1 + nu) G / (3 (1 - 2 nu));
      e_c = Gamma - lambda ln p (Gamma at 1 kPa); psi = e - e_c(p),
      psi_i = e - e_c(p_i); chi_i = chi_tc / (1 - lambda chi_tc / M_tc);
      M_i = g(theta) (M_tc - N chi_i |psi_i|), g = [2c^4/(c^4+1+(c^4-1) sin3theta)]^(1/4),
      c = 3 / (3 + M_tc); dp_i / p_i = H g (p/p_i)^2 (exp(-chi_i psi_i / M_i,tc) - p_i/p) de_q^p,
      H = H0 - Hy psi.
    - Yield surface and flow with Nova's volumetric coupling N (Jefferies 1993,
      Jefferies and Shuttle 2002): eta = (M_i / N) [1 - (1 - N) (p / p_i)^(N/(1-N))],
      associated, D^p = (M_i - eta) / (1 - N); for N = 0 it becomes the
      FLAC3D form eta / M_i = 1 - ln(p / p_i), D^p = M_i - eta. The Nova form
      reproduces the tutorial better (onset of instability and pore pressure
      peak within 3 %; end of the test about 10 % below, see spec 013 plan).
    - Initial state: e0 = e_c(p0) + psi0; p_i = OCR x the image stress that
      puts the initial stress on the yield surface.
    Integration: explicit substeps of at most 1e-4 strain, consistency with the
    full dF/dp_i (M_i depends on p_i through psi_i) and drift correction of p_i.
    "Cap Softening" (check box of the reference program) is stored but not modelled: its
    formulation is not published (FLAC3D calls its softening term
    "still in debate" and not supported).
    """

    SUBSTEP = 1e-4

    def __init__(self, params: Mapping, stiffness: Mapping) -> None:
        self.Mtc = float(params["m_tc"])
        self.lam = float(params["lambda"])
        self.H0 = float(params["h0"])
        self.Hy = float(params.get("hy", 0.0))
        self.chi_tc = float(params["chi_tc"])
        self.Nc = float(params["n"])
        self.psi0 = float(params["psi0"])
        self.Gamma = float(params["gamma"])
        self.ocr = float(params.get("ocr", 1.0))
        st = stiffness_from(stiffness)
        self.g_ref, self.p_ref = st["g_ref"], st["p_ref"]
        self.g_exp, self.g_min, self.nu = st["g_exp"], st["g_min"], st["ns_poisson"]
        if self.Mtc <= 0.0 or self.lam <= 0.0 or self.chi_tc <= 0.0 or self.H0 <= 0.0:
            raise SimulationError("NorSand needs positive M_tc, lambda, chi_tc and H0")
        if not 0.0 <= self.Nc < 1.0:
            raise SimulationError("NorSand needs 0 <= N < 1")
        if self.ocr < 1.0:
            raise SimulationError("the overconsolidation ratio must be >= 1")
        if self.g_ref <= 0.0 or self.p_ref <= 0.0 or not -1.0 < self.nu < 0.5:
            raise SimulationError("NorSand stiffness needs G_ref > 0, p_ref > 0 and -1 < nu < 0.5")
        ratio = self.lam * self.chi_tc / self.Mtc
        if ratio >= 1.0:
            raise SimulationError("NorSand: lambda chi_tc / M_tc must be below 1")
        self.chi_i = self.chi_tc / (1.0 - ratio)
        self.c = 3.0 / (3.0 + self.Mtc)
        self.a = self.Nc / (1.0 - self.Nc)  # Nova exponent (0: logarithmic surface)

    def e_c(self, p: float) -> float:
        return self.Gamma - self.lam * math.log(max(p, _TINY))

    def g(self, sin3: float) -> float:
        c4 = self.c**4
        return (2.0 * c4 / (c4 + 1.0 + (c4 - 1.0) * sin3)) ** 0.25

    def moduli(self, p: float) -> tuple[float, float]:
        G = max(self.g_ref * (max(p, 0.0) / self.p_ref) ** self.g_exp, self.g_min, _TINY)
        return 2.0 * (1.0 + self.nu) * G / (3.0 * (1.0 - 2.0 * self.nu)), G

    def m_itc(self, e: float, p_i: float) -> float:
        return self.Mtc - self.Nc * self.chi_i * abs(e - self.e_c(p_i))

    def eta_surface(self, m_i: float, ratio: float) -> float:
        """Stress ratio of the yield surface at p / p_i = ratio."""

        if self.a == 0.0:
            return m_i * (1.0 - math.log(ratio))
        return m_i / self.Nc * (1.0 - (1.0 - self.Nc) * ratio**self.a)

    def F(self, S: np.ndarray, e: float, p_i: float) -> float:
        p, _, q, sin3 = _invariants(S)
        if p <= 0.0:
            return math.inf
        return q - p * self.eta_surface(self.g(sin3) * self.m_itc(e, p_i), p / p_i)

    def image_on_surface(self, S: np.ndarray, e: float, guess: float) -> float:
        """p_i putting S on the yield surface (fixed point: M_i depends on psi_i(p_i))."""

        p, _, q, sin3 = _invariants(S)
        eta = q / p
        p_i = guess
        for _ in range(60):
            m_i = self.g(sin3) * self.m_itc(e, p_i)
            if m_i <= 0.0:
                return p_i
            if self.a == 0.0:
                new = p * math.exp(eta / m_i - 1.0)
            else:
                x = max((1.0 - self.Nc * eta / m_i) / (1.0 - self.Nc), 1e-12)
                new = p * x ** (-1.0 / self.a)
            if abs(new - p_i) <= 1e-12 * p_i:
                return new
            p_i = new
        return p_i

    def initial_state(self, S0: np.ndarray) -> dict:
        p0 = float(np.trace(S0)) / 3.0
        if p0 <= 0.0:
            raise SimulationError("NorSand needs a positive initial mean stress (set the initial lateral stress)")
        e0 = self.e_c(p0) + self.psi0
        p_i = self.ocr * self.image_on_surface(S0, e0, p0 / 2.0)
        return {"e": e0, "p_i": p_i}

    def _plastic(self, S, e, p_i, dE, K, G):
        p, s, q, sin3 = _invariants(S)
        gth = self.g(sin3)
        psi_i = e - self.e_c(p_i)
        m_itc = self.Mtc - self.Nc * self.chi_i * abs(psi_i)
        m_i = gth * m_itc
        ratio = p / p_i
        if self.a == 0.0:
            dpF = m_i * math.log(ratio)  # = M_i - eta on the surface
            dF_dpi_m = -p * m_i / p_i
            dF_dm = -p * (1.0 - math.log(ratio))
        else:
            x = ratio**self.a
            dpF = -(m_i / self.Nc) * (1.0 - x)  # = (M_i - eta) / (1 - N) on the surface
            dF_dpi_m = -p * m_i * x / p_i
            dF_dm = -(p / self.Nc) * (1.0 - (1.0 - self.Nc) * x)
        unit = 1.5 * s / q if q > _TINY else np.zeros((3, 3))
        n = dpF / 3.0 * np.eye(3) + unit
        Dn = K * np.trace(n) * np.eye(3) + 2.0 * G * (n - np.trace(n) / 3.0 * np.eye(3))
        psi = e - self.e_c(p)
        H = self.H0 - self.Hy * psi
        h = p_i * H * gth * ratio**2 * (math.exp(-self.chi_i * psi_i / m_itc) - 1.0 / ratio)
        # dF/dp_i including M_i(psi_i(p_i)): d|psi_i|/dp_i = sign(psi_i) lambda / p_i
        dm_dpi = -gth * self.Nc * self.chi_i * math.copysign(1.0, psi_i) * self.lam / p_i
        dF_dpi = dF_dpi_m + dF_dm * dm_dpi
        denominator = float(np.sum(n * Dn)) - dF_dpi * h
        loading = float(np.sum(Dn * dE))
        if denominator <= 0.0 or loading <= 0.0:
            return None
        return loading / denominator, n, h

    def update(self, S: np.ndarray, state: dict, dE: np.ndarray):
        e, p_i = state["e"], state["p_i"]
        dev = dE - np.trace(dE) / 3.0 * np.eye(3)
        size = max(math.sqrt(2.0 / 3.0 * float(np.sum(dev * dev))), abs(float(np.trace(dE))))
        n_sub = max(1, int(math.ceil(size / self.SUBSTEP)))
        d = dE / n_sub
        yielded = False
        for _ in range(n_sub):
            plastic_step = False
            p = float(np.trace(S)) / 3.0
            if p <= 0.0:
                raise _StepFailure()
            K, G = self.moduli(p)
            dS_el = K * np.trace(d) * np.eye(3) + 2.0 * G * (d - np.trace(d) / 3.0 * np.eye(3))
            on_surface = self.F(S, e, p_i) >= -1e-8 * p
            plastic = self._plastic(S, e, p_i, d, K, G) if on_surface else None
            if plastic is None:
                trial = S + dS_el
                if self.F(trial, e, p_i) <= 0.0 or on_surface:
                    S = trial  # elastic (or elastic unloading from the surface)
                else:
                    # elastic up to the surface, plastic for the rest (bisection on the fraction)
                    lo, hi = 0.0, 1.0
                    for _ in range(40):
                        mid = 0.5 * (lo + hi)
                        if self.F(S + mid * dS_el, e, p_i) > 0.0:
                            hi = mid
                        else:
                            lo = mid
                    S = S + lo * dS_el
                    rest = (1.0 - lo) * d
                    K, G = self.moduli(float(np.trace(S)) / 3.0)
                    plastic = self._plastic(S, e, p_i, rest, K, G)
                    if plastic is None:
                        S = S + K * np.trace(rest) * np.eye(3) + 2.0 * G * (rest - np.trace(rest) / 3.0 * np.eye(3))
                    else:
                        S, p_i = self._apply(S, p_i, rest, plastic, K, G)
                        plastic_step = True
            else:
                S, p_i = self._apply(S, p_i, d, plastic, K, G)
                plastic_step = True
            e = e - (1.0 + e) * float(np.trace(d))
            if plastic_step:
                yielded = True
                p_i = self.image_on_surface(S, e, p_i)  # drift correction onto the surface
        return S, {"e": e, "p_i": p_i}, yielded

    @staticmethod
    def _apply(S, p_i, d, plastic, K, G):
        lam_dot, n, h = plastic
        dp = d - lam_dot * n
        S = S + K * np.trace(dp) * np.eye(3) + 2.0 * G * (dp - np.trace(dp) / 3.0 * np.eye(3))
        return S, max(p_i + h * lam_dot, _TINY)


def build_model(criterion: str, params: Mapping, stiffness: Mapping | None):
    """Constitutive model of a material for the test driver."""

    p = params
    residual_is_peak = bool(p.get("set_residual_to_peak", True))
    stiff = stiffness_from(stiffness)
    if criterion in ("cam_clay", "modified_cam_clay"):
        return CamClayModel(p, stiff, criterion == "modified_cam_clay")
    if criterion == "norsand":
        return NorSandModel(p, stiff)
    elastic = _Elastic(stiff)
    if criterion in ("mohr_coulomb", "hoek_brown") and p.get("material_type") == "Elastic":
        return ElasticModel(elastic)  # spec 026 RF-8
    if criterion == "softening_hardening":
        return SofteningHardeningModel(elastic, p)
    if criterion == "drucker_prager":
        qpsi = float(p.get("dilation_parameter", 0.0))
        peak = _dp_set(float(p["peak_k"]), float(p["peak_q"]), qpsi, float(p.get("peak_tensile", 0.0)), ("dp", "peak"))
        if residual_is_peak:
            return PerfectBrittleModel(elastic, peak, peak)
        residual = _dp_set(float(p["residual_k"]), float(p["residual_q"]), qpsi, float(p.get("residual_tensile", 0.0)), ("dp", "res"))
        return PerfectBrittleModel(elastic, peak, residual)
    peak_st, residual_st = strengths(criterion, p)
    if criterion == "mohr_coulomb":
        tp = float(p.get("peak_tensile", 0.0))
        tr = tp if residual_is_peak else float(p.get("residual_tensile", 0.0))
        peak = _pyramid_set(peak_st, tp, ("mc", "peak"))
        residual = peak if residual_is_peak else _pyramid_set(residual_st, tr, ("mc", "res"))
    else:  # Hoek-Brown family: tensile strength inherent to the criterion
        peak = _pyramid_set(peak_st, None, ("hb", "peak"))
        residual = peak if residual_is_peak else _pyramid_set(residual_st, None, ("hb", "res"))
    return PerfectBrittleModel(elastic, peak, residual)


def strengths(criterion: str, params: Mapping) -> tuple[Strength, Strength]:
    """(peak, residual) pyramid strength of MC / HB / GHB in kPa."""

    p = params
    residual_is_peak = bool(p.get("set_residual_to_peak", True))
    if criterion == "mohr_coulomb":
        psi = float(p.get("dilation", 0.0))
        peak = Strength.mohr_coulomb(float(p["peak_cohesion"]), float(p["peak_friction"]), psi)
        if residual_is_peak:
            return peak, peak
        return peak, Strength.mohr_coulomb(float(p["residual_cohesion"]), float(p["residual_friction"]), psi)
    if criterion == "hoek_brown":
        sigci, mg = float(p["compressive_strength"]), float(p.get("dilation_parameter", 0.0))
        peak = Strength.hoek_brown(sigci, float(p["mb"]), float(p["s"]), 0.5, mg)
        if residual_is_peak:
            return peak, peak
        return peak, Strength.hoek_brown(sigci, float(p["residual_mb"]), float(p["residual_s"]), 0.5, mg)
    if criterion == "generalized_hoek_brown":
        sigci = float(p["sigci"])

        def ghb(gsi, mi, d) -> Strength:
            try:
                inp = HbInput(sigci=sigci / 1000.0, gsi=float(gsi), mi=float(mi), disturbance=float(d))
            except ValueError as exc:
                raise SimulationError(str(exc)) from None
            mb, s, a = hoek_brown_constants(inp)
            return Strength.hoek_brown(sigci, mb, s, a)

        peak = ghb(p["gsi"], p["mi"], p["d"])
        if residual_is_peak:
            return peak, peak
        return peak, ghb(p["gsi_residual"], p["mi_residual"], p["d_residual"])
    raise SimulationError(f"test simulation of the {criterion!r} model is not available")


# ------------------------------------------------------------------ driver


@dataclass
class SimulationResult:
    """Per-step effective stresses (kPa), engineering strains and pore pressure (kPa).

    strain and stress are (n, 6) in the order (a, x, y, a-x, x-y, a-y).
    """

    test: TestSimulation
    strain: np.ndarray
    stress: np.ndarray
    pore_pressure: np.ndarray
    yielded: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))

    @property
    def axial_strain(self) -> np.ndarray:
        return self.strain[:, 0]

    @property
    def axial_stress(self) -> np.ndarray:
        return self.stress[:, 0]

    @property
    def shear_strain(self) -> np.ndarray:
        """Engineering shear strain gamma_ax (simple shear)."""

        return self.strain[:, 3]

    @property
    def shear_stress(self) -> np.ndarray:
        return self.stress[:, 3]

    @property
    def p(self) -> np.ndarray:
        return self.stress[:, :3].mean(axis=1)

    @property
    def q(self) -> np.ndarray:
        s = self.stress
        normal = 0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2)
        return np.sqrt(normal + 3.0 * (s[:, 3] ** 2 + s[:, 4] ** 2 + s[:, 5] ** 2))

    @property
    def eps_v(self) -> np.ndarray:
        return self.strain[:, :3].sum(axis=1)

    @property
    def eps_q(self) -> np.ndarray:
        """Deviatoric strain sqrt(2/3 e:e) (= 2/3 (ea - er) in triaxial), signed with the loading."""

        e = self.strain[:, :3] - self.eps_v[:, None] / 3.0
        ee = (e**2).sum(axis=1) + 0.5 * (self.strain[:, 3:] ** 2).sum(axis=1)
        magnitude = np.sqrt(2.0 / 3.0 * ee)
        if self.test.test_type == "simple_shear":
            driver = self.strain[:, 3]
        else:
            driver = self.strain[:, 0] - 0.5 * (self.strain[:, 1] + self.strain[:, 2])
        return np.where(driver < 0.0, -1.0, 1.0) * magnitude

    def _principal(self) -> np.ndarray:
        return np.array([np.linalg.eigvalsh(to_matrix(row, False)) for row in self.stress])

    @property
    def sigma1(self) -> np.ndarray:
        return self._principal()[:, -1]

    @property
    def sigma3(self) -> np.ndarray:
        return self._principal()[:, 0]

    @property
    def peak_q(self) -> float:
        return float(self.q.max())


@dataclass(frozen=True)
class _Controls:
    base: np.ndarray  # engineering strain increment per unit driver increment
    mode: np.ndarray | None  # free strain direction (None: all strains imposed)
    index: int  # stress component held at `target` by the mode
    target: float
    pore_index: int  # undrained: u = sc - stress[pore_index]


def _controls(test: TestSimulation) -> _Controls:
    S0 = to_voigt(test.initial_stress(), False)
    e = np.eye(6)
    undrained = test.seepage == "Undrained"
    if test.test_type == "general":
        # proportional strain path; undrained keeps the volume (normal part made deviatoric)
        direction = np.array(test.strain_ratio, dtype=float)
        direction = direction / np.max(np.abs(direction))
        if undrained:
            direction[:3] -= direction[:3].mean()
            if np.max(np.abs(direction)) == 0.0:
                raise SimulationError("General Test: an undrained test needs a deviatoric strain direction")
        return _Controls(direction, None, -1, float(S0[:3].mean()), -1)
    if test.test_type == "simple_shear":
        if undrained:
            return _Controls(e[3], None, 0, S0[0], 0)
        return _Controls(e[3], e[0], 0, S0[0], 0)
    sc = S0[1]
    if test.test_type == "biaxial":
        if undrained:
            return _Controls(e[0] - e[1], None, 1, sc, 1)
        return _Controls(e[0], e[1], 1, sc, 1)
    if undrained:
        return _Controls(e[0] - 0.5 * (e[1] + e[2]), None, 1, sc, 1)
    return _Controls(e[0], e[1] + e[2], 1, sc, 1)


def _solve_step(model, S, state, d, ctl: _Controls):
    """One increment; returns (dE, S, state, yielded) or None."""

    base = ctl.base * d
    if ctl.mode is None:
        dE = to_matrix(base, True)
        try:
            new, st, y = model.update(S, state, dE)
        except _StepFailure:
            return None
        return dE, new, st, y

    def run(x):
        dE = to_matrix(base + x * ctl.mode, True)
        new, st, y = model.update(S, state, dE)
        return dE, new, st, y

    scale = max(1.0, abs(ctl.target), float(np.max(np.abs(S))))
    tol = 1e-9 * scale
    def residual(x):
        out = run(x)
        return out, to_voigt(out[1], False)[ctl.index] - ctl.target

    x = 0.0  # no free strain to start; damped Newton with a finite-difference slope
    try:
        out, g = residual(x)
        for _ in range(60):
            if abs(g) < tol:
                return out
            h = 1e-7 * max(1e-6, abs(x), abs(d))
            _, g_h = residual(x + h)
            slope = (g_h - g) / h
            if not math.isfinite(slope) or abs(slope) < 1e-12 * scale:
                return None
            step = -g / slope
            for _ in range(30):  # backtrack until the residual decreases
                trial_out, trial_g = residual(x + step)
                if abs(trial_g) < abs(g):
                    break
                step *= 0.5
            else:
                return None
            x, out, g = x + step, trial_out, trial_g
    except (_StepFailure, np.linalg.LinAlgError):
        return None
    return None


def simulate(criterion: str, params: Mapping, stiffness: Mapping | None, test: TestSimulation) -> SimulationResult:
    """Integrate a test simulation; raises SimulationError when not possible."""

    if not test.simulated:
        raise SimulationError(f"{TEST_TYPES[test.test_type]}: the reference program does not document its inputs; not simulated")
    test.validate()
    model = build_model(criterion, params, stiffness)
    ctl = _controls(test)

    S = test.initial_stress()  # consolidated start; uniaxial starts unloaded
    state = model.initial_state(S)
    E = np.zeros((3, 3))
    strains, stresses, flags = [to_voigt(E, True)], [to_voigt(S, False)], [False]
    states = [dict(state)]
    previous = 0.0
    yielded = False
    for target in test.history():
        d_total = float(target) - previous
        previous = float(target)
        pending = [d_total]
        while pending:
            d = pending.pop(0)
            solved = _solve_step(model, S, state, d, ctl)
            if solved is None and getattr(model, "brittle", False) and not state.get("failed"):
                # the peak -> residual drop makes the mixed control discontinuous:
                # solve the step on the residual branch, valid if the peak is exceeded
                forced = _solve_step(model, S, {"failed": True}, d, ctl)
                if forced is not None and model.peak_violated(S, forced[0]):
                    solved = (forced[0], forced[1], {"failed": True}, True)
            if solved is None:
                if abs(d) < abs(d_total) / 1024.0:
                    raise SimulationError("the simulation did not converge (step subdivision exhausted)")
                pending[:0] = [d / 2.0, d / 2.0]
                continue
            dE, S, state, yielded = solved
            E = E + dE
        strains.append(to_voigt(E, True))
        stresses.append(to_voigt(S, False))
        flags.append(bool(yielded))
        states.append(dict(state))
    stress = np.array(stresses)
    if test.seepage == "Undrained":
        if ctl.pore_index < 0:  # general: total mean stress kept (OGR assumption)
            u = ctl.target - stress[:, :3].mean(axis=1)
        else:
            u = ctl.target - stress[:, ctl.pore_index]
    else:
        u = np.zeros(len(stress))
    result = SimulationResult(test, np.array(strains), stress, u, np.array(flags))
    result.states = states
    result.model = model
    return result


def simulate_material(material, test: TestSimulation) -> SimulationResult:
    """Simulate a test on a project material (core.project.Material)."""

    return simulate(material.criterion, material.parameters, getattr(material, "stiffness", None), test)


def failure_deviator(criterion: str, params: Mapping, test: TestSimulation) -> float:
    """Analytic failure deviator q_f of a drained axisymmetric compression test (kPa).

    MC / HB / GHB peak strength with sigma3 = confining (triaxial) or 0
    (uniaxial): q_f = S(sigma3) - sigma3. Used to check the integration.
    """

    peak, _ = strengths(criterion, params)
    sigma3 = test.confining if test.confined else 0.0
    return peak.deviator_at(sigma3)


# ------------------------------------------------------- yield surface in q-p (animation)


def _pyramid_pq(surfaces, p_max: float, n: int = 80) -> tuple[np.ndarray, np.ndarray]:
    """Triaxial-compression meridian (sigma2 = sigma3) of a pyramid / cone set, kPa."""

    faces = [s for s in surfaces if isinstance(s, PairFace)]
    cones = [s for s in surfaces if isinstance(s, DruckerPragerCone)]
    if cones:
        cone = cones[0]
        lo = cone.apex if math.isfinite(cone.apex) else 0.0
        p = np.linspace(lo, p_max, n)
        return p, np.maximum(math.sqrt(3.0) * (cone.k + cone.q_phi * p), 0.0)
    if not faces:
        return np.zeros(0), np.zeros(0)
    st = faces[0].st
    lo = st.apex if math.isfinite(st.apex) else 0.0
    s3 = np.linspace(lo, p_max, n)
    s1 = np.array([st.S(float(x)) for x in s3])
    return (s1 + 2.0 * s3) / 3.0, s1 - s3


def yield_surface_pq(result: "SimulationResult", step: int) -> tuple[np.ndarray, np.ndarray]:
    """Current yield surface of a simulated test in the q-p plane (kPa), at a step.

    Triaxial-compression meridian (Lode angle of TC) for MC / HB / DP and the
    Softening-Hardening cone; the caps of Cam-Clay, MCC, NorSand and SH with
    their hardening state at that step. Empty arrays when not available.
    """

    model = getattr(result, "model", None)
    states = getattr(result, "states", None)
    if model is None or not states:
        return np.zeros(0), np.zeros(0)
    step = max(0, min(step, len(states) - 1))
    state = states[step]
    p_max = max(float(np.max(result.p)) * 1.3, 1.0)
    if isinstance(model, PerfectBrittleModel):
        current = model.residual if state.get("failed") else model.peak
        return _pyramid_pq(current.surfaces, p_max)
    if isinstance(model, SofteningHardeningModel):
        ps = model._set(state["kappa"], None, state.get("pc"))
        p, q = _pyramid_pq(ps.surfaces, p_max)
        caps = [s for s in ps.surfaces if isinstance(s, (VerticalCap, EllipticalCap))]
        if caps:
            cap = caps[0]
            if isinstance(cap, VerticalCap):
                keep = p <= cap.pc
                q_cap = float(np.interp(cap.pc, p, q))
                p = np.concatenate([p[keep], [cap.pc, cap.pc]])
                q = np.concatenate([q[keep], [q_cap, 0.0]])
            else:
                pc_p = np.linspace(cap.top, cap.pc, 60)
                q_cap = cap.M * np.sqrt(np.maximum(-(pc_p + cap.a) * (pc_p - cap.pc), 0.0))
                keep = p <= cap.top
                p = np.concatenate([p[keep], pc_p])
                q = np.concatenate([q[keep], q_cap])
        return p, q
    if isinstance(model, CamClayModel):
        pc = state["pc"]
        p = np.linspace(1e-6 * pc, pc, 120)
        if model.modified:
            q = model.M * np.sqrt(np.maximum(p * (pc - p), 0.0))
        else:
            q = np.maximum(-model.M * p * np.log(p / pc), 0.0)
        return p, q
    if isinstance(model, NorSandModel):
        e, p_i = state["e"], state["p_i"]
        m_i = model.m_itc(e, p_i)
        top = p_i * (math.e if model.a == 0.0 else (1.0 / (1.0 - model.Nc)) ** (1.0 / model.a))
        p = np.linspace(1e-6 * p_i, top, 120)
        q = np.array([max(x * model.eta_surface(m_i, x / p_i), 0.0) for x in p])
        return p, q
    return np.zeros(0), np.zeros(0)
