"""Calibration of a strength model against failure states (spec 014).

The RSData Calibration dialog (capture 33; options verified in RSData
1.009, Referencias/Ejemplos/RSData_analisis/07_estados_y_rutas_verificado.md
section 4) on top of the fitting of spec 006:

- several failure states at once (their non-excluded points), triaxial
  and general states as (sigma3, sigma1), direct shear as (sigma_n, tau);
- Strength type: Mohr Coulomb, Generalized Hoek Brown, Power Curve,
  Barton Bandis; Failure Data Type: Lab Data or Rock Mass Data (GHB only,
  sigci and D fixed, as RocData's "Use Rock Mass Data");
- Algorithm: Linear Regression (closed forms of spec 006: MC and intact
  HB), Levenberg-Marquardt, Simplex (Nelder-Mead, RocData); Error
  Summation: Vertical (residuals in sigma1 or tau, as the RocData manual);
  Error Type: Absolute or Relative (residual / observed value);
- the result is a NEW material; the source material is not changed.

Physical bounds (c >= 0, 0 < phi < 90, positive strengths, 1 <= GSI <= 100,
0 <= JRC <= 20): when an unbounded Levenberg-Marquardt solution violates
them, the fit is redone with a bounded trust-region solver and the result
says so. RSData behaves similarly (it returned c ~ 0 where the unbounded
fit gives c < 0) but its exact value (phi = 40.5662 deg in the verification
case) is not reproducible; the bounded optimum here is phi = 40.09 deg.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable

import numpy as np
from scipy.optimize import least_squares, minimize

from . import fitting
from .hoek_brown import HbInput, hoek_brown_constants
from .states import FailureState
from .units import power_curve_a_to_kpa

STRENGTH_TYPES: dict[str, str] = {
    "mohr_coulomb": "Mohr Coulomb",
    "generalized_hoek_brown": "Generalized Hoek Brown",
    "power_curve": "Power Curve",
    "barton_bandis": "Barton Bandis",
}
ALGORITHMS: dict[str, str] = {
    fitting.LINEAR: "Linear Regression",
    fitting.LEVENBERG_MARQUARDT: "Levenberg-Marquardt",
    fitting.SIMPLEX: "Simplex",
}
ERROR_TYPES = ("Absolute", "Relative")
DATA_TYPES = ("Lab Data", "Rock Mass Data")


@dataclass
class CalibrationSettings:
    strength_type: str = "generalized_hoek_brown"
    algorithm: str = fitting.LEVENBERG_MARQUARDT
    error_type: str = "Absolute"
    data_type: str = "Lab Data"
    sigci_kpa: float = 100000.0  # rock mass data (GHB)
    disturbance: float = 0.0  # rock mass data (GHB)
    phi_b_deg: float = 30.0  # Barton-Bandis


@dataclass
class CalibrationResult:
    criterion: str  # registry criterion of the new material
    parameters: dict  # registry units (kPa, deg)
    fitted: dict[str, float]  # fitted values as reported (MPa / deg)
    data_kind: str
    n_points: int
    ssr: float  # sum of squared (absolute or relative) vertical residuals
    rms: float  # sqrt(ssr / n)
    method_note: str = ""
    residuals: np.ndarray = field(default_factory=lambda: np.zeros(0))


# ------------------------------------------------------------- data


def _state_points(state: FailureState) -> tuple[str, np.ndarray, np.ndarray]:
    """(data kind, x, y) in kPa of the non-excluded points of one state."""

    if state.test_type == "direct_shear":
        return (fitting.DIRECT, *state.shear_points())
    return (fitting.TRIAXIAL, *state.principal_points())


def has_points(state: FailureState) -> bool:
    """True if the state has a non-excluded point to calibrate against."""

    return len(_state_points(state)[1]) > 0


def collect_points(states: Iterable[FailureState]) -> tuple[str, np.ndarray, np.ndarray]:
    """(data kind, x, y) in MPa from the non-excluded points of the states."""

    kinds, xs, ys = set(), [], []
    for state in states:
        kind, x, y = _state_points(state)
        if len(x):
            kinds.add(kind)
            xs.append(x / 1000.0)
            ys.append(y / 1000.0)
    if not kinds:
        raise ValueError("the selected failure states have no (non-excluded) points")
    if len(kinds) > 1:
        raise ValueError("cannot calibrate triaxial and direct shear states together")
    return kinds.pop(), np.concatenate(xs), np.concatenate(ys)


# ------------------------------------------------------- generic solver


def _solve(
    model: Callable[[np.ndarray, np.ndarray], np.ndarray],
    p0: list[float],
    bounds: tuple[list[float], list[float]],
    x: np.ndarray,
    y: np.ndarray,
    algorithm: str,
    relative: bool,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Best parameters, weighted residuals and a note on the solver used."""

    if relative and np.any(y == 0.0):
        raise ValueError("relative error needs non-zero observed values")
    weight = 1.0 / np.abs(y) if relative else np.ones_like(y)
    residual = lambda p: (model(x, p) - y) * weight
    lo, hi = (np.asarray(b, dtype=float) for b in bounds)

    def inside(p):
        return bool(np.all(p >= lo) and np.all(p <= hi))

    if algorithm == fitting.SIMPLEX:
        sol = minimize(
            lambda p: float(residual(p) @ residual(p)), np.clip(p0, lo, hi), method="Nelder-Mead",
            bounds=list(zip(lo, hi)), options={"maxiter": 40000, "xatol": 1e-12, "fatol": 1e-14},
        )
        return sol.x, residual(sol.x), "Simplex (Nelder-Mead)"
    if algorithm != fitting.LEVENBERG_MARQUARDT:
        raise ValueError(f"unknown algorithm {algorithm!r}")
    sol = least_squares(residual, p0, method="lm")
    if inside(sol.x):
        return sol.x, sol.fun, "Levenberg-Marquardt"
    sol = least_squares(residual, np.clip(p0, lo + 1e-9, hi - 1e-9), method="trf", bounds=(lo, hi), xtol=1e-14, ftol=1e-14, gtol=1e-14)
    return sol.x, sol.fun, "Levenberg-Marquardt hit a physical bound: bounded trust-region solution"


def _mc_principal(x: np.ndarray, p: np.ndarray) -> np.ndarray:
    phi = math.radians(p[1])
    return 2.0 * p[0] * math.cos(phi) / (1.0 - math.sin(phi)) + (1.0 + math.sin(phi)) / (1.0 - math.sin(phi)) * x


def _result(criterion, parameters, fitted, kind, residual, note) -> CalibrationResult:
    ssr = float(residual @ residual)
    return CalibrationResult(criterion, parameters, fitted, kind, len(residual), ssr, math.sqrt(ssr / len(residual)), note, residual)


# ------------------------------------------------------------- models


def _mohr_coulomb(kind, x, y, s: CalibrationSettings) -> CalibrationResult:
    relative = s.error_type == "Relative"
    if s.algorithm == fitting.LINEAR:
        weight = 1.0 / np.abs(y) if relative else None
        if relative and np.any(y == 0.0):
            raise ValueError("relative error needs non-zero observed values")
        slope, intercept = np.polyfit(x, y, 1, w=weight)
        if kind == fitting.TRIAXIAL:
            if intercept <= 0 or slope <= 1.0:
                raise ValueError("data does not define a valid Mohr-Coulomb envelope")
            phi = math.degrees(math.asin((slope - 1.0) / (slope + 1.0)))
            c = intercept / (2.0 * math.sqrt(slope))
        else:
            if slope <= 0.0:
                raise ValueError("data does not define a valid Mohr-Coulomb envelope")
            phi, c = math.degrees(math.atan(slope)), intercept
        p = np.array([c, phi])
        model = _mc_principal if kind == fitting.TRIAXIAL else (lambda xx, pp: pp[0] + xx * math.tan(math.radians(pp[1])))
        residual = (model(x, p) - y) * (weight if weight is not None else 1.0)
        note = "Linear Regression"
    else:
        model = _mc_principal if kind == fitting.TRIAXIAL else (lambda xx, pp: pp[0] + xx * np.tan(np.radians(pp[1])))
        p, residual, note = _solve(model, [max(float(np.min(y)) * 0.1, 1e-3), 30.0], ([0.0, 1e-6], [np.inf, 89.9]), x, y, s.algorithm, relative)
    c, phi = float(p[0]), float(p[1])
    params = {"peak_cohesion": c * 1000.0, "peak_friction": phi, "residual_cohesion": c * 1000.0, "residual_friction": phi}
    return _result("mohr_coulomb", params, {"cohesion_mpa": c, "friction_deg": phi}, kind, residual, note)


def _hoek_brown_lab(x, y, s: CalibrationSettings) -> CalibrationResult:
    """Lab data: intact rock (GSI = 100, D = 0 -> mb = mi, s = 1, a = 0.5)."""

    relative = s.error_type == "Relative"
    model = lambda xx, p: xx + p[0] * np.sqrt(np.maximum(p[1] * xx / p[0] + 1.0, 0.0))
    if s.algorithm == fitting.LINEAR:
        if relative:
            raise ValueError("Linear Regression fits Hoek-Brown in a transformed space; use Levenberg-Marquardt or Simplex for relative error")
        res = fitting.fit_hb_intact_triaxial(x, y, fitting.LINEAR)
        p = np.array([res.parameters["sigci_mpa"], res.parameters["mi"]])
        residual, note = model(x, p) - y, "Linear Regression (Hoek, PRE ch. 11)"
    else:
        try:
            start = fitting.fit_hb_intact_triaxial(x, y, fitting.LINEAR)
            p0 = [start.parameters["sigci_mpa"], start.parameters["mi"]]
        except ValueError:
            p0 = [max(float(np.max(y - x)), 1.0), 10.0]
        p0 = [max(p0[0], 1e-3), max(p0[1], 1e-3)]
        p, residual, note = _solve(model, p0, ([1e-6, 1e-6], [np.inf, np.inf]), x, y, s.algorithm, relative)
    sigci, mi = float(p[0]), float(p[1])
    params = {"sigci": sigci * 1000.0, "mi": mi, "gsi": 100.0, "d": 0.0, "mi_residual": mi, "gsi_residual": 100.0, "d_residual": 0.0}
    return _result("generalized_hoek_brown", params, {"sigci_mpa": sigci, "mi": mi}, fitting.TRIAXIAL, residual, note)


def _hoek_brown_mass(x, y, s: CalibrationSettings) -> CalibrationResult:
    """Rock mass data: GSI and mi with sigci and D fixed (GHB 2002 model)."""

    if s.algorithm == fitting.LINEAR:
        raise ValueError("Linear Regression is not available for rock mass data (RocData)")
    sigci = s.sigci_kpa / 1000.0
    if sigci <= 0:
        raise ValueError("sigci must be positive")
    d = s.disturbance

    def model(xx, p):
        mb, s_, a = hoek_brown_constants(HbInput(sigci=sigci, gsi=float(np.clip(p[0], 1.0, 100.0)), mi=max(float(p[1]), 1e-6), disturbance=d))
        return xx + sigci * np.maximum(mb * xx / sigci + s_, 0.0) ** a

    p, residual, note = _solve(model, [50.0, 10.0], ([1.0, 1e-3], [100.0, 100.0]), x, y, s.algorithm, s.error_type == "Relative")
    gsi, mi = float(p[0]), float(p[1])
    params = {"sigci": s.sigci_kpa, "gsi": gsi, "mi": mi, "d": d, "gsi_residual": gsi, "mi_residual": mi, "d_residual": d}
    return _result("generalized_hoek_brown", params, {"gsi": gsi, "mi": mi, "sigci_mpa": sigci, "disturbance": d}, fitting.TRIAXIAL, residual, note)


def _power_curve(x, y, s: CalibrationSettings) -> CalibrationResult:
    if s.algorithm == fitting.LINEAR:
        raise ValueError("Linear Regression is only available for Mohr-Coulomb and intact Hoek-Brown (RocData)")
    model = lambda xx, p: p[0] * np.maximum(xx + p[2], 0.0) ** p[1]
    p, residual, note = _solve(model, [0.8, 0.8, 0.01], ([1e-9, 1e-6, 0.0], [np.inf, 10.0, np.inf]), x, y, s.algorithm, s.error_type == "Relative")
    a, b, d = (float(v) for v in p)
    a_kpa = power_curve_a_to_kpa(a, b)  # spec 026: the form holds a with stresses in kPa
    params = {"a": a_kpa, "b": b, "d": d * 1000.0, "residual_a": a_kpa, "residual_b": b, "residual_d": d * 1000.0}
    return _result("power_curve", params, {"a": a, "b": b, "d_mpa": d}, fitting.DIRECT, residual, note)


def _barton_bandis(x, y, s: CalibrationSettings) -> CalibrationResult:
    if s.algorithm == fitting.LINEAR:
        raise ValueError("Linear Regression is only available for Mohr-Coulomb and intact Hoek-Brown (RocData)")
    if np.any(x <= 0):
        raise ValueError("Barton-Bandis requires positive normal stress")
    phi_b = math.radians(s.phi_b_deg)
    model = lambda xx, p: xx * np.tan(phi_b + np.radians(p[0] * np.log10(np.maximum(p[1], 1e-12) / xx)))
    p0 = [10.0, max(float(np.max(x)) * 10.0, 1.0)]
    p, residual, note = _solve(model, p0, ([0.0, float(np.max(x))], [20.0, np.inf]), x, y, s.algorithm, s.error_type == "Relative")
    jrc, jcs = float(p[0]), float(p[1])
    params = {"phi_r": s.phi_b_deg, "jrc": jrc, "jcs": jcs * 1000.0}
    return _result("barton_bandis", params, {"jrc": jrc, "jcs_mpa": jcs, "phi_b_deg": s.phi_b_deg}, fitting.DIRECT, residual, note)


COMPATIBLE = {
    "mohr_coulomb": (fitting.TRIAXIAL, fitting.DIRECT),
    "generalized_hoek_brown": (fitting.TRIAXIAL,),
    "power_curve": (fitting.DIRECT,),
    "barton_bandis": (fitting.DIRECT,),
}


def calibrate(states: Iterable[FailureState], settings: CalibrationSettings) -> CalibrationResult:
    kind, x, y = collect_points(states)
    st = settings.strength_type
    if kind not in COMPATIBLE.get(st, ()):
        raise ValueError(f"{STRENGTH_TYPES.get(st, st)} cannot be calibrated against {'direct shear' if kind == fitting.DIRECT else 'triaxial'} data")
    if kind == fitting.TRIAXIAL and np.any(x > y):
        raise ValueError("triaxial data with sigma3 > sigma1 is not valid")
    minimum = {"mohr_coulomb": 2, "generalized_hoek_brown": 2, "power_curve": 3, "barton_bandis": 2}[st]
    if len(x) < minimum:
        raise ValueError(f"at least {minimum} data points are required")
    if st == "mohr_coulomb":
        return _mohr_coulomb(kind, x, y, settings)
    if st == "generalized_hoek_brown":
        if settings.data_type == "Rock Mass Data":
            return _hoek_brown_mass(x, y, settings)
        return _hoek_brown_lab(x, y, settings)
    if st == "power_curve":
        return _power_curve(x, y, settings)
    return _barton_bandis(x, y, settings)
