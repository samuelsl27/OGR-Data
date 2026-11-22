"""Fitting strength criteria to laboratory data (spec 006).

Data kinds: "triaxial" (sigma3, sigma1) and "direct" (normal, shear), MPa.
Methods: "linear" (closed form, where documented), "levenberg_marquardt"
and "simplex". Residuals are the sum of squared vertical distances, as in
the RocData manual.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import least_squares, minimize

TRIAXIAL = "triaxial"
DIRECT = "direct"

LINEAR = "linear"
LEVENBERG_MARQUARDT = "levenberg_marquardt"
SIMPLEX = "simplex"


@dataclass(frozen=True)
class FitResult:
    criterion: str
    data_kind: str
    method: str
    parameters: dict[str, float]
    residuals: float
    fixed: dict[str, float] | None = None


def _validate(x: np.ndarray, y: np.ndarray, min_points: int) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("x and y must be one-dimensional arrays of equal length")
    if len(x) < min_points:
        raise ValueError(f"at least {min_points} data points are required")
    return x, y


def _validate_triaxial(sig3: np.ndarray, sig1: np.ndarray) -> None:
    if np.any(sig3 > sig1):
        raise ValueError("triaxial data with sigma3 > sigma1 is not valid")


def _ssr(residual: np.ndarray) -> float:
    return float(residual @ residual)


def _nonlinear(
    model: Callable[[np.ndarray, np.ndarray], np.ndarray],
    p0: list[float],
    x: np.ndarray,
    y: np.ndarray,
    method: str,
    criterion: str,
    data_kind: str,
    names: list[str],
    fixed: dict[str, float] | None = None,
) -> FitResult:
    if method == LEVENBERG_MARQUARDT:
        sol = least_squares(lambda p: model(x, p) - y, p0, method="lm")
        params = sol.x
        ssr = _ssr(sol.fun)
    elif method == SIMPLEX:
        fun = lambda p: _ssr(model(x, p) - y)
        sol = minimize(fun, p0, method="Nelder-Mead", options={"maxiter": 20000, "xatol": 1e-12, "fatol": 1e-12})
        params = sol.x
        ssr = float(sol.fun)
    else:
        raise ValueError(f"method {method!r} has no closed form for {criterion}")
    return FitResult(criterion, data_kind, method, dict(zip(names, params)), ssr, fixed or {})


# ---------------------------------------------------------------- Mohr-Coulomb

def fit_mohr_coulomb_triaxial(sig3, sig1, method: str = LINEAR) -> FitResult:
    """Fit c (MPa) and friction angle (deg) to triaxial data."""

    sig3, sig1 = _validate(sig3, sig1, 2)
    _validate_triaxial(sig3, sig1)
    if method != LINEAR:
        return _nonlinear(
            lambda x, p: 2.0 * p[0] * math.cos(math.radians(p[1])) / (1.0 - math.sin(math.radians(p[1])))
            + (1.0 + math.sin(math.radians(p[1]))) / (1.0 - math.sin(math.radians(p[1]))) * x,
            [1.0, 30.0],
            sig3,
            sig1,
            method,
            "mohr_coulomb",
            TRIAXIAL,
            ["cohesion_mpa", "friction_deg"],
        )
    slope, intercept = np.polyfit(sig3, sig1, 1)
    if intercept <= 0 or slope <= 1.0:
        raise ValueError("data does not define a valid Mohr-Coulomb envelope")
    friction = math.degrees(math.asin((slope - 1.0) / (slope + 1.0)))
    cohesion = intercept / (2.0 * math.sqrt(slope))
    residual = sig1 - (intercept + slope * sig3)
    return FitResult(
        "mohr_coulomb",
        TRIAXIAL,
        LINEAR,
        {"cohesion_mpa": cohesion, "friction_deg": friction},
        _ssr(residual),
    )


def fit_mohr_coulomb_direct(normal, shear, method: str = LINEAR) -> FitResult:
    """Fit c (MPa) and friction angle (deg) to direct shear data."""

    normal, shear = _validate(normal, shear, 2)
    if method != LINEAR:
        return _nonlinear(
            lambda x, p: p[0] + x * math.tan(math.radians(p[1])),
            [0.1, 30.0],
            normal,
            shear,
            method,
            "mohr_coulomb",
            DIRECT,
            ["cohesion_mpa", "friction_deg"],
        )
    slope, intercept = np.polyfit(normal, shear, 1)
    if slope <= 0.0:
        raise ValueError("data does not define a valid Mohr-Coulomb envelope")
    residual = shear - (intercept + slope * normal)
    return FitResult(
        "mohr_coulomb",
        DIRECT,
        LINEAR,
        {"cohesion_mpa": intercept, "friction_deg": math.degrees(math.atan(slope))},
        _ssr(residual),
    )


# ---------------------------------------------------------------- Hoek-Brown

def fit_hb_intact_triaxial(sig3, sig1, method: str = LINEAR) -> FitResult:
    """Fit sigci (MPa) and mi of intact rock, classic HB (s = 1, a = 0.5).

    Linear form (Hoek, PRE ch.11): y = (sig1 - sig3)^2 = mi sigci sig3 + sigci^2.
    """

    sig3, sig1 = _validate(sig3, sig1, 2)
    _validate_triaxial(sig3, sig1)
    if method != LINEAR:
        return _nonlinear(
            lambda x, p: x + p[0] * np.sqrt(p[1] * x / p[0] + 1.0),
            [50.0, 10.0],
            sig3,
            sig1,
            method,
            "hoek_brown",
            TRIAXIAL,
            ["sigci_mpa", "mi"],
        )
    y = (sig1 - sig3) ** 2
    slope, intercept = np.polyfit(sig3, y, 1)
    if intercept <= 0:
        raise ValueError("data does not define a valid Hoek-Brown envelope")
    sigci = math.sqrt(intercept)
    mi = slope / sigci
    residual = sig1 - (sig3 + sigci * np.sqrt(mi * sig3 / sigci + 1.0))
    return FitResult("hoek_brown", TRIAXIAL, LINEAR, {"sigci_mpa": sigci, "mi": mi}, _ssr(residual))


def fit_ghb_mass_triaxial(sig3, sig1, sigci: float, disturbance: float, method: str = LEVENBERG_MARQUARDT) -> FitResult:
    """Fit mb, s, a of the generalized Hoek-Brown criterion to rock mass data.

    sigci (MPa) and D are fixed inputs, as in the RocData 'Use Rock Mass
    Data' analysis.
    """

    sig3, sig1 = _validate(sig3, sig1, 3)
    _validate_triaxial(sig3, sig1)
    if sigci <= 0:
        raise ValueError("sigci must be positive")
    model = lambda x, p: x + sigci * (p[0] * x / sigci + p[1]) ** p[2]
    return _nonlinear(
        model, [5.0, 0.01, 0.5], sig3, sig1, method, "generalized_hoek_brown", TRIAXIAL,
        ["mb", "s", "a"], {"sigci_mpa": sigci, "disturbance": disturbance},
    )


# ---------------------------------------------------------------- Barton-Bandis

def fit_barton_bandis_direct(normal, shear, phi_b_deg: float, method: str = LEVENBERG_MARQUARDT) -> FitResult:
    """Fit JRC and JCS (MPa) with the basic friction angle fixed."""

    normal, shear = _validate(normal, shear, 2)
    phi_b = math.radians(phi_b_deg)
    if np.any(normal <= 0):
        raise ValueError("Barton-Bandis requires positive normal stress")
    model = lambda x, p: x * np.tan(phi_b + p[0] * np.log10(p[1] / x))
    return _nonlinear(model, [10.0, 100.0], normal, shear, method, "barton_bandis", DIRECT, ["jrc", "jcs_mpa"], {"phi_b_deg": phi_b_deg})


# ---------------------------------------------------------------- Power Curve

def fit_power_curve_direct(normal, shear, method: str = LEVENBERG_MARQUARDT) -> FitResult:
    """Fit a, b, d (MPa) of tau = a (sigma + d)^b to direct shear data."""

    normal, shear = _validate(normal, shear, 3)
    model = lambda x, p: p[0] * (x + p[2]) ** p[1]
    return _nonlinear(model, [0.8, 0.8, 0.1], normal, shear, method, "power_curve", DIRECT, ["a", "b", "d_mpa"])


# ---------------------------------------------------------------- dispatcher

FITS: dict[tuple[str, str], Callable] = {
    ("mohr_coulomb", TRIAXIAL): fit_mohr_coulomb_triaxial,
    ("mohr_coulomb", DIRECT): fit_mohr_coulomb_direct,
    ("hoek_brown", TRIAXIAL): fit_hb_intact_triaxial,
    ("generalized_hoek_brown", TRIAXIAL): fit_ghb_mass_triaxial,
    ("barton_bandis", DIRECT): fit_barton_bandis_direct,
    ("power_curve", DIRECT): fit_power_curve_direct,
}

COMPATIBILITY: dict[str, tuple[str, ...]] = {
    "mohr_coulomb": (TRIAXIAL, DIRECT),
    "hoek_brown": (TRIAXIAL,),
    "generalized_hoek_brown": (TRIAXIAL,),
    "barton_bandis": (DIRECT,),
    "power_curve": (DIRECT,),
}


def available_fits(criterion_key: str) -> tuple[str, ...]:
    return COMPATIBILITY.get(criterion_key, ())


def fit(criterion_key: str, data_kind: str, x, y, method: str = LINEAR, fixed: dict[str, float] | None = None) -> FitResult:
    """Dispatch a fit; `fixed` carries inputs like sigci/D or phi_b."""

    fn = FITS.get((criterion_key, data_kind))
    if fn is None:
        raise ValueError(f"{criterion_key} cannot be fit to {data_kind} data")
    fixed = fixed or {}
    if criterion_key == "generalized_hoek_brown":
        return fn(x, y, fixed["sigci_mpa"], fixed.get("disturbance", 0.0), method)
    if criterion_key == "barton_bandis":
        return fn(x, y, fixed["phi_b_deg"], method)
    return fn(x, y, method)
