"""sigma3max estimation by application (spec 009): tunnels and slopes.

Hoek, Carranza-Torres & Corkum (2002), section 6, equations 18 and 19:

    tunnels:  sig3max = 0.47 * sigcm * (sigcm / (gamma * H)) ** (-0.94)
    slopes:   sig3max = 0.72 * sigcm * (sigcm / (gamma * H)) ** (-0.91)

where sigcm is the global rock mass strength (paper eq. 17, see
core/hoek_brown.py), gamma the rock mass unit weight (MN/m3) and H the
tunnel depth or slope height (m); gamma * H is a stress in MPa. Marinos &
Hoek (2000) section 2.2 gives the range 0 < sig3 < sigv with
sigv = depth * unit weight.

Validated against ORMAS V2.0 (spec 009): default material
(sigci 30 MPa, GSI 50, mi 10, D 0 -> sigcm 5.2300 MPa), gamma = 0.026
MN/m3 and H = 50 m give sig3max = 0.6643 MPa (ORMAS: 0.6642) for tunnels
and 1.0610 MPa for slopes (reproduces the ORMAS fit phi = 46.50 deg).
"""

from __future__ import annotations

TUNNEL_FACTOR = 0.47
TUNNEL_EXPONENT = -0.94
SLOPE_FACTOR = 0.72
SLOPE_EXPONENT = -0.91


def _check(sigcm_mpa: float, unit_weight_mn_m3: float, depth_m: float) -> float:
    if sigcm_mpa <= 0.0:
        raise ValueError("sigcm must be positive")
    if unit_weight_mn_m3 <= 0.0:
        raise ValueError("unit weight must be positive")
    if depth_m <= 0.0:
        raise ValueError("depth must be positive")
    return sigcm_mpa / (unit_weight_mn_m3 * depth_m)


def sig3max_tunnel(sigcm_mpa: float, unit_weight_mn_m3: float, depth_m: float) -> float:
    """Maximum sigma3 for tunnel design (Hoek et al. 2002, eq. 18)."""

    ratio = _check(sigcm_mpa, unit_weight_mn_m3, depth_m)
    return TUNNEL_FACTOR * sigcm_mpa * ratio ** TUNNEL_EXPONENT


def sig3max_slope(sigcm_mpa: float, unit_weight_mn_m3: float, height_m: float) -> float:
    """Maximum sigma3 for slope design (Hoek et al. 2002, eq. 19)."""

    ratio = _check(sigcm_mpa, unit_weight_mn_m3, height_m)
    return SLOPE_FACTOR * sigcm_mpa * ratio ** SLOPE_EXPONENT
