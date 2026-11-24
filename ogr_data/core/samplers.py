"""Graphical samplers and plot overlays (spec 008).

Stress sampler, instantaneous Mohr-Coulomb sampler, best-fit MC overlay
and Mogi line, as in the earlier reference program:
stress sampler (p. 33), instantaneous Mohr-Coulomb sampler (pp. 33-34,
tangential line with instantaneous c and phi), equivalent / best-fit MC
envelope (p. 10) and Mogi's line sig1/sig3 = 3.4 (p. 37).

The instantaneous friction angle follows the analytic derivative
d(sigma1)/d(sigma3) of the envelope (Hoek 2002 notation, same tangent
construction as core/envelope.py): sin(phi) = (d1 - 1) / (d1 + 1).

Internal stress unit: MPa.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

MOGI_RATIO = 3.4


@dataclass(frozen=True)
class StressSample:
    """Envelope coordinates at the sampled abscissa (MPa)."""

    x: float
    y: float


@dataclass(frozen=True)
class InstantaneousMC:
    """Instantaneous Mohr-Coulomb parameters at an envelope point (MPa, deg).

    slope is d(sigma1)/d(sigma3) for principal-space envelopes and
    d(tau)/d(sigma_n) for shear-space envelopes.
    """

    cohesion_mpa: float
    friction_deg: float
    point_x: float
    point_y: float
    slope: float


def sample(x_arr: np.ndarray, y_arr: np.ndarray, x: float) -> StressSample:
    """Envelope ordinate at abscissa x, clipped to the curve range."""

    x_arr = np.asarray(x_arr, dtype=float)
    y_arr = np.asarray(y_arr, dtype=float)
    xc = float(np.clip(x, x_arr[0], x_arr[-1]))
    return StressSample(x=xc, y=float(np.interp(xc, x_arr, y_arr)))


def hb_derivative(sig3: float, sigci: float, mb: float, s: float, a: float) -> float:
    """Analytic d(sigma1)/d(sigma3) of the Hoek-Brown envelope (Hoek 2002)."""

    return 1.0 + mb * a * (mb * sig3 / sigci + s) ** (a - 1.0)


def instantaneous_mc(
    sig3: np.ndarray,
    sig1: np.ndarray,
    x: float,
    slope: float | None = None,
) -> InstantaneousMC:
    """Instantaneous MC parameters of a principal-space envelope at x = sigma3.

    slope is the analytic derivative d(sigma1)/d(sigma3) at the point if
    known (Hoek-Brown family); otherwise it is taken numerically from the
    curve. The tangent line in principal space is
    sigma1 = intercept + slope * sigma3 with
    intercept = sigma1* - slope * sigma3*, and
    c = intercept * (1 - sin(phi)) / (2 cos(phi)).
    """

    sig3 = np.asarray(sig3, dtype=float)
    sig1 = np.asarray(sig1, dtype=float)
    s = sample(sig3, sig1, x)
    d1 = float(slope) if slope is not None else float(np.interp(s.x, sig3, np.gradient(sig1, sig3)))
    sin_phi = (d1 - 1.0) / (d1 + 1.0)
    phi = math.degrees(math.asin(min(max(sin_phi, -1.0), 1.0)))
    intercept = s.y - d1 * s.x
    cohesion = intercept * (1.0 - sin_phi) / (2.0 * math.cos(math.radians(phi)))
    return InstantaneousMC(cohesion_mpa=cohesion, friction_deg=phi, point_x=s.x, point_y=s.y, slope=d1)


def instantaneous_mc_shear(normal: np.ndarray, shear: np.ndarray, x: float) -> InstantaneousMC:
    """Instantaneous MC parameters of a shear-space envelope at x = sigma_n.

    The envelope tangent at the point is the instantaneous MC line
    tau = c + sigma_n * tan(phi) with tan(phi) = d(tau)/d(sigma_n).
    """

    normal = np.asarray(normal, dtype=float)
    shear = np.asarray(shear, dtype=float)
    s = sample(normal, shear, x)
    slope = float(np.interp(s.x, normal, np.gradient(shear, normal)))
    tan_phi = max(slope, 0.0)
    phi = math.degrees(math.atan(tan_phi))
    cohesion = s.y - s.x * tan_phi
    return InstantaneousMC(cohesion_mpa=cohesion, friction_deg=phi, point_x=s.x, point_y=s.y, slope=slope)


def mc_tangent_principal(inst: InstantaneousMC, x_range: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The instantaneous MC line in principal stress space."""

    sin_phi = math.sin(math.radians(inst.friction_deg))
    denom = 1.0 - sin_phi
    slope = (1.0 + sin_phi) / denom
    intercept = 2.0 * inst.cohesion_mpa * math.cos(math.radians(inst.friction_deg)) / denom
    x_range = np.asarray(x_range, dtype=float)
    return x_range, intercept + slope * x_range


def mc_tangent_shear(inst: InstantaneousMC, x_range: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The instantaneous MC line in shear-normal stress space."""

    x_range = np.asarray(x_range, dtype=float)
    return x_range, inst.cohesion_mpa + x_range * math.tan(math.radians(inst.friction_deg))


def best_fit_mc(normal: np.ndarray, shear: np.ndarray) -> InstantaneousMC:
    """Least-squares best-fit MC line tau = c + sigma_n tan(phi).

    As in the earlier reference program, the best-fit Mohr-Coulomb envelope is determined
    over the displayed stress range (vertical residuals, same convention
    as the fitting module).
    """

    normal = np.asarray(normal, dtype=float)
    shear = np.asarray(shear, dtype=float)
    design = np.column_stack([np.ones_like(normal), normal])
    (c, t), *_ = np.linalg.lstsq(design, shear, rcond=None)
    phi = math.degrees(math.atan(max(t, 0.0)))
    return InstantaneousMC(cohesion_mpa=float(c), friction_deg=phi, point_x=0.0, point_y=float(c), slope=float(t))


def mogi_line(x_max: float, points: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Mogi's line sigma1 = MOGI_RATIO * sigma3 (as in the earlier reference program)."""

    sig3 = np.linspace(0.0, x_max, points)
    return sig3, MOGI_RATIO * sig3
