"""Envelope construction tests."""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core.envelope import shear_normal_envelope
from ogr_data.core.hoek_brown import HbInput, hoek_brown_constants


def test_tangent_envelope_starts_at_sigt() -> None:
    inp = HbInput()
    mb, s, a = hoek_brown_constants(inp)
    env = shear_normal_envelope(inp, mb, s, a, points=200)
    # First tangent point of the shear-normal envelope sits at the tensile
    # intercept: normal = sigt, shear = 0.
    assert abs(env.normal[0] - (-0.0692)) < 5e-3
    assert abs(env.shear[0]) < 1e-6


def test_shear_stays_positive_and_monotonic_envelope() -> None:
    inp = HbInput(sigci=80.0, gsi=65.0, mi=15.0, sig3max=20.0)
    mb, s, a = hoek_brown_constants(inp)
    env = shear_normal_envelope(inp, mb, s, a, points=500)
    assert np.all(env.shear >= 0.0)
    assert np.all(np.diff(env.shear) > 0.0), "shear envelope must increase"


def test_principal_envelope_matches_formula() -> None:
    inp = HbInput()
    mb, s, a = hoek_brown_constants(inp)
    env = shear_normal_envelope(inp, mb, s, a)
    # At sig3 = 0 the envelope point is the uniaxial strength.
    assert abs(env.sig1[0] - inp.sigci * s**a) < 1e-9
