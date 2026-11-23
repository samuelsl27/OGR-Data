"""Test simulations (spec 013, phase 13a).

RSData's Tests module (Define Test Simulations, capture 20): a simulated
laboratory test on a material — Test Type, Seepage Condition (Drained /
Undrained), Loading Direction (Compression / Tension), Maximum Strain,
Number of Steps and Cyclic Loading Cycles — integrated step by step with
the material's constitutive model. Results feed the Stress Path Graphs.

Phase 13a: linear isotropic elasticity (RSData Stiffness tab: Poisson's
Ratio 0.3, Young's Modulus 20000 kPa) with perfectly plastic Mohr-Coulomb,
Hoek-Brown and Generalized Hoek-Brown strength. When "Set Residual to
Peak" is off the material is elastic-brittle-plastic: the first plastic
step drops the stress onto the residual surface (RS2 convention).

Formulation (compression positive, fixed principal axes 1 = axial,
2 and 3 = lateral; stresses in kPa, effective):

- Yield surfaces f_ij = sigma_i - S(sigma_j) for the six ordered pairs
  i != j (only the one with i = major, j = minor can be active away from
  edges; the others make the edges and the apex of the pyramid exact).
  Mohr-Coulomb: S(x) = N_phi x + 2 c sqrt(N_phi), N = (1+sin)/(1-sin).
  Hoek-Brown: S(x) = x + sigci (mb x / sigci + s)^a.
- Plastic potentials g_ij = sigma_i - S_g(sigma_j): Mohr-Coulomb with the
  dilation angle psi (S_g' = N_psi); Hoek-Brown with the dilation
  parameter as mb of the potential (0 = no plastic volume change, mb =
  associated, RS2 convention); Generalized Hoek-Brown has no dilation
  field in the RSData dialog and flows without volume change.
- Backward-Euler return mapping with an active set of surfaces (Newton on
  sigma and the plastic multipliers; exact in one iteration for
  Mohr-Coulomb), with return to the apex when more than two surfaces are
  active.
- Mixed control per test: axial strain increments are imposed; the
  lateral conditions are solved with Newton on symmetric lateral modes
  (the axisymmetric split is indeterminate on an edge of the pyramid).

Tests:
- Uniaxial: lateral stresses zero.
- Triaxial: lateral effective stresses = confining stress (drained); or
  no volume change, eps_r = -eps_a / 2, pore pressure u = sigma_c - sigma'_r
  with the cell pressure constant (undrained; initial u = 0).
- Biaxial (plane strain): eps_2 = 0; sigma'_3 = confining (drained) or
  eps_3 = -eps_1 and u = sigma_c - sigma'_3 (undrained).
- Simple Shear and General: phase 13b (rotating principal axes / general
  loading), defined and saved but not simulated yet.

Loading Direction Tension imposes negative (extension) axial strains.
Cyclic loading (13a, basic): the axial strain goes 0 -> max -> 0 per
cycle, Number of Steps per half cycle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

from .hoek_brown import HbInput, hoek_brown_constants

# Define Test Simulations, Test Type combo of RSData (capture 20; help).
TEST_TYPES: dict[str, str] = {
    "uniaxial": "Uniaxial Test",
    "triaxial": "Triaxial Test",
    "biaxial": "Biaxial Test",
    "simple_shear": "Simple Shear Test",
    "general": "General Test",
}
SIMULATED_TYPES = ("uniaxial", "triaxial", "biaxial")
SEEPAGE = ("Drained", "Undrained")
LOADING = ("Compression", "Tension")
SIMULATED_CRITERIA = ("mohr_coulomb", "hoek_brown", "generalized_hoek_brown")

DEFAULT_COLOR = "#800000"  # RSData default color of a new object

# RSData Stiffness tab, Linear Isotropic (capture 12)
STIFFNESS_TYPES = ("Linear Isotropic",)
DEFAULT_STIFFNESS = {"type": "Linear Isotropic", "poisson": 0.3, "young": 20000.0}  # young in kPa


class SimulationError(ValueError):
    """The test cannot be simulated (model, inputs or convergence)."""


def stiffness_from(data: Mapping | None) -> dict:
    data = dict(data or {})
    out = dict(DEFAULT_STIFFNESS)
    if data.get("type") in STIFFNESS_TYPES:
        out["type"] = data["type"]
    for key in ("poisson", "young"):
        if key in data:
            out[key] = float(data[key])
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
    # OGR Data: confining (cell) stress of triaxial / biaxial tests, kPa.
    # RSData's field for it is not documented; the default matches the
    # Initial Effective Lateral Stress of its stress paths (100 kPa).
    confining: float = 100.0
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

    @property
    def simulated(self) -> bool:
        return self.test_type in SIMULATED_TYPES

    @property
    def confined(self) -> bool:
        return self.test_type in ("triaxial", "biaxial")

    def validate(self) -> None:
        if not self.max_strain > 0.0:
            raise SimulationError("Maximum Strain must be positive")
        if self.max_strain > 1.0:
            raise SimulationError("Maximum Strain must not exceed 1")
        if self.steps > 100000:
            raise SimulationError("too many steps (max 100000)")

    def axial_history(self) -> np.ndarray:
        """Imposed axial strain at the end of each step (start 0 excluded)."""

        sign = 1.0 if self.loading == "Compression" else -1.0
        up = np.linspace(0.0, sign * self.max_strain, self.steps + 1)[1:]
        if not self.cyclic:
            return up
        down = up[::-1][1:]
        cycle = np.concatenate([up, down, [0.0]])
        return np.tile(cycle, self.cycles)

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
            visible=bool(data.get("visible", True)),
        )


# ------------------------------------------------------------- strength

_TINY = 1e-12


@dataclass(frozen=True)
class Strength:
    """Yield function S(x) and potential S_g(x) of a criterion (kPa)."""

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
    def mohr_coulomb(cls, c: float, phi_deg: float, psi_deg: float = 0.0) -> "Strength":
        if not 0.0 <= phi_deg < 90.0:
            raise SimulationError("friction angle must be in [0, 90) degrees")
        sin = math.sin(math.radians(phi_deg))
        n_phi = (1.0 + sin) / (1.0 - sin)
        sin_psi = math.sin(math.radians(max(0.0, psi_deg)))
        return cls("mc", n_phi=n_phi, sc=2.0 * c * math.sqrt(n_phi), n_psi=(1.0 + sin_psi) / (1.0 - sin_psi))

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


def strengths(criterion: str, params: Mapping) -> tuple[Strength, Strength]:
    """(peak, residual) strength of a material in kPa."""

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
    raise SimulationError(
        f"test simulation of the {criterion!r} model is not available yet (spec 013b); "
        f"13a simulates Mohr-Coulomb, Hoek-Brown and Generalized Hoek-Brown"
    )


def elastic_matrix(young: float, poisson: float) -> np.ndarray:
    """Isotropic elasticity in principal components (kPa)."""

    if young <= 0.0:
        raise SimulationError("Young's modulus must be positive")
    if not -1.0 < poisson < 0.5:
        raise SimulationError("Poisson's ratio must be in (-1, 0.5)")
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    mu = young / (2.0 * (1.0 + poisson))
    return np.full((3, 3), lam) + np.eye(3) * 2.0 * mu


# --------------------------------------------------------- return mapping

PAIRS = tuple((i, j) for i in range(3) for j in range(3) if i != j)


def _yield(model: Strength, sig: np.ndarray, k: int) -> float:
    i, j = PAIRS[k]
    return sig[i] - model.S(sig[j])


def _normal(model: Strength, sig: np.ndarray, k: int) -> np.ndarray:
    i, j = PAIRS[k]
    n = np.zeros(3)
    n[i] = 1.0
    n[j] = -model.dS(sig[j])
    return n


def _flow(model: Strength, sig: np.ndarray, k: int) -> np.ndarray:
    i, j = PAIRS[k]
    m = np.zeros(3)
    m[i] = 1.0
    m[j] = -model.dSg(sig[j])
    return m


def _solve_active(model: Strength, D: np.ndarray, trial: np.ndarray, active: list[int], tol: float):
    """Newton on (sigma, dlambda) for an active set; None if it does not converge."""

    m = len(active)
    sig = trial.copy()
    dl = np.zeros(m)
    for _ in range(60):
        flows = [_flow(model, sig, k) for k in active]
        r1 = sig - trial + D @ sum((dl[n] * flows[n] for n in range(m)), np.zeros(3))
        r2 = np.array([_yield(model, sig, k) for k in active])
        if np.max(np.abs(r1)) < tol and np.max(np.abs(r2)) < tol:
            return sig, dl
        jac = np.zeros((3 + m, 3 + m))
        jac[:3, :3] = np.eye(3)
        for n, k in enumerate(active):
            j = PAIRS[k][1]
            dm = np.zeros((3, 3))
            dm[j, j] = -model.d2Sg(sig[j])
            jac[:3, :3] += dl[n] * D @ dm
            jac[:3, 3 + n] = D @ flows[n]
            jac[3 + n, :3] = _normal(model, sig, k)
        try:
            delta = np.linalg.solve(jac, -np.concatenate([r1, r2]))
        except np.linalg.LinAlgError:
            return None
        if not np.all(np.isfinite(delta)):
            return None
        sig = sig + delta[:3]
        dl = dl + delta[3:]
    return None


def return_map(model: Strength, D: np.ndarray, trial: np.ndarray) -> tuple[np.ndarray, bool]:
    """Stress on or inside the yield pyramid; (sigma, yielded)."""

    scale = max(1.0, float(np.max(np.abs(trial))), model.sc if model.kind == "mc" else model.sigci)
    tol = 1e-10 * scale
    values = [_yield(model, trial, k) for k in range(len(PAIRS))]
    fmax = max(values)
    if fmax <= tol:
        return trial, False
    active = [k for k, v in enumerate(values) if v >= fmax - 1e-9 * scale]
    for _ in range(12):
        if len(active) > 2:
            break
        solved = _solve_active(model, D, trial, active, tol)
        if solved is None:
            break
        sig, dl = solved
        if np.any(dl < -tol / scale):
            active.pop(int(np.argmin(dl)))
            if not active:
                break
            continue
        violated = [(v, k) for k in range(len(PAIRS)) if k not in active and (v := _yield(model, sig, k)) > tol]
        if not violated:
            return sig, True
        active.append(max(violated)[1])
    if math.isinf(model.apex):
        raise SimulationError("stress state beyond a cohesionless, frictionless surface")
    return np.full(3, model.apex), True


# ------------------------------------------------------------------ driver


@dataclass
class SimulationResult:
    """Per-step effective stresses (kPa), strains and pore pressure (kPa)."""

    test: TestSimulation
    strain: np.ndarray  # (n, 3): axial, lateral 2, lateral 3
    stress: np.ndarray  # (n, 3) effective
    pore_pressure: np.ndarray  # (n,)
    yielded: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))

    @property
    def axial_strain(self) -> np.ndarray:
        return self.strain[:, 0]

    @property
    def axial_stress(self) -> np.ndarray:
        return self.stress[:, 0]

    @property
    def p(self) -> np.ndarray:
        return self.stress.mean(axis=1)

    @property
    def q(self) -> np.ndarray:
        s = self.stress
        return np.sqrt(0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2))

    @property
    def eps_v(self) -> np.ndarray:
        return self.strain.sum(axis=1)

    @property
    def eps_q(self) -> np.ndarray:
        """Deviatoric strain sqrt(2/3 e:e), signed as eps_a - mean lateral (= 2/3 (ea - er) triaxial)."""

        e = self.strain - self.eps_v[:, None] / 3.0
        magnitude = np.sqrt(2.0 / 3.0 * (e**2).sum(axis=1))
        sign = np.where(self.strain[:, 0] - 0.5 * (self.strain[:, 1] + self.strain[:, 2]) < 0.0, -1.0, 1.0)
        return sign * magnitude

    @property
    def sigma1(self) -> np.ndarray:
        return self.stress.max(axis=1)

    @property
    def sigma3(self) -> np.ndarray:
        return self.stress.min(axis=1)

    @property
    def peak_q(self) -> float:
        return float(self.q.max())


def _controls(test: TestSimulation):
    """(lateral strain increment per unit axial increment, modes, controlled index, target).

    Lateral increment d_lat (3,) multiplies the axial increment (undrained /
    plane strain); modes are the free lateral strain directions solved so
    that the effective stress of `index` equals `target`.
    """

    sc = test.confining if test.confined else 0.0
    if test.seepage == "Undrained":
        if test.test_type == "biaxial":
            return np.array([1.0, 0.0, -1.0]), [], None, sc
        return np.array([1.0, -0.5, -0.5]), [], None, sc
    if test.test_type == "biaxial":
        return np.array([1.0, 0.0, 0.0]), [np.array([0.0, 0.0, 1.0])], 2, sc
    return np.array([1.0, 0.0, 0.0]), [np.array([0.0, 1.0, 1.0])], 1, sc


class _Integrator:
    def __init__(self, peak: Strength, residual: Strength, D: np.ndarray) -> None:
        self.peak = peak
        self.residual = residual
        self.brittle = residual != peak
        self.D = D

    def update(self, sig: np.ndarray, failed: bool, deps: np.ndarray) -> tuple[np.ndarray, bool, bool]:
        trial = sig + self.D @ deps
        model = self.residual if failed else self.peak
        new, yielded = return_map(model, self.D, trial)
        if yielded and not failed and self.brittle:
            new, _ = return_map(self.residual, self.D, trial)
            return new, True, True
        return new, failed, yielded


def _solve_step(integ: _Integrator, sig, failed, d_axial, unit, modes, index, target):
    """One increment; returns (deps, sigma, failed, yielded) or None."""

    base = unit * d_axial
    if not modes:
        new, nf, y = integ.update(sig, failed, base)
        return base, new, nf, y
    mode = modes[0]
    D = integ.D
    # elastic predictor of the lateral strain
    x = (target - sig[index] - (D @ base)[index]) / (D @ mode)[index]
    scale = max(1.0, abs(target), float(np.max(np.abs(sig))))
    tol = 1e-9 * scale
    for _ in range(40):
        deps = base + x * mode
        new, nf, y = integ.update(sig, failed, deps)
        g = new[index] - target
        if abs(g) < tol:
            return deps, new, nf, y
        h = 1e-7 * max(1e-6, abs(x), abs(d_axial))
        new_h, _, _ = integ.update(sig, failed, base + (x + h) * mode)
        slope = (new_h[index] - new[index]) / h
        if not math.isfinite(slope) or abs(slope) < 1e-12 * scale:
            return None
        x -= g / slope
    return None


def simulate(criterion: str, params: Mapping, stiffness: Mapping | None, test: TestSimulation) -> SimulationResult:
    """Integrate a test simulation; raises SimulationError when not possible."""

    if not test.simulated:
        raise SimulationError(f"{TEST_TYPES[test.test_type]} is simulated from spec 013b")
    test.validate()
    stiff = stiffness_from(stiffness)
    D = elastic_matrix(stiff["young"], stiff["poisson"])
    peak, residual = strengths(criterion, params)
    integ = _Integrator(peak, residual, D)
    unit, modes, index, target = _controls(test)
    sc = test.confining if test.confined else 0.0

    sig = np.full(3, sc)  # isotropic (consolidated) start; uniaxial starts unloaded
    if return_map(peak, D, sig)[1]:
        raise SimulationError("the initial (confining) stress state is outside the yield surface")
    eps = np.zeros(3)
    failed = False
    strains, stresses, flags = [eps.copy()], [sig.copy()], [False]
    previous = 0.0
    for target_axial in test.axial_history():
        d_total = float(target_axial) - previous
        previous = float(target_axial)
        pending = [d_total]
        while pending:
            d = pending.pop(0)
            solved = _solve_step(integ, sig, failed, d, unit, modes, index, target)
            if solved is None:
                if abs(d) < abs(d_total) / 64.0:
                    raise SimulationError("the simulation did not converge (step subdivision exhausted)")
                pending[:0] = [d / 2.0, d / 2.0]
                continue
            deps, sig, failed, yielded = solved
            eps = eps + deps
        strains.append(eps.copy())
        stresses.append(sig.copy())
        flags.append(bool(yielded))
    stress = np.array(stresses)
    if test.seepage == "Undrained":
        lateral = 2  # the loaded lateral direction (3)
        u = sc - stress[:, lateral]
    else:
        u = np.zeros(len(stress))
    return SimulationResult(test, np.array(strains), stress, u, np.array(flags))


def simulate_material(material, test: TestSimulation) -> SimulationResult:
    """Simulate a test on a project material (core.project.Material)."""

    return simulate(material.criterion, material.parameters, getattr(material, "stiffness", None), test)


def failure_deviator(criterion: str, params: Mapping, test: TestSimulation) -> float:
    """Analytic failure deviator q_f of a drained axisymmetric compression test (kPa).

    Peak strength with sigma3 = confining (triaxial) or 0 (uniaxial):
    q_f = S(sigma3) - sigma3. Used to check the integration.
    """

    peak, _ = strengths(criterion, params)
    sigma3 = test.confining if test.confined else 0.0
    return peak.deviator_at(sigma3)
