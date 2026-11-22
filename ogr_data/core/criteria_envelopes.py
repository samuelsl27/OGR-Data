"""Generic envelopes for the ten RSData criteria (spec 002).

Conventions: the registry stores kPa and degrees; this module works in MPa
and degrees, and returns MPa arrays. Criteria with envelope space
"principal" provide sigma1(sigma3); "shear" criteria provide tau(sigma_n);
"norsand" has no envelope yet (parameters only).
"""

from __future__ import annotations

import math
from typing import Mapping, Union

import numpy as np

from .hoek_brown import HbInput, major_principal_stress, hoek_brown_constants
from .models import CRITERIA

Params = Mapping[str, Union[float, bool, str]]

KPA_TO_MPA = 1.0 / 1000.0


def _f(params: Params, key: str) -> float:
    return float(params[key])


def _mc_principal(c_mpa: float, friction_deg: float, sig3: np.ndarray) -> np.ndarray:
    """Mohr-Coulomb line in principal stress space (MPa)."""

    phi = math.radians(friction_deg)
    sin_phi = math.sin(phi)
    intercept = 2.0 * c_mpa * math.cos(phi) / (1.0 - sin_phi)
    slope = (1.0 + sin_phi) / (1.0 - sin_phi)
    return intercept + slope * sig3


def principal_curve(key: str, params: Params, sig3max_mpa: float, points: int = 200) -> tuple[np.ndarray, np.ndarray] | None:
    """(sigma3, sigma1) arrays of the criterion envelope in MPa, or None."""

    crit = CRITERIA[key]
    if crit.envelope != "principal":
        return None
    sig3 = np.linspace(0.0, sig3max_mpa, points)

    if key == "mohr_coulomb":
        return sig3, _mc_principal(_f(params, "peak_cohesion") * KPA_TO_MPA, _f(params, "peak_friction"), sig3)

    if key == "hoek_brown":
        sigci = _f(params, "compressive_strength") * KPA_TO_MPA
        mb, s = _f(params, "mb"), _f(params, "s")
        return sig3, sig3 + sigci * np.sqrt(mb * sig3 / sigci + s)

    if key == "generalized_hoek_brown":
        inp = HbInput(
            sigci=_f(params, "sigci") * KPA_TO_MPA,
            gsi=_f(params, "gsi"),
            mi=_f(params, "mi"),
            disturbance=_f(params, "d"),
            sig3max=sig3max_mpa,
        )
        mb, s, a = hoek_brown_constants(inp)
        return sig3, major_principal_stress(inp, mb, s, a, sig3)

    if key == "drucker_prager":
        # Fs = sqrt(J2) + (q_phi/3) I1 - k = 0 -> q = sqrt(3) (k - q_phi p)
        t = math.sqrt(3.0) * _f(params, "peak_q")
        k = _f(params, "peak_k") * KPA_TO_MPA
        slope = (1.0 - 2.0 * t / 3.0) / (1.0 + t / 3.0)
        intercept = math.sqrt(3.0) * k / (1.0 + t / 3.0)
        return sig3, intercept + slope * sig3

    if key in ("cam_clay", "modified_cam_clay"):
        # Critical state line q = M p, drawn as a strength envelope.
        m = _f(params, "critical_state_slope")
        slope = (1.0 + 2.0 * m / 3.0) / (1.0 - m / 3.0)
        return sig3, slope * sig3

    if key == "softening_hardening":
        # Failure surface is Mohr-Coulomb; M for triaxial compression
        # (RSData theory manual, Pietruszczak 2010): M = 6 sin(phi)/(3 - sin(phi))
        phi = math.radians(_f(params, "peak_friction"))
        m = 6.0 * math.sin(phi) / (3.0 - math.sin(phi))
        c = _f(params, "peak_cohesion") * KPA_TO_MPA
        slope = (1.0 + 2.0 * m / 3.0) / (1.0 - m / 3.0)
        # q = M (p + c/tan(phi)) in compression-positive convention
        # (the RSData manual writes q + M(p - c/tan(phi)) = 0 with
        # compression negative).
        intercept = (m * c / math.tan(phi)) / (1.0 - m / 3.0)
        return sig3, intercept + slope * sig3

    raise ValueError(f"no principal envelope implemented for {key!r}")


def shear_curve(key: str, params: Params, sig3max_mpa: float, points: int = 200) -> tuple[np.ndarray, np.ndarray] | None:
    """(normal, shear) arrays in MPa for shear-space criteria, else None."""

    crit = CRITERIA[key]
    if crit.envelope != "shear":
        return None

    if key == "power_curve":
        # RocData 2004 manual: tau = a (sigma + d)^b. Fields c and waviness
        # are kept in the registry (RSData dialog) with no effect until their
        # exact semantics are verified.
        a, b = _f(params, "a"), _f(params, "b")
        d = _f(params, "d") * KPA_TO_MPA
        normal = np.linspace(0.0, sig3max_mpa, points)
        return normal, a * (normal + d) ** b

    if key == "barton_bandis":
        # tau = sigma_n tan(phi_r + JRC log10(JCS / sigma_n)), 0 < sigma_n <= JCS
        phi_r = math.radians(_f(params, "phi_r"))
        jrc = _f(params, "jrc")
        jcs = _f(params, "jcs") * KPA_TO_MPA
        hi = min(sig3max_mpa, jcs)
        lo = max(hi * 1e-4, 1e-6)
        normal = np.geomspace(lo, hi, points)
        angle = phi_r + jrc * np.log10(jcs / normal)
        return normal, normal * np.tan(angle)

    raise ValueError(f"no shear envelope implemented for {key!r}")


def numeric_derivative(sig3: np.ndarray, sig1: np.ndarray) -> np.ndarray:
    """Central differences of sigma1 over sigma3 (clipped at the ends)."""

    d1 = np.gradient(sig1, sig3)
    return d1


def tangent_shear(sig3: np.ndarray, sig1: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Tangent (Mohr) construction of the shear-normal envelope (MPa)."""

    d1 = numeric_derivative(sig3, sig1)
    sin_phi = np.clip((d1 - 1.0) / (d1 + 1.0), -1.0, 1.0)
    centre = (sig1 + sig3) / 2.0
    radius = (sig1 - sig3) / 2.0
    normal = centre - radius * sin_phi
    shear = radius * np.sqrt(1.0 - sin_phi**2)
    return normal, shear


def mc_line(cohesion_mpa: float, friction_deg: float, sig3max_mpa: float) -> tuple[np.ndarray, np.ndarray]:
    """Mohr-Coulomb line in both spaces, for overlays (MPa)."""

    sig3 = np.linspace(0.0, sig3max_mpa, 2)
    sig1 = _mc_principal(cohesion_mpa, friction_deg, sig3)
    phi = math.radians(friction_deg)
    normal = sig3
    shear = cohesion_mpa + normal * math.tan(phi)
    return (sig3, sig1), (normal, shear)
