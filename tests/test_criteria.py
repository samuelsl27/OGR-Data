"""Spec 002: the ten RSData criteria — registry defaults and envelopes."""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import criteria_envelopes as ce
from ogr_data.core.models import CRITERIA, defaults


def test_ten_criteria_present():
    assert set(CRITERIA) == {
        "mohr_coulomb",
        "hoek_brown",
        "drucker_prager",
        "generalized_hoek_brown",
        "cam_clay",
        "modified_cam_clay",
        "softening_hardening",
        "norsand",
        "power_curve",
        "barton_bandis",
    }
    assert all(c.fields for c in CRITERIA.values())


def test_defaults_match_rsdata_capture():
    d = defaults("mohr_coulomb")
    assert d["peak_cohesion"] == 10.5 and d["peak_friction"] == 35.0
    d = defaults("hoek_brown")
    assert d["compressive_strength"] == 100000.0 and d["mb"] == 1.0 and d["s"] == 0.001
    d = defaults("drucker_prager")
    assert d["peak_q"] == 0.005 and d["peak_k"] == 35.0
    d = defaults("generalized_hoek_brown")
    assert d["sigci"] == 100000.0 and d["gsi"] == 50.0 and d["mi"] == 10.0 and d["d"] == 0.0
    for key in ("cam_clay", "modified_cam_clay"):
        d = defaults(key)
        assert d["critical_state_slope"] == 1.3 and d["specific_volume_unit_pressure"] == 2.61
        assert d["kappa"] == 0.025 and d["ocr"] == 2.0 and d["lambda"] == 0.15
    d = defaults("softening_hardening")
    assert d["peak_friction"] == 35.0 and d["peak_cohesion"] == 10.5 and d["hardening_property"] == 0.005
    d = defaults("norsand")
    assert d["m_tc"] == 1.4 and d["lambda"] == 0.06 and d["h0"] == 75.0 and d["psi0"] == -0.025
    d = defaults("power_curve")
    assert d["a"] == 0.7 and d["b"] == 1.0 and d["dilation_ratio"] == 0.5
    d = defaults("barton_bandis")
    assert d["phi_r"] == 30.0 and d["jrc"] == 10.0 and d["jcs"] == 1e7


def test_mohr_coulomb_tangent_recovers_line():
    params = defaults("mohr_coulomb")
    params["peak_cohesion"] = 12.0  # kPa
    params["peak_friction"] = 30.0  # deg
    sig3max = 1.0  # MPa
    sig3, sig1 = ce.principal_curve("mohr_coulomb", params, sig3max)
    normal, shear = ce.tangent_shear(sig3, sig1)
    c_mpa = 12.0 / 1000.0
    phi = math.radians(30.0)
    expected = c_mpa + normal * math.tan(phi)
    assert np.allclose(shear, expected, atol=1e-9)


def test_hoek_brown_classic_uniaxial():
    params = defaults("hoek_brown")
    params["compressive_strength"] = 50000.0  # kPa
    params["mb"] = 8.0
    params["s"] = 0.1
    sig3, sig1 = ce.principal_curve("hoek_brown", params, 10.0)
    assert abs(sig1[0] - 50.0 * math.sqrt(0.1)) < 1e-9  # sigci * sqrt(s) at sig3 = 0


def test_drucker_prager_positive_and_linear():
    params = defaults("drucker_prager")
    sig3, sig1 = ce.principal_curve("drucker_prager", params, 1.0)
    assert np.all(np.diff(sig1) > 0.0)
    k = np.polyfit(sig3, sig1, 1)
    assert abs(k[1] - (math.sqrt(3.0) * 35.0 / 1000.0) / (1.0 + math.sqrt(3.0) * 0.005 / 3.0)) < 1e-9


def test_cam_clay_csl_linear_through_origin():
    params = defaults("cam_clay")
    for key in ("cam_clay", "modified_cam_clay"):
        sig3, sig1 = ce.principal_curve(key, params, 1.0)
        assert abs(sig1[0]) < 1e-12
        m = params["critical_state_slope"]
        slope = (1.0 + 2.0 * m / 3.0) / (1.0 - m / 3.0)
        assert np.allclose(np.diff(sig1) / np.diff(sig3), slope, atol=1e-9)


def test_softening_hardening_is_mc_at_failure():
    params = defaults("softening_hardening")
    params["peak_cohesion"] = 20.0  # kPa
    params["peak_friction"] = 30.0  # deg
    sig3, sig1 = ce.principal_curve("softening_hardening", params, 1.0)
    normal, shear = ce.tangent_shear(sig3, sig1)
    c_mpa = 20.0 / 1000.0
    phi = math.radians(30.0)
    # The failure surface is Mohr-Coulomb, so the tangent construction
    # recovers tau = c + sigma_n tan(phi).
    assert np.allclose(shear, c_mpa + normal * math.tan(phi), atol=1e-9)


def test_power_curve_formula():
    params = defaults("power_curve")
    params["a"] = 0.7
    params["b"] = 0.8
    params["d"] = 50.0  # kPa
    normal, shear = ce.shear_curve("power_curve", params, 2.0)
    expected = 0.7 * (normal + 0.05) ** 0.8
    assert np.allclose(shear, expected, atol=1e-12)


def test_barton_bandis_formula():
    params = defaults("barton_bandis")
    params["phi_r"] = 30.0
    params["jrc"] = 10.0
    params["jcs"] = 100000.0  # kPa = 100 MPa
    normal, shear = ce.shear_curve("barton_bandis", params, 10.0)
    expected = normal * np.tan(np.radians(30.0) + 10.0 * np.log10(100.0 / normal))
    assert np.allclose(shear, expected, rtol=1e-12)


def test_norsand_has_no_envelope_yet():
    params = defaults("norsand")
    assert ce.principal_curve("norsand", params, 1.0) is None
    assert ce.shear_curve("norsand", params, 1.0) is None
