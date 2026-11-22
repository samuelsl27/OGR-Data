"""Failure envelope points in principal and shear-normal stress space.

The shear-normal envelope is the tangent construction on the Mohr circles
of consecutive principal-stress pairs, using the analytic derivative
d(sigma1)/d(sigma3) of the Hoek-Brown envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .hoek_brown import HbInput, major_principal_stress


@dataclass(frozen=True)
class Envelope:
    sig3: np.ndarray
    sig1: np.ndarray
    normal: np.ndarray
    shear: np.ndarray


def principal_envelope(inp: HbInput, mb: float, s: float, a: float, points: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """sigma3 / sigma1 arrays of the envelope from 0 to sig3max (MPa)."""

    sig3 = np.linspace(0.0, inp.sig3max, points)
    sig1 = major_principal_stress(inp, mb, s, a, sig3)
    return sig3, sig1


def shear_normal_envelope(inp: HbInput, mb: float, s: float, a: float, points: int = 200) -> Envelope:
    """Tangent envelope points (normal, shear) in MPa.

    For a Mohr circle with centre c and radius R whose envelope tangent has
    instantaneous friction sin(phi_i) = (d1 - 1) / (d1 + 1) with
    d1 = d(sigma1)/d(sigma3), the tangency point is
    normal = c - R * sin(phi_i), shear = R * cos(phi_i).
    """

    sig3, sig1 = principal_envelope(inp, mb, s, a, points)
    d1 = 1.0 + mb * a * (mb * sig3 / inp.sigci + s) ** (a - 1.0)
    sin_phi = np.clip((d1 - 1.0) / (d1 + 1.0), -1.0, 1.0)
    centre = (sig1 + sig3) / 2.0
    radius = (sig1 - sig3) / 2.0
    normal = centre - radius * sin_phi
    shear = radius * np.sqrt(1.0 - sin_phi**2)
    return Envelope(sig3=sig3, sig1=sig1, normal=normal, shear=shear)
