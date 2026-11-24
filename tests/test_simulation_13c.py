"""Spec 013, completion: NorSand, test fields of the reference program (K0), Cam-Clay options,
Softening-Hardening caps and tables, General Test and the Animation tab.

References: NorSand (Fraser River sand) and Modified Cam Clay tutorials of
the reference program (results read from their figures); FLAC3D 9.2
NorSand documentation; Softening-Hardening theory manual of the reference
program.
"""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import simulation as sm
from ogr_data.core.models import CRITERIA, defaults

# NorSand tutorial of the reference program, Fraser River sand (material and test dialogs)
FRS = dict(defaults("norsand"), m_tc=1.47, h0=75.0, chi_tc=3.2, n=0.5, hy=400.0, psi0=-0.025, gamma=1.2, ocr=1.1, **{"lambda": 0.06})
FRS_STIFF = {"g_ref": 40000.0, "p_ref": 395.0, "g_exp": 0.47, "ns_poisson": 0.15, "g_min": 1.0}


def _run(criterion, params, stiffness=None, **test):
    return sm.simulate(criterion, params, stiffness, sm.TestSimulation(**test))


# ------------------------------------------------------------------ NorSand


def test_norsand_fraser_river_tutorial() -> None:
    """Undrained triaxial at 395 kPa (tutorial "UTC"; reference program vs Jefferies' spreadsheet).

    Read from the tutorial figure: phase transformation (minimum p') at
    p' ~ 280 kPa, q ~ 380 kPa; pore pressure peak ~ 250 kPa near e_a = 0.02;
    at e_a = 0.2: q ~ 860 kPa, p' ~ 590 kPa (OGR about 10 % lower, documented).
    """

    r = _run("norsand", FRS, FRS_STIFF, test_type="triaxial", seepage="Undrained", confining=395.0, max_strain=0.2, steps=200)
    i = int(np.argmin(r.p))
    assert abs(r.p[i] / 280.0 - 1.0) < 0.05 and abs(r.q[i] / 380.0 - 1.0) < 0.05
    assert abs(r.pore_pressure.max() / 250.0 - 1.0) < 0.05 and 0.005 < r.axial_strain[np.argmax(r.pore_pressure)] < 0.03
    assert abs(r.q[-1] / 860.0 - 1.0) < 0.12 and abs(r.p[-1] / 590.0 - 1.0) < 0.12
    assert np.allclose(r.eps_v, 0.0, atol=1e-14)
    # initial void ratio from psi0 (spreadsheet: e0 = 0.816)
    assert abs(r.states[0]["e"] - 0.816) < 5e-4


def test_norsand_drained_dense_loose_and_lode() -> None:
    model = sm.NorSandModel(FRS, FRS_STIFF)
    assert abs(model.g(1.0) - 1.0) < 1e-12 and abs(model.g(-1.0) - 3.0 / (3.0 + 1.47)) < 1e-12
    # dense drained: peak above the critical state ratio, dilation, then towards M
    dense = _run("norsand", dict(FRS, psi0=-0.1), FRS_STIFF, test_type="triaxial", confining=100.0, max_strain=0.3)
    eta = dense.q / dense.p
    assert eta.max() > 1.47 and dense.eps_v[-1] < 0.0 and abs(eta[-1] - 1.47) < 0.1 * 1.47
    # loose undrained: static liquefaction (q peaks then drops)
    loose = _run("norsand", dict(FRS, psi0=0.08, ocr=1.0), FRS_STIFF, test_type="triaxial", seepage="Undrained", confining=200.0, max_strain=0.2)
    assert loose.q[-1] < 0.6 * loose.peak_q and loose.pore_pressure[-1] > 100.0
    # N = 0: the FLAC3D logarithmic surface
    ln = _run("norsand", dict(FRS, n=0.0), FRS_STIFF, test_type="triaxial", confining=100.0, max_strain=0.1)
    assert np.all(np.isfinite(ln.q)) and ln.peak_q > 0.0


# ------------------------------------- test fields of the reference program


def test_initial_effective_k0_and_general_test() -> None:
    mc = defaults("mohr_coulomb")
    r = _run("mohr_coulomb", mc, test_type="triaxial", confining=100.0, k0=0.8, max_strain=0.001, steps=1)
    assert np.allclose(r.stress[0, :3], [125.0, 100.0, 100.0])  # axial = lateral / K0
    # General Test, isotropic compression: elastic bulk modulus E / (3 (1 - 2 nu))
    g = _run("mohr_coulomb", mc, test_type="general", confining=100.0, max_strain=0.001, steps=4)
    K = 20000.0 / (3.0 * 0.4)
    assert abs((g.p[-1] - g.p[0]) / g.eps_v[-1] / K - 1.0) < 1e-9 and np.allclose(g.q, 0.0, atol=1e-9)
    # oedometric direction (1, 0, 0): elastic K0 = nu / (1 - nu)
    o = _run("mohr_coulomb", dict(mc, peak_cohesion=1000.0), test_type="general", strain_ratio=(1, 0, 0, 0, 0, 0), confining=100.0, max_strain=0.0005, steps=2)
    d = o.stress[-1, :3] - o.stress[0, :3]
    assert abs(d[1] / d[0] - 0.3 / 0.7) < 1e-9
    # round trip of the new fields
    t = sm.TestSimulation(test_type="general", k0=0.6, strain_ratio=(1, -0.5, -0.5, 0.2, 0, 0))
    assert sm.TestSimulation.from_dict(t.to_dict()).to_dict() == t.to_dict()


# ------------------------------------------------------- Cam-Clay options


def test_cam_clay_reference_options_and_tutorial() -> None:
    base = dict(defaults("modified_cam_clay"), critical_state_slope=1.2, specific_volume_unit_pressure=1.788, kappa=0.0077, **{"lambda": 0.066})
    # Modified Cam Clay tutorial, HOC (Po = 500 kPa, p0 = 100 kPa, 50 steps):
    # "rise up to near 300 kPa first, and then smoothly decline to around 200 kPa"
    hoc = dict(base, initial_consolidation="Preconsolidation Pressure (Po)", preconsolidation_stress=500.0)
    r = _run("modified_cam_clay", hoc, {"poisson": 0.3}, test_type="triaxial", confining=100.0, max_strain=0.2, steps=50)
    assert 270.0 < r.peak_q < 310.0 and abs(r.q[-1] - 200.0) < 15.0
    assert abs(r.states[0]["pc"] - 500.0) < 1e-9
    # Po below the initial state: readjusted onto the surface (manual §8.5)
    low = _run("modified_cam_clay", dict(hoc, preconsolidation_stress=50.0), {"poisson": 0.3}, test_type="triaxial", confining=100.0, max_strain=0.01)
    assert abs(low.states[0]["pc"] - 100.0) < 1e-9
    # Gamma reference: N = Gamma + (lambda - kappa) ln 2 (MCC, eq. 8.4) gives the same test
    gamma = 1.788 - (0.066 - 0.0077) * math.log(2.0)
    g = _run("modified_cam_clay", dict(hoc, volume_reference="Critical State Line (Gamma)", specific_volume_unit_pressure=gamma), {"poisson": 0.3},
             test_type="triaxial", confining=100.0, max_strain=0.2, steps=50)
    assert np.allclose(g.q, r.q)
    # Constant Shear Modulus: elastic q = 3 G e_q
    cg = _run("modified_cam_clay", dict(base, ocr=5.0), {"elastic_parameter": "Constant Shear Modulus", "shear_modulus": 5000.0},
              test_type="triaxial", seepage="Undrained", confining=100.0, max_strain=0.001, steps=2)
    assert abs(cg.q[1] / cg.eps_q[1] / 15000.0 - 1.0) < 1e-6


# ------------------------------------------- Softening-Hardening completion


def test_softening_hardening_tabular_and_caps() -> None:
    sh = dict(defaults("softening_hardening"), peak_cohesion=0.0, peak_friction=43.5)
    table = [[0.0, 0.0, 0.0], [0.02, 43.5, 0.0], [0.1, 36.0, 0.0], [0.3, 36.0, 0.0]]
    tab = dict(sh, cone_hardening_type="Tabular", cone_hardening_table=table)
    r = _run("softening_hardening", tab, {"young": 300000.0, "poisson": 0.35}, test_type="triaxial", confining=300.0, max_strain=0.2)
    n36 = (1 + math.sin(math.radians(36))) / (1 - math.sin(math.radians(36)))
    assert r.peak_q > 1.3 * r.q[-1] and abs(r.q[-1] - (n36 - 1.0) * 300.0) < 1e-3  # softens to the table residual
    # vertical cap with Cam-Clay type hardening, isotropic compression (General Test)
    cap = dict(sh, peak_cohesion=10.0, cap_type="Vertical", initial_mean_stress=200.0, lambda_kappa=0.05)
    H = {"young": 180000.0, "poisson": 0.35}
    v = _run("softening_hardening", cap, H, test_type="general", confining=100.0, max_strain=0.02, steps=200)
    K = 180000.0 / (3.0 * 0.3)
    ev_p = v.eps_v[-1] - (v.p[-1] - 100.0) / K
    assert abs(v.p[-1] / (200.0 * math.exp(ev_p / 0.05)) - 1.0) < 0.01  # pc = pc0 exp(e_v^p / (lambda - kappa))
    assert abs(v.p[-1] - v.states[-1]["pc"]) / v.p[-1] < 0.01
    # rigid cap (Lambda Kappa = 0) and tabular cap hardening
    rigid = _run("softening_hardening", dict(cap, lambda_kappa=0.0), H, test_type="general", confining=100.0, max_strain=0.02)
    assert abs(rigid.p[-1] - 200.0) < 1e-6
    tcap = dict(cap, cap_hardening_type="Tabular", cap_hardening_table=[[0.0, 200.0], [0.05, 400.0]])
    t = _run("softening_hardening", tcap, H, test_type="general", confining=100.0, max_strain=0.01, steps=200)  # e_v^p < 0.05: inside the table
    ev_p = t.eps_v[-1] - (t.p[-1] - 100.0) / K
    assert abs(t.p[-1] - (200.0 + 4000.0 * ev_p)) < 5.0
    # elliptical cap: same as the vertical one on the isotropic axis; stress on the drawn surface
    e = _run("softening_hardening", dict(cap, cap_type="Elliptical"), H, test_type="general", confining=100.0, max_strain=0.02, steps=200)
    assert abs(e.p[-1] / v.p[-1] - 1.0) < 1e-6
    fields = {f.key: f for f in CRITERIA["softening_hardening"].fields}
    assert fields["cone_hardening_table"].kind == "table" and fields["cap_hardening_table"].stress_columns == (False, True)


def test_yield_surface_for_animation() -> None:
    cases = [
        ("mohr_coulomb", defaults("mohr_coulomb"), None),
        ("drucker_prager", defaults("drucker_prager"), None),
        ("modified_cam_clay", defaults("modified_cam_clay"), None),
        ("cam_clay", defaults("cam_clay"), None),
        ("norsand", FRS, FRS_STIFF),
        ("softening_hardening", dict(defaults("softening_hardening"), cap_type="Elliptical", initial_mean_stress=500.0), None),
    ]
    for criterion, params, stiff in cases:
        r = _run(criterion, params, stiff, test_type="triaxial", confining=100.0, max_strain=0.05)
        for step in (len(r.q) // 2, len(r.q) - 1):
            if not r.yielded[step]:
                continue
            p, q = sm.yield_surface_pq(r, step)
            assert len(p) > 10
            assert abs(np.interp(r.p[step], p, q) - r.q[step]) < 1e-3 * max(1.0, r.q[step]), (criterion, step)
        assert len(r.states) == len(r.q)


# ------------------------------------------------------------------- GUI


def test_window_stiffness_tables_and_animation() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        w._add_material("soil")
        panel = w._stiffness_box
        # stiffness rows follow the model (Stiffness tab of the reference program)
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("norsand"))
        assert panel.title() == "Stiffness (NorSand)" and panel.form.isRowVisible(panel.spins["g_ref"])
        assert not panel.form.isRowVisible(panel._young_row)
        panel.spins["g_ref"].setValue(40000.0)
        panel.spins["p_ref"].setValue(395.0)
        assert w._current_material().stiffness["p_ref"] == 395.0
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("modified_cam_clay"))
        assert panel.title() == "Stiffness (CamClay Isotropic)" and panel.form.isRowVisible(panel.spins["poisson"])
        panel.elastic_parameter.setCurrentText("Constant Shear Modulus")
        assert panel.form.isRowVisible(panel.spins["shear_modulus"]) and not panel.form.isRowVisible(panel.spins["poisson"])
        # MPa display rescales the stress rows only
        w._set_stress_unit("MPa")
        assert abs(panel.spins["p_ref"].value() - 0.395) < 1e-9 and w._current_material().stiffness["p_ref"] == 395.0
        w._set_stress_unit("kPa")
        # table parameter: editor round trip in display units
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("softening_hardening"))
        table = w._widgets["cone_hardening_table"]
        dialog, editor = table.editor()
        try:
            editor.set_rows([[0.0, 0.0, 0.0], [0.05, 30.0, 5.0]])
            table.setValue(editor.rows())
        finally:
            dialog.deleteLater()
        assert w._params()["cone_hardening_table"] == [[0.0, 0.0, 0.0], [0.05, 30.0, 5.0]] and "2 rows" in table.text()
        # animation: a visible test, step marks on the four graphs and the yield surface in q-p
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("modified_cam_clay"))
        w.set_test_simulations([sm.TestSimulation(name="TC", test_type="triaxial", confining=200.0, max_strain=0.1)])
        app.processEvents()
        anim = w._animation
        assert anim.material.count() == 1 and anim.material.currentText().endswith("- TC")
        anim.set_step(50)
        (x, y), (sx, sy) = w._path_canvases["pq"].animation_data()
        result = anim._current()[1]
        assert abs(x[0] * 1000.0 - result.p[50]) < 1e-9 and abs(y[0] * 1000.0 - result.q[50]) < 1e-9 and len(sx) > 10
        (ax, ay), _ = w._path_canvases["axial"].animation_data()
        assert abs(ax[0] - result.axial_strain[50]) < 1e-12
        anim.start()
        assert anim.timer.isActive()
        for _ in range(200):
            anim._tick()
        assert not anim.timer.isActive() and anim.slider.value() == len(result.q) - 1
        w.set_test_simulations([])
        assert anim.material.count() == 0 and not anim.play.isEnabled()
    finally:
        w.deleteLater()
