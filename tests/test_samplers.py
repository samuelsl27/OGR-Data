"""Spec 008: samplers and overlays (no Qt)."""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import criteria_envelopes as ce
from ogr_data.core import samplers
from ogr_data.core.hoek_brown import HbInput, hoek_brown_constants
from ogr_data.core.models import defaults
from ogr_data.gui.themes import mpl_colors


def _ghb_curve(sigci=30.0, gsi=50.0, mi=10.0, d=0.0, sig3max=7.5, points=400):
    inp = HbInput(sigci=sigci, gsi=gsi, mi=mi, disturbance=d, sig3max=sig3max)
    mb, s, a = hoek_brown_constants(inp)
    sig3 = np.linspace(0.0, sig3max, points)
    sig1 = sig3 + inp.sigci * (mb * sig3 / inp.sigci + s) ** a
    return inp, mb, s, a, sig3, sig1


def test_stress_sample_interpolates_and_clips() -> None:
    x = np.array([0.0, 1.0, 2.0, 4.0])
    y = np.array([1.0, 3.0, 5.0, 9.0])
    s = samplers.sample(x, y, 1.5)
    assert abs(s.x - 1.5) < 1e-12 and abs(s.y - 4.0) < 1e-12
    assert samplers.sample(x, y, -3.0).x == 0.0
    assert samplers.sample(x, y, 99.0).x == 4.0


def test_instantaneous_mc_matches_analytic_tangent() -> None:
    # Classical Hoek-Brown with sigci=100, mb=1, s=1, a=0.5:
    # d1 = 1 + 0.5 * (sig3/100 + 1)^(-0.5).
    inp, mb, s, a, sig3, sig1 = _ghb_curve(sigci=100.0, gsi=100.0, mi=1.0, sig3max=30.0)
    # gsi=100 gives s=1, mb=mi=1, a=0.5 exactly.
    assert abs(s - 1.0) < 1e-12 and abs(a - 0.5) < 1e-12
    for xq in (0.0, 5.0, 15.0):
        d1 = samplers.hb_derivative(xq, inp.sigci, mb, s, a)
        sin_phi = (d1 - 1.0) / (d1 + 1.0)
        phi = math.degrees(math.asin(sin_phi))
        inst = samplers.instantaneous_mc(sig3, sig1, xq, slope=d1)
        # Friction angle is exact; cohesion is computed from the sampled
        # point of the (discretized) envelope curve.
        assert abs(inst.friction_deg - phi) < 1e-9
        assert abs(inst.slope - d1) < 1e-12
        sig1_q = float(np.interp(xq, sig3, sig1))
        assert abs(inst.point_y - sig1_q) < 1e-12
        intercept = sig1_q - d1 * xq
        c = intercept * (1.0 - sin_phi) / (2.0 * math.cos(math.radians(phi)))
        assert abs(inst.cohesion_mpa - c) < 1e-9


def test_instantaneous_mc_numeric_derivative_matches_analytic() -> None:
    inp, mb, s, a, sig3, sig1 = _ghb_curve()
    xq = 3.0
    analytic = samplers.instantaneous_mc(
        sig3, sig1, xq, slope=samplers.hb_derivative(xq, inp.sigci, mb, s, a)
    )
    numeric = samplers.instantaneous_mc(sig3, sig1, xq)
    assert abs(analytic.friction_deg - numeric.friction_deg) < 1e-3
    assert abs(analytic.cohesion_mpa - numeric.cohesion_mpa) < 1e-3


def test_mc_tangent_touches_envelope_in_principal_space() -> None:
    inp, mb, s, a, sig3, sig1 = _ghb_curve()
    xq = 4.0
    inst = samplers.instantaneous_mc(sig3, sig1, xq, slope=samplers.hb_derivative(xq, inp.sigci, mb, s, a))
    xr, yt = samplers.mc_tangent_principal(inst, np.array([xq]))
    assert abs(yt[0] - inst.point_y) < 1e-9
    # The HB envelope is concave in principal space (slope decreases with
    # sigma3), so the tangent stays on one side of the curve.
    xr2 = np.linspace(0.0, inp.sig3max, 200)
    _, yt2 = samplers.mc_tangent_principal(inst, xr2)
    env = xr2 + inp.sigci * (mb * xr2 / inp.sigci + s) ** a
    delta = env - yt2
    # Discretization: nearest node is ~0.02 MPa away, so allow a small band.
    assert np.all(delta <= 1e-4) or np.all(delta >= -1e-4)


def test_instantaneous_mc_shear_tangent_touches_barton_bandis() -> None:
    params = defaults("barton_bandis")
    params["jcs"] = 50000.0  # 50 MPa
    normal, shear = ce.shear_curve("barton_bandis", params, 20.0, points=800)
    xq = 5.0
    inst = samplers.instantaneous_mc_shear(normal, shear, xq)
    assert abs(inst.point_y - float(np.interp(xq, normal, shear))) < 1e-9
    _, tau_t = samplers.mc_tangent_shear(inst, np.array([xq]))
    assert abs(tau_t[0] - inst.point_y) < 1e-9
    assert 0.0 < inst.friction_deg < 90.0
    # Best-fit overlay conversion back to principal is the same MC line.
    xr = np.linspace(0.0, 20.0, 50)
    _, tau_line = samplers.mc_tangent_shear(inst, xr)
    _, sig1_line = samplers.mc_tangent_principal(inst, xr)
    sin_phi = math.sin(math.radians(inst.friction_deg))
    slope_p = (1.0 + sin_phi) / (1.0 - sin_phi)
    assert np.allclose(sig1_line, 2 * inst.cohesion_mpa * math.cos(math.radians(inst.friction_deg)) / (1.0 - sin_phi) + slope_p * xr)


def test_best_fit_mc_recovers_a_straight_line() -> None:
    c, phi = 0.35, 33.0
    normal = np.linspace(0.0, 10.0, 50)
    shear = c + normal * math.tan(math.radians(phi))
    inst = samplers.best_fit_mc(normal, shear)
    assert abs(inst.cohesion_mpa - c) < 1e-9
    assert abs(inst.friction_deg - phi) < 1e-9


def test_best_fit_mc_approximates_power_curve() -> None:
    params = defaults("power_curve")
    normal, shear = ce.shear_curve("power_curve", params, 5.0, points=200)
    inst = samplers.best_fit_mc(normal, shear)
    _, fit = samplers.mc_tangent_shear(inst, normal)
    assert np.sqrt(np.mean((fit - shear) ** 2)) < 0.05 * float(np.max(shear))


def test_mogi_line_ratio_and_brittle_ductile() -> None:
    x, y = samplers.mogi_line(7.5)
    assert np.allclose(y, 3.4 * x)
    # High GSI: brittle, envelope above Mogi's line over the whole range
    # (RocData 2004 p. 37).
    _, _, _, _, sig3_hi, sig1_hi = _ghb_curve(gsi=80.0)
    assert np.all(sig1_hi[1:] > 3.4 * sig3_hi[1:])
    # Low GSI: ductile, the envelope crosses Mogi's line from above (near
    # the origin sig1(0) > 0) to below at working confinement.
    _, _, _, _, sig3_lo, sig1_lo = _ghb_curve(gsi=10.0, sig3max=30.0)
    diff = sig1_lo - 3.4 * sig3_lo
    assert diff[0] > 0.0
    assert diff[-1] < 0.0
    work = sig3_lo > 2.0
    assert np.all(diff[work] < 0.0)


def test_mogi_color_defined_per_theme() -> None:
    for theme in ("light", "dark"):
        colors = mpl_colors(theme)
        assert "mogi" in colors
        assert colors["mogi"].startswith("#")


def test_sampler_window_offscreen() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
    app.processEvents()

    # The equivalent MC overlay is on by default for GHB.
    assert w._overlay_inst is not None

    # Stress sampler: click + drag on the principal plot.
    w._stress_sampler_act.setChecked(True)
    assert w._sampler_mode == "stress"
    w._on_plot_event("principal", "press", 3.0)
    w._on_plot_event("principal", "move", 4.0)
    w._on_plot_event("principal", "release", 4.0)
    msg = w.statusBar().currentMessage()
    assert "sigma3 = 4.0000 MPa" in msg and "[MC]" in msg
    assert w._principal._vline.get_visible()

    # A move without pressing must not sample.
    w._on_plot_event("principal", "move", 5.0)
    assert w.statusBar().currentMessage() == msg

    # MC sampler: instantaneous c/phi from the analytic derivative.
    w._mc_sampler_act.setChecked(True)
    assert w._sampler_mode == "mc"
    w._on_plot_event("principal", "press", 2.0)
    sig3, sig1 = w._curves["principal"]
    inst = samplers.instantaneous_mc(sig3, sig1, 2.0, slope=w._d1_func(2.0))
    msg = w.statusBar().currentMessage()
    assert f"c = {inst.cohesion_mpa:.4f} MPa" in msg
    assert f"phi = {inst.friction_deg:.2f} deg" in msg
    assert len(w._shear._tangent_line.get_xdata()) == 2
    assert w._shear._marker.get_offsets().size > 0

    # Mogi line overlay on the principal plot.
    w._overlay_mogi_act.setChecked(True)
    assert len(w._principal._mogi_line.get_xdata()) > 0
    w._overlay_mogi_act.setChecked(False)
    assert len(w._principal._mogi_line.get_xdata()) == 0

    # Shear-space criterion: sampler works on the shear plot.
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("barton_bandis"))
    w._stress_sampler_act.setChecked(True)
    w._on_plot_event("shear", "press", 5.0)
    assert "sigma_n = 5.0000 MPa" in w.statusBar().currentMessage()

    # MC sampler on a shear-space envelope.
    w._mc_sampler_act.setChecked(True)
    w._on_plot_event("shear", "press", 5.0)
    assert "c =" in w.statusBar().currentMessage()
    w._mc_sampler_act.setChecked(False)
    assert w._sampler_mode is None
