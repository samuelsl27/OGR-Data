"""Generic envelopes for the ten criteria of the reference program (spec 002).

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
        # Fs = sqrt(J2) + q_phi I1/3 - k = 0 with I1 tension positive (as in
        # the reference program), i.e. q = sqrt(3) (k + q_phi p) with p compression
        # positive (manual Fig. 4.2: q_phi = 0.5, k = 3 kPa, p0 = 100 kPa ->
        # q_f = 129 kPa). Spec 013b fix: spec 002 had the q_phi sign reversed.
        t = math.sqrt(3.0) * _f(params, "peak_q")
        k = _f(params, "peak_k") * KPA_TO_MPA
        if t >= 3.0:
            raise ValueError("Drucker-Prager q parameter must be below sqrt(3) for a triaxial envelope")
        slope = (1.0 + 2.0 * t / 3.0) / (1.0 - t / 3.0)
        intercept = math.sqrt(3.0) * k / (1.0 - t / 3.0)
        return sig3, intercept + slope * sig3

    if key in ("cam_clay", "modified_cam_clay"):
        # Critical state line q = M p, drawn as a strength envelope.
        m = _f(params, "critical_state_slope")
        slope = (1.0 + 2.0 * m / 3.0) / (1.0 - m / 3.0)
        return sig3, slope * sig3

    if key == "softening_hardening":
        # Failure surface is Mohr-Coulomb; M for triaxial compression
        # (Pietruszczak 2010): M = 6 sin(phi)/(3 - sin(phi))
        phi = math.radians(_f(params, "peak_friction"))
        m = 6.0 * math.sin(phi) / (3.0 - math.sin(phi))
        c = _f(params, "peak_cohesion") * KPA_TO_MPA
        slope = (1.0 + 2.0 * m / 3.0) / (1.0 - m / 3.0)
        # q = M (p + c/tan(phi)) in compression-positive convention
        # (the reference program writes q + M(p - c/tan(phi)) = 0 with
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
        # spec 026: tau = a (sigma_n + d)^b + c + sigma_n tan(i), every stress
        # in kPa, a included (its value depends on the stress unit when
        # b != 1). a (sigma_n + d)^b is the power-law Mohr envelope of Hoek and
        # Brown (FHWA 1989, eq. 30: a = A sigci^(1-B), b = B, d = -T sigci);
        # c (strength at sigma_n = -d) and the waviness angle i, added to the
        # friction as Patton's roughness angle (Hoek 2023, eq. 3), are deduced.
        a, b = _f(params, "a"), _f(params, "b")
        c, d = _f(params, "c"), _f(params, "d")
        waviness = math.radians(_f(params, "waviness"))
        normal = np.linspace(0.0, sig3max_mpa, points)
        n_kpa = normal / KPA_TO_MPA
        tau_kpa = a * np.maximum(n_kpa + d, 0.0) ** b + c + n_kpa * math.tan(waviness)
        return normal, tau_kpa * KPA_TO_MPA

    if key == "barton_bandis":
        # tau = sigma_n tan(phi_r + JRC log10(JCS / sigma_n)), 0 < sigma_n <= JCS
        # (angles in degrees; Barton-Bandis 1982 as used by the earlier reference program)
        phi_r = _f(params, "phi_r")
        jrc = _f(params, "jrc")
        jcs = _f(params, "jcs") * KPA_TO_MPA
        hi = min(sig3max_mpa, jcs)
        lo = max(hi * 1e-4, 1e-6)
        normal = np.geomspace(lo, hi, points)
        angle = np.radians(phi_r + jrc * np.log10(jcs / normal))
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


def envelopes(key: str, params: Params, sig3max_mpa: float) -> tuple[tuple | None, tuple | None]:
    """Envelope of a material in both plots: ((sig3, sig1) | None, (sigma_n, tau) | None).

    Principal-space criteria give both (the shear one by the tangent Mohr
    construction); shear-space criteria only the shear one; criteria with
    no envelope give neither (spec 011: other materials of the project).
    """

    crit = CRITERIA[key]
    if crit.envelope == "principal":
        curve = principal_curve(key, params, sig3max_mpa)
        if curve is None:
            return None, None
        return curve, tangent_shear(*curve)
    if crit.envelope == "shear":
        return None, shear_curve(key, params, sig3max_mpa)
    return None, None
