"""Spec 013 (phase 13a): test simulations with elastoplastic MC / HB / GHB."""

from __future__ import annotations

import math

import numpy as np

from ogr_data.core import project
from ogr_data.core import simulation as sm
from ogr_data.core.hoek_brown import HbInput, hoek_brown_constants
from ogr_data.core.models import defaults

MC = defaults("mohr_coulomb")  # c = 10.5 kPa, phi = 35 deg, psi = 0 (RSData defaults)


def _n(deg: float) -> float:
    s = math.sin(math.radians(deg))
    return (1.0 + s) / (1.0 - s)


def _run(params=MC, criterion="mohr_coulomb", stiffness=None, **test):
    return sm.simulate(criterion, params, stiffness, sm.TestSimulation(**test))


def test_triaxial_cd_mohr_coulomb_plateau() -> None:
    """Acceptance 13a: drained triaxial on MC, q plateau at the analytic q_f (1 %)."""

    r = _run(test_type="triaxial", confining=100.0)
    n = _n(35.0)
    q_f = (n - 1.0) * 100.0 + 2.0 * 10.5 * math.sqrt(n)
    assert abs(r.peak_q - q_f) / q_f < 0.01 and abs(r.q[-1] - q_f) / q_f < 1e-6
    assert abs(sm.failure_deviator("mohr_coulomb", MC, r.test) - q_f) < 1e-9
    # 100 steps + start; lateral effective stress kept at the confining stress
    assert r.stress.shape == (101, 3) and np.allclose(r.stress[:, 1:], 100.0, atol=1e-6)
    # elastic branch: slope E (axial stress vs axial strain under constant lateral stress)
    assert abs((r.axial_stress[1] - r.axial_stress[0]) / r.axial_strain[1] - 20000.0) < 1e-6
    # p' rises along the 1:3 drained path, q = 3 (p' - sigma_c)
    assert np.allclose(r.q, 3.0 * (r.p - 100.0), atol=1e-6)
    # psi = 0: no plastic volume change, the volumetric strain stays at its value at failure
    assert np.all(r.yielded[-10:]) and abs(r.eps_v[-1] - r.eps_v[-10]) < 1e-12
    assert np.all(r.pore_pressure == 0.0)


def test_mohr_coulomb_other_tests_against_closed_forms() -> None:
    n = _n(35.0)
    sc = 2.0 * 10.5 * math.sqrt(n)
    # uniaxial compression and tension
    assert abs(_run(test_type="uniaxial").peak_q - sc) < 1e-6
    tension = _run(test_type="uniaxial", loading="Tension")
    assert abs(tension.axial_stress.min() + 2.0 * 10.5 / math.sqrt(n)) < 1e-6
    # triaxial extension: the lateral stress is major, sigma_a = (sigma_c - sc) / N
    ext = _run(test_type="triaxial", loading="Tension", confining=100.0)
    assert abs(ext.axial_stress[-1] - (100.0 - sc) / n) < 1e-6 and ext.axial_strain[-1] < 0.0
    # undrained triaxial: p' constant while elastic, q_f = 3 [(N-1) sc' + sc] / (2 + N), u = p0 - p'
    und = _run(test_type="triaxial", seepage="Undrained", confining=100.0)
    q_u = 3.0 * ((n - 1.0) * 100.0 + sc) / (2.0 + n)
    assert abs(und.peak_q - q_u) < 1e-6 and np.allclose(und.eps_v, 0.0, atol=1e-15)
    assert np.allclose(und.p, 100.0, atol=1e-6)
    assert abs(und.pore_pressure[-1] - (100.0 - und.stress[-1, 2])) < 1e-9 and und.pore_pressure[-1] > 0.0
    # biaxial (plane strain): eps_2 = 0, sigma'_3 = confining; failure on sigma'1 = N sigma'3 + sc
    bi = _run(test_type="biaxial", confining=100.0)
    assert np.allclose(bi.strain[:, 1], 0.0) and abs(bi.stress[-1, 0] - (n * 100.0 + sc)) < 1e-6
    assert abs(bi.stress[-1, 2] - 100.0) < 1e-6 and 100.0 < bi.stress[-1, 1] < bi.stress[-1, 0]  # sigma2 intermediate


def test_dilatancy_brittle_and_cyclic() -> None:
    # dilation angle psi: plastic d(eps_v)/d(eps_a) = 1 - N_psi on the triaxial edge (compression +)
    r = _run(dict(MC, dilation=10.0), test_type="triaxial")
    slope = (r.eps_v[-1] - r.eps_v[-2]) / (r.axial_strain[-1] - r.axial_strain[-2])
    assert abs(slope - (1.0 - _n(10.0))) < 1e-6
    # Set Residual to Peak off: elastic-brittle-plastic, q falls to the residual strength
    brittle = dict(MC, set_residual_to_peak=False, residual_cohesion=0.0, residual_friction=30.0)
    r = _run(brittle, test_type="triaxial", confining=100.0)
    assert abs(r.q[-1] - (_n(30.0) - 1.0) * 100.0) < 1e-6 and r.peak_q < 309.36
    # cyclic: 0 -> max -> 0 per cycle, Number of Steps per half cycle
    test = sm.TestSimulation(test_type="triaxial", max_strain=0.01, steps=10, cyclic=True, cycles=2)
    history = test.axial_history()
    assert len(history) == 40 and history[9] == 0.01 and history[19] == 0.0 and history[-1] == 0.0
    r = sm.simulate("mohr_coulomb", MC, None, test)
    assert r.axial_strain[-1] == 0.0 and len(r.q) == 41


def test_hoek_brown_and_generalized() -> None:
    stiff = {"young": 2.0e7, "poisson": 0.25}
    ghb = defaults("generalized_hoek_brown")
    mb, s, a = hoek_brown_constants(HbInput(sigci=100.0, gsi=50.0, mi=10.0, disturbance=0.0))
    for confining in (0.0, 1000.0, 10000.0):
        test_type = "uniaxial" if confining == 0.0 else "triaxial"
        r = _run(ghb, "generalized_hoek_brown", stiff, test_type=test_type, confining=confining, max_strain=0.01)
        q_f = 100000.0 * (mb * confining / 100000.0 + s) ** a
        assert abs(r.q[-1] - q_f) / q_f < 1e-6, (confining, r.q[-1], q_f)
        # GHB flows without plastic volume change (no dilation field in RSData)
        assert abs(r.eps_v[-1] - r.eps_v[-5]) < 1e-12
    # classic Hoek-Brown (a = 0.5) with the dilation parameter as mb of the potential
    hb = dict(defaults("hoek_brown"), mb=5.0, s=0.01)
    r = _run(hb, "hoek_brown", stiff, test_type="triaxial", confining=5000.0, max_strain=0.01)
    assert abs(r.q[-1] - 100000.0 * math.sqrt(5.0 * 0.05 + 0.01)) < 1e-4
    dilatant = _run(dict(hb, dilation_parameter=5.0), "hoek_brown", stiff, test_type="triaxial", confining=5000.0, max_strain=0.01)
    assert dilatant.eps_v[-1] < r.eps_v[-1]  # associated flow dilates


def test_errors_and_unsupported() -> None:
    for kwargs, message in (
        ({"test_type": "simple_shear"}, "013b"),
        ({"test_type": "general"}, "013b"),
        ({"max_strain": 0.0}, "Maximum Strain"),
    ):
        try:
            _run(**kwargs)
        except sm.SimulationError as exc:
            assert message in str(exc), exc
        else:
            raise AssertionError(kwargs)
    for criterion in ("cam_clay", "norsand", "barton_bandis"):
        try:
            sm.simulate(criterion, defaults(criterion), None, sm.TestSimulation())
        except sm.SimulationError as exc:
            assert "13b" in str(exc)
        else:
            raise AssertionError(criterion)
    try:
        _run(stiffness={"poisson": 0.5})
    except sm.SimulationError as exc:
        assert "Poisson" in str(exc)
    else:
        raise AssertionError("poisson 0.5 accepted")


def test_project_round_trip_and_templates() -> None:
    proj = project.Project.new()
    soil = proj.materials[proj.add("soil")]
    assert [t.name for t in soil.test_simulations] == ["Test 1"]  # "Material Model + Test, Stress Path"
    assert soil.stiffness == {"type": "Linear Isotropic", "poisson": 0.3, "young": 20000.0}
    soil.stiffness["young"] = 50000.0
    soil.test_simulations.append(sm.TestSimulation(name="CU", test_type="triaxial", seepage="Undrained", confining=200.0, cyclic=True, cycles=3))
    back = project.Project.from_dict(proj.to_dict())
    assert back.materials[1].stiffness["young"] == 50000.0
    assert [t.to_dict() for t in back.materials[1].test_simulations] == [t.to_dict() for t in soil.test_simulations]
    # files without the spec 013 keys load with the defaults
    data = proj.to_dict()
    del data["materials"][1]["stiffness"], data["materials"][1]["test_simulations"]
    old = project.Project.from_dict(data).materials[1]
    assert old.stiffness["young"] == 20000.0 and old.test_simulations == []
    assert sm.TestSimulation.from_dict({"test_type": "bogus", "steps": 0}).test_type == "uniaxial"


def test_window_tests_dialog_compute_and_graphs() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow
    from ogr_data.gui.simulation_dialog import TestSimulationsDialog

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        w._add_material("soil")
        w.set_stress_paths([])
        material = w._current_material()
        # stiffness edited in the sidebar is stored on the material
        w._young.setValue(40000.0)
        w._poisson.setValue(0.25)
        assert material.stiffness["young"] == 40000.0 and material.stiffness["poisson"] == 0.25
        dlg = TestSimulationsDialog(w, material.name, material.test_simulations, "kPa")
        try:
            assert dlg._list.count() == 1
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("triaxial"))
            assert dlg._form.isRowVisible(dlg._confining)
            dlg._confining.setValue(150.0)
            dlg.add_item()
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("simple_shear"))
            assert "013b" in dlg._note.text() and not dlg._form.isRowVisible(dlg._confining)
            dlg.store_current()
            items = dlg.items
        finally:
            dlg.deleteLater()
        assert [(t.test_type, t.confining) for t in items] == [("triaxial", 150.0), ("simple_shear", 100.0)]
        w.set_test_simulations(items)
        app.processEvents()
        problems = w.compute(report_problems=False)
        assert len(problems) == 1 and "Test 2" in problems[0]
        # the triaxial test is drawn in the four Stress Path Graphs and in sigma'1-sigma'3
        n = _n(35.0)
        q_f = (n - 1.0) * 150.0 + 2.0 * 10.5 * math.sqrt(n)
        x, y = w._path_canvases["pq"]._lines[0].get_data()
        assert abs(y.max() * 1000.0 - q_f) < 1e-6 and abs(x[0] * 1000.0 - 150.0) < 1e-9
        assert all(len(c._lines) == 1 for c in w._path_canvases.values())
        assert w._path_canvases["axial"]._lines[0].get_marker() == "None"
        assert len(w._principal._layers) == 1
        # tree child, visibility toggle hides it
        child = w._tree.topLevelItem(w._current).child(0)
        assert child.data(0, 256) == ("test", 0)
        from PySide6.QtCore import Qt

        child.setCheckState(0, Qt.CheckState.Unchecked)
        assert not material.test_simulations[0].visible and all(c._lines == [] for c in w._path_canvases.values())
        child.setCheckState(0, Qt.CheckState.Checked)
        # editing the material recomputes (cache keyed on the inputs)
        w._widgets["peak_friction"].setValue(30.0)
        y = w._path_canvases["pq"]._lines[0].get_data()[1]
        q30 = (_n(30.0) - 1.0) * 150.0 + 2.0 * 10.5 * math.sqrt(_n(30.0))
        assert abs(y.max() * 1000.0 - q30) < 1e-6
        # stress unit change rescales the Young's modulus display, not the stored value
        w._set_stress_unit("MPa")
        assert abs(w._young.value() - 40.0) < 1e-9 and material.stiffness["young"] == 40000.0
        w._set_stress_unit("kPa")
        w._delete_child("test", 0)
        assert [t.name for t in w._current_material().test_simulations] == ["Test 2"]
    finally:
        w.deleteLater()
