"""Spec 006: fitting strength criteria to lab data."""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import fitting
from ogr_data.core.fitting import DIRECT, LEVENBERG_MARQUARDT, LINEAR, SIMPLEX, TRIAXIAL


def test_mohr_coulomb_triaxial_recovers_parameters():
    c, phi = 0.02, 30.0  # MPa
    sin = math.sin(math.radians(phi))
    sig3 = np.array([0.0, 0.5, 1.0, 2.0, 4.0])
    sig1 = 2 * c * math.cos(math.radians(phi)) / (1 - sin) + (1 + sin) / (1 - sin) * sig3
    for method in (LINEAR, LEVENBERG_MARQUARDT, SIMPLEX):
        r = fitting.fit_mohr_coulomb_triaxial(sig3, sig1, method)
        assert abs(r.parameters["cohesion_mpa"] - c) < 1e-6
        assert abs(r.parameters["friction_deg"] - phi) < 1e-4
        assert r.residuals < 1e-12


def test_mohr_coulomb_direct_recovers_parameters():
    c, phi = 0.01, 35.0
    normal = np.array([0.1, 0.5, 1.0, 2.0])
    shear = c + normal * math.tan(math.radians(phi))
    r = fitting.fit_mohr_coulomb_direct(normal, shear)
    assert abs(r.parameters["cohesion_mpa"] - c) < 1e-9
    assert abs(r.parameters["friction_deg"] - phi) < 1e-6


def test_hb_intact_linearization_matches_hoek_ch11():
    # Hoek PRE ch.11 spreadsheet: y = (sig1-sig3)^2, slope = mi sigci,
    # intercept = sigci^2. Synthetic intact rock: sigci=50 MPa, mi=10.
    sigci, mi = 50.0, 10.0
    sig3 = np.array([0.0, 2.5, 5.0, 7.5, 15.0, 20.0, 47.5])
    sig1 = sig3 + sigci * np.sqrt(mi * sig3 / sigci + 1.0)
    r = fitting.fit_hb_intact_triaxial(sig3, sig1, LINEAR)
    assert abs(r.parameters["sigci_mpa"] - sigci) < 1e-9
    assert abs(r.parameters["mi"] - mi) < 1e-9
    assert r.residuals < 1e-9
    # nonlinear methods recover too
    r = fitting.fit_hb_intact_triaxial(sig3, sig1, LEVENBERG_MARQUARDT)
    assert abs(r.parameters["sigci_mpa"] - sigci) < 1e-3
    assert abs(r.parameters["mi"] - mi) < 1e-3


def test_ghb_mass_fit():
    sigci, mb, s, a = 30.0, 1.6768, 0.0039, 0.5057
    sig3 = np.linspace(0.0, 7.5, 8)
    sig1 = sig3 + sigci * (mb * sig3 / sigci + s) ** a
    r = fitting.fit("generalized_hoek_brown", TRIAXIAL, sig3, sig1, LEVENBERG_MARQUARDT, {"sigci_mpa": sigci})
    assert abs(r.parameters["mb"] - mb) < 5e-3
    assert abs(r.parameters["s"] - s) < 5e-5
    assert abs(r.parameters["a"] - a) < 5e-4
    assert r.residuals < 1e-6
    assert r.fixed["sigci_mpa"] == sigci


def test_barton_bandis_fit():
    phi_b, jrc, jcs = 30.0, 12.0, 80.0  # MPa
    normal = np.geomspace(0.5, 50.0, 8)
    shear = normal * np.tan(np.radians(phi_b) + jrc * np.log10(jcs / normal))
    r = fitting.fit("barton_bandis", DIRECT, normal, shear, LEVENBERG_MARQUARDT, {"phi_b_deg": phi_b})
    assert abs(r.parameters["jrc"] - jrc) < 1e-2
    assert abs(r.parameters["jcs_mpa"] - jcs) < 1e-1
    assert r.fixed["phi_b_deg"] == phi_b


def test_power_curve_fit():
    a, b, d = 0.7, 0.8, 0.05
    normal = np.linspace(0.0, 3.0, 8)
    shear = a * (normal + d) ** b
    r = fitting.fit("power_curve", DIRECT, normal, shear, LEVENBERG_MARQUARDT)
    assert abs(r.parameters["a"] - a) < 1e-3
    assert abs(r.parameters["b"] - b) < 1e-3
    assert abs(r.parameters["d_mpa"] - d) < 1e-3


def test_invalid_triaxial_rejected():
    sig3 = np.array([5.0, 1.0])
    sig1 = np.array([1.0, 10.0])
    try:
        fitting.fit_mohr_coulomb_triaxial(sig3, sig1)
    except ValueError as exc:
        assert "sigma3 > sigma1" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_compatibility_table():
    assert fitting.available_fits("mohr_coulomb") == (TRIAXIAL, DIRECT)
    assert fitting.available_fits("barton_bandis") == (DIRECT,)
    assert fitting.available_fits("hoek_brown") == (TRIAXIAL,)
    assert fitting.available_fits("cam_clay") == ()
    try:
        fitting.fit("barton_bandis", TRIAXIAL, [1, 2], [1, 2])
    except ValueError as exc:
        assert "cannot be fit" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_fit_dialog_offscreen():
    import numpy as np
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.fit_dialog import FitDialog

    app = QApplication.instance() or QApplication([])
    dlg = FitDialog()
    # paste synthetic MC triaxial data through the clipboard path
    sin = math.sin(math.radians(30.0))
    sig3 = [0.0, 1.0, 2.0, 4.0]
    rows = "\n".join(f"{x}\t{0.02 * math.cos(math.radians(30.0)) * 2 / (1 - sin) + (1 + sin) / (1 - sin) * x}" for x in sig3)
    QApplication.clipboard().setText(rows)
    dlg._paste()
    dlg._method.setCurrentIndex(dlg._method.findData(LINEAR))
    dlg._run_fit()
    assert dlg._result is not None
    assert abs(dlg._result.parameters["friction_deg"] - 30.0) < 1e-6
    assert dlg._apply_button.isEnabled()
    dlg.reject()
