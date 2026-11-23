"""Spec 009: sig3max by application (tunnel / slope), validated vs ORMAS."""

from __future__ import annotations


def _sigcm_default() -> float:
    from ogr_data.core.hoek_brown import HbInput, compute

    inp = HbInput(sigci=30.0, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=7.5)
    return compute(inp).sigcm


def test_tunnel_matches_ormas() -> None:
    from ogr_data.core import application

    sigcm = _sigcm_default()
    assert abs(sigcm - 5.2300) < 1e-3  # ORMAS rock mass strength
    sig3max = application.sig3max_tunnel(sigcm, 0.026, 50.0)
    # ORMAS V2.0 (annotated): 0.6642 MPa with unit weight 0.026, depth 50 m
    assert abs(sig3max - 0.6642) / 0.6642 < 0.005
    # below the vertical stress sigv = gamma * H (Marinos & Hoek 2000, 2.2)
    assert sig3max < 0.026 * 50.0


def test_slope_reproduces_ormas_fit_phi() -> None:
    from ogr_data.core import application
    from ogr_data.core.hoek_brown import HbInput, equivalent_mc, hoek_brown_constants

    sigcm = _sigcm_default()
    sig3max = application.sig3max_slope(sigcm, 0.026, 50.0)
    assert abs(sig3max - 1.0610) < 1e-3

    # the closed-form MC fit at that sig3max must reproduce the ORMAS
    # annotated slope fit phi = 46.50 deg
    inp = HbInput(sigci=30.0, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max)
    mb, s, a = hoek_brown_constants(inp)
    mc = equivalent_mc(inp, mb, s, a)
    assert abs(mc.friction_deg - 46.50) < 0.05


def test_tunnel_reproduces_ormas_fit_phi() -> None:
    from ogr_data.core import application
    from ogr_data.core.hoek_brown import HbInput, equivalent_mc, hoek_brown_constants

    sigcm = _sigcm_default()
    sig3max = application.sig3max_tunnel(sigcm, 0.026, 50.0)
    inp = HbInput(sigci=30.0, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max)
    mb, s, a = hoek_brown_constants(inp)
    mc = equivalent_mc(inp, mb, s, a)
    # ORMAS annotated tunnel fit: phi = 49.98 deg
    assert abs(mc.friction_deg - 49.98) < 0.05


def test_sig3max_scales_with_depth() -> None:
    from ogr_data.core import application

    sigcm = _sigcm_default()
    shallow = application.sig3max_tunnel(sigcm, 0.026, 25.0)
    deep = application.sig3max_tunnel(sigcm, 0.026, 100.0)
    assert 0.0 < shallow < deep


def test_validation() -> None:
    from ogr_data.core import application

    for fn in (application.sig3max_tunnel, application.sig3max_slope):
        for args in ((0.0, 0.026, 50.0), (5.23, 0.0, 50.0), (5.23, 0.026, 0.0)):
            try:
                fn(*args)
            except ValueError:
                pass
            else:
                raise AssertionError(f"expected ValueError for {fn.__name__}{args}")


def test_application_window_offscreen() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
    w._widgets["sigci"].setValue(30000.0)  # 30 MPa, the ORMAS case
    app.processEvents()

    # custom: manual sigma3max (default)
    assert w._application_combo.currentData() == "custom"
    assert w._sig3max.isEnabled()
    assert w._app_fields.isHidden()

    # tunnel: sigma3max estimated from sigcm (Hoek 2002 eq. 18)
    w._application_combo.setCurrentIndex(w._application_combo.findData("tunnel"))
    assert not w._sig3max.isEnabled()
    assert not w._app_fields.isHidden()
    assert abs(w._sig3max.value() - 0.6642) / 0.6642 < 0.005
    assert "sigma3max" not in w._sig3max_label.text() or w._sig3max_label.isHidden()

    # slope: eq. 19
    w._application_combo.setCurrentIndex(w._application_combo.findData("slope"))
    assert abs(w._sig3max.value() - 1.0610) < 1e-3
    assert w._depth_label.text() == "Slope height"

    # changing the unit weight recomputes
    w._unit_weight.setValue(0.030)
    assert abs(w._sig3max.value() - _slope_003()) < 1e-4  # spin has 4 decimals

    # non-HB criteria fall back to custom (no sigcm, as in ORMAS)
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("mohr_coulomb"))
    assert w._application_combo.currentData() == "custom"
    assert w._sig3max.isEnabled()


def _tunnel_003() -> float:
    from ogr_data.core import application
    from ogr_data.core.hoek_brown import HbInput, compute

    inp = HbInput(sigci=30.0, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=7.5)
    sigcm = compute(inp).sigcm
    return application.sig3max_tunnel(sigcm, 0.030, 50.0)


def _slope_003() -> float:
    from ogr_data.core import application
    from ogr_data.core.hoek_brown import HbInput, compute

    inp = HbInput(sigci=30.0, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=7.5)
    sigcm = compute(inp).sigcm
    return application.sig3max_slope(sigcm, 0.030, 50.0)
