"""Specs 012 and 021: failure states and stress paths.

Reference numbers come from the verification of the reference program
(private references, 07_estados_y_rutas_verificado.md).
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np

from ogr_data.core import project
from ogr_data.core import states as st
from tests._references import roc_examples

EXAMPLES = roc_examples()  # found by search (spec 027)
EA = [0.0, 0.01, 0.02]


# ------------------------------------------------------------ table text


def test_parse_rows_variants() -> None:
    # Excel (tab) with header and decimal comma; Exclude flag column
    text = "Sigma3\tSigma1\tExclude\n0\t30,5\t0\n5\t60\tx\n\n10\t80\n"
    assert st.parse_rows(text, 2, flag_column=True) == [(0.0, 30.5, False), (5.0, 60.0, True), (10.0, 80.0, False)]
    assert st.parse_rows("1;2,5\n3;4\n", 2) == [(1.0, 2.5), (3.0, 4.0)]
    assert st.parse_rows("a,b\n1,2.03849095\r\n2,1.5\r\n", 2) == [(1.0, 2.03849095), (2.0, 1.5)]
    assert st.parse_rows("1 2 3\n4 5 6\nnote\n", 3) == [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]
    assert st.parse_rows("1\n", 2) == []


def test_official_example_csv_reads() -> None:
    rows = st.read_rows_csv(EXAMPLES / "GHB Lab Test Data.csv")
    assert len(rows) >= 5 and rows[0] == (1.0, 25.16631527)


def test_csv_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "points.csv"
        st.write_rows_csv(path, ["Sigma3 (kPa)", "Sigma1 (kPa)", "Exclude"], [(0.0, 30.0, False), (5.0, 61.25, True)])
        assert path.read_text(encoding="utf-8").splitlines()[0] == "Sigma3 (kPa),Sigma1 (kPa),Exclude"
        assert st.read_rows_csv(path, 2, flag_column=True) == [(0.0, 30.0, False), (5.0, 61.25, True)]


def test_mohr_circle_geometry() -> None:
    normal, shear = st.mohr_circle(2.0, 10.0)
    assert math.isclose(normal[0], 2.0) and math.isclose(normal[-1], 10.0)
    assert np.allclose((normal - 6.0) ** 2 + shear**2, 16.0) and np.all(shear >= -1e-12)


# --------------------------------------------------------- failure states


def test_failure_state_types_and_columns() -> None:
    # Test Type combo of the reference program (capture 70) and columns
    assert list(st.FAILURE_TEST_TYPES.values()) == ["Triaxial Test", "Direct Shear Test", "General Test"]
    assert st.FailureState().columns == ("Sigma3", "Sigma1")
    assert st.FailureState(test_type="direct_shear").columns == ("SigmaN", "Tau")
    assert st.FailureState(test_type="general").columns == ("StressXX", "StressYY", "StressZZ", "TauXY", "TauYZ", "TauXZ")
    assert st.FailureState(test_type="simple_shear").test_type == "triaxial"  # not a state type of the reference program


def test_exclude_and_principal_points() -> None:
    state = st.FailureState(points=[st.TestPoint(0, 40.3), st.TestPoint(100, 409), st.TestPoint(300, 1500, True)])
    sig3, sig1 = state.principal_points()
    assert list(sig3) == [0.0, 100.0] and list(sig1) == [40.3, 409.0]  # excluded point dropped
    assert state.shear_points() is None
    direct = st.FailureState(test_type="direct_shear", points=[st.TestPoint(100, 80), st.TestPoint(200, 150, True)])
    assert direct.principal_points() is None
    n, t = direct.shear_points()
    assert list(n) == [100.0] and list(t) == [80.0]
    # general: principal stresses are the eigenvalues of the stress tensor
    general = st.FailureState(test_type="general", tensors=[(100, 100, 200, 30, 0, 0), (50, 80, 300, 0, 0, 0)])
    sig3, sig1 = general.principal_points()
    assert np.allclose(sig3, [70.0, 50.0]) and np.allclose(sig1, [200.0, 300.0])


def test_exclude_reproduces_the_reference_calibration() -> None:
    # reference program: MC calibration (Levenberg-Marquardt, vertical, absolute) with the
    # outlier (300; 1500) excluded gives c = 10.4788 kPa, phi = 34.9894 deg.
    from ogr_data.core import fitting

    state = st.FailureState(points=[st.TestPoint(0, 40.3), st.TestPoint(100, 409), st.TestPoint(200, 778), st.TestPoint(300, 1500, True)])
    sig3, sig1 = state.principal_points()
    result = fitting.fit_mohr_coulomb_triaxial(sig3 / 1000.0, sig1 / 1000.0)
    assert abs(result.parameters["cohesion_mpa"] * 1000.0 - 10.4788) < 1e-3
    assert abs(result.parameters["friction_deg"] - 34.9894) < 1e-3


def test_legacy_residual_points_become_a_state() -> None:
    legacy = [{"name": "S", "peak": [[0, 30, False]], "residual": [[5, 40, False]], "color": "#800000"}]
    states = st.failure_states_from_dicts(legacy)
    assert [s.name for s in states] == ["S", "S (residual)"]
    assert states[0].points == [st.TestPoint(0, 30)] and states[1].points == [st.TestPoint(5, 40)]
    assert states[1].color != states[0].color


# ----------------------------------------------------------- stress paths


def test_path_columns_match_the_reference() -> None:
    def cols(**kw):
        return st.StressPath(**kw).columns()

    assert list(st.PATH_TEST_TYPES) == ["uniaxial", "triaxial", "biaxial", "simple_shear"]
    assert cols(test_type="uniaxial") == ("EpsilonZZ", "SigmaZZ", "EpsilonXX")
    assert cols(test_type="uniaxial", strain_type="Volumetric") == ("EpsilonZZ", "SigmaZZ", "EpsilonV")
    assert cols(test_type="uniaxial", strain_type="None") == ("EpsilonZZ", "SigmaZZ", "EpsilonV")
    for test_type in ("triaxial", "biaxial"):
        assert cols(test_type=test_type) == ("EpsilonZZ", "SigmaXX", "EpsilonV")
        assert cols(test_type=test_type, loading="Axial") == ("EpsilonZZ", "SigmaZZ", "EpsilonV")
        assert cols(test_type=test_type, loading="None") == ("EpsilonZZ", "EpsilonV")
        assert cols(test_type=test_type, loading="Axial", seepage="Undrained") == ("EpsilonZZ", "SigmaZZ", "Pore Water Pressure")
        assert cols(test_type=test_type, loading="Lateral", seepage="Undrained") == ("EpsilonZZ", "SigmaXX", "Pore Water Pressure")
        assert cols(test_type=test_type, loading="None", seepage="Undrained") == ("EpsilonZZ", "Pore Water Pressure")
    assert cols(test_type="simple_shear") == ("SigmaZY", "EpsilonZY", "EpsilonZZ")
    assert st.StressPath(test_type="triaxial", loading="Axial", seepage="Undrained").stress_columns() == (False, True, True)


def test_defaults_and_legacy_values() -> None:
    path = st.StressPath()
    assert (path.loading, path.strain_type, path.lateral_stress, path.k0) == ("Lateral", "Lateral", 100.0, 1.0)
    assert st.StressPath(strain_type="Volumatric").strain_type == "Volumetric"  # spelling of the reference program
    assert st.StressPath.from_dict({"loading": "Compression"}).loading == "Lateral"
    assert st.StressPath.from_dict({"test_type": "general"}).test_type == "uniaxial"
    assert st.StressPath(test_type="bogus", seepage="x").seepage == "Drained"


def _tx(sigma_zz, lateral=100.0, k0=1.0, last=(0.0, 0.0, 0.0), seepage="Drained"):
    steps = [[a, s, v] for a, s, v in zip(EA, sigma_zz, last)]
    return st.StressPath(test_type="triaxial", loading="Axial", seepage=seepage, lateral_stress=lateral, k0=k0, steps=steps)


def test_triaxial_axial_matches_the_reference_numbers() -> None:
    inv = _tx([100, 200, 300]).invariants()  # TX_Axial_K1
    assert np.allclose(inv.sigma_a, [100, 200, 300])
    assert np.allclose(inv.p, [100, 400 / 3, 500 / 3]) and np.allclose(inv.q, [0, 100, 200])
    assert np.allclose(inv.eps_v, 0) and np.allclose(inv.eps_q, EA)
    # K0 has no effect (TX_Axial_K05 == TX_Axial_K1)
    assert np.allclose(_tx([100, 200, 300], k0=0.5).invariants().p, inv.p)
    # sigma'h0 = 150: q unsigned (50 / 50 / 150)
    inv150 = _tx([100, 200, 300], lateral=150.0, k0=0.5).invariants()
    assert np.allclose(inv150.p, [400 / 3, 500 / 3, 200]) and np.allclose(inv150.q, [50, 50, 150])
    # undrained, u = 0 / 10 / 20: effective axial 100 / 190 / 280
    und = _tx([100, 200, 300], last=(0, 10, 20), seepage="Undrained").invariants()
    assert np.allclose(und.sigma_a, [100, 190, 280]) and np.allclose(und.p, [100, 370 / 3, 440 / 3])
    assert np.allclose(und.q, [0, 100, 200]) and np.allclose(und.eps_v, 0)


def test_uniaxial_strains_and_shear_points() -> None:
    vol = st.StressPath(test_type="uniaxial", strain_type="Volumetric", steps=[[a, s, v] for a, s, v in zip(EA, [0, 100, 200], [0, 0.004, 0.008])])
    inv = vol.invariants()
    assert np.allclose(inv.eps_q, [0, 0.01 - 0.004 / 3, 0.02 - 0.008 / 3])  # reference program: 0.00867, 0.01733
    assert np.allclose(inv.sigma_r, 0)  # OGR: uniaxial radial stress is zero
    lat = st.StressPath(test_type="uniaxial", steps=[[0.03, 600.0, -0.01]])
    inv = lat.invariants()
    assert np.allclose(inv.eps_v, 0.01) and np.allclose(inv.q, 600)
    s, t = lat.shear_path()
    assert np.allclose(s, 300) and np.allclose(t, 300)
    sig3, sig1 = lat.principal_path()
    assert np.allclose(sig3, 0) and np.allclose(sig1, 600)


def test_unverified_configurations_are_not_drawn() -> None:
    steps = [[0.0, 100.0, 0.0]]
    for kw in ({"loading": "Lateral"}, {"loading": "None"}):
        assert st.StressPath(test_type="triaxial", steps=steps, **kw).invariants() is None
    assert st.StressPath(test_type="biaxial", loading="Axial", steps=steps).invariants() is None
    assert st.StressPath(test_type="simple_shear", steps=steps).invariants() is None
    assert st.StressPath(test_type="triaxial", loading="Axial").invariants() is None  # empty


def test_templates_and_project_round_trip() -> None:
    proj = project.Project.new()
    rock = proj.materials[proj.add("rock")]
    soil = proj.materials[proj.add("soil")]
    assert [s.name for s in rock.failure_states] == ["State 1"] and [p.name for p in soil.stress_paths] == ["Path 1"]
    rock.failure_states[0].points = [st.TestPoint(0.0, 30000.0), st.TestPoint(5000.0, 61000.0, True)]
    rock.failure_states.append(st.FailureState("Tensor", "#123456", "s", "general", tensors=[(1, 2, 3, 4, 5, 6)], visible=False))
    soil.stress_paths[0] = _tx([100, 200, 300], seepage="Undrained", last=(0, 10, 20))
    dup = proj.materials[proj.duplicate(1)]
    dup.failure_states[0].points[0].y = 1.0
    assert rock.failure_states[0].points[0].y == 30000.0
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "states.ogrdata"
        project.save_project(path, proj)
        back = project.load_project(path)
    r = back.materials[1]
    assert r.failure_states[0].points == [st.TestPoint(0.0, 30000.0), st.TestPoint(5000.0, 61000.0, True)]
    assert r.failure_states[1] == st.FailureState("Tensor", "#123456", "s", "general", tensors=[(1, 2, 3, 4, 5, 6)], visible=False)
    assert back.materials[3].stress_paths[0] == soil.stress_paths[0]
    # first-012 files: peak/residual split, steps kept
    data = proj.to_dict()
    data["materials"][1]["failure_states"] = [{"name": "Old", "peak": [[0, 1, False]], "residual": [[2, 3, False]]}]
    assert [s.name for s in project.Project.from_dict(data).materials[1].failure_states] == ["Old", "Old (residual)"]


# ------------------------------------------------------------------- GUI


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._set_stress_unit("kPa")
    app.processEvents()
    return app, w


def _headers(table) -> list[str]:
    return [table.table.horizontalHeaderItem(c).text() for c in range(table.table.columnCount())]


def test_failure_states_dialog_and_plot() -> None:
    from PySide6.QtCore import Qt

    from ogr_data.gui.states_dialog import FailureStatesDialog

    app, w = _window()
    try:
        w._add_material("rock")
        material = w._current_material()
        dlg = FailureStatesDialog(w, material.name, material.failure_states, "MPa")
        try:
            assert _headers(dlg._points) == ["Sigma3 (MPa)", "Sigma1 (MPa)", "Exclude"]
            assert dlg._points.paste_text("Sigma3\tSigma1\n0\t30\n5\t61,5\n10\t100\t1\n") == 3
            # second state: direct shear, then a general (tensor) state
            dlg.add_item()
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("direct_shear"))
            assert _headers(dlg._points) == ["SigmaN (MPa)", "Tau (MPa)", "Exclude"]
            dlg._points.paste_text("0.1\t0.08\n")
            dlg.add_item()
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("general"))
            assert _headers(dlg._points) == [f"{c} (MPa)" for c in st.GENERAL_COLUMNS]  # no Exclude
            dlg._points.paste_text("0.1\t0.1\t0.2\t0.03\t0\t0\n")
            dlg._list.setCurrentRow(0)
            assert dlg._points.table.rowCount() == 3 and dlg._points.table.columnCount() == 3
            dlg._points.table.item(0, 1).setText("abc")
            try:
                dlg.store_current()
            except ValueError as exc:
                assert "row 1" in str(exc)
            else:
                raise AssertionError("expected ValueError")
            dlg._points.table.item(0, 1).setText("30")
            with tempfile.TemporaryDirectory() as tmp:
                csv_path = Path(tmp) / "points.csv"
                dlg._points.export_csv(str(csv_path))
                assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "Sigma3 (MPa),Sigma1 (MPa),Exclude"
                dlg._points.set_rows([])
                assert dlg._points.import_csv(str(csv_path)) == 3
            dlg.accept()
            items = dlg.items
        finally:
            dlg.deleteLater()
        tri, direct, general = items
        assert tri.points == [st.TestPoint(0.0, 30000.0), st.TestPoint(5000.0, 61500.0), st.TestPoint(10000.0, 100000.0, True)]
        assert direct.points == [st.TestPoint(100.0, 80.0)]
        assert general.test_type == "general" and np.allclose(general.tensors[0], (100, 100, 200, 30, 0, 0))
        assert material.failure_states[0].points == []  # dialog edits copies
        w.set_failure_states(items)
        app.processEvents()
        item = w._tree.topLevelItem(1)
        assert [item.child(i).text(0) for i in range(item.childCount())] == ["State 1", "State 2", "State 3"]
        # principal: triaxial (2 included points) + general (1 point)
        p_layers = w._principal._layers
        assert len(p_layers) == 2
        assert list(p_layers[0].get_xdata()) == [0.0, 5.0] and list(p_layers[0].get_ydata()) == [30.0, 61.5]
        assert np.allclose(p_layers[1].get_xdata(), [0.07]) and np.allclose(p_layers[1].get_ydata(), [0.2])
        # shear: 3 Mohr circles (excluded point dropped) + the direct shear point
        circles = [l for l in w._shear._layers if l.get_linestyle() != "None"]
        points = [l for l in w._shear._layers if l.get_linestyle() == "None"]
        assert len(circles) == 3 and len(points) == 1 and list(points[0].get_xdata()) == [0.1]
        legend = [t.get_text() for t in w._principal.axes.get_legend().get_texts()]
        assert "Rock: State 1" in legend and "Rock: State 3" in legend
        item.child(0).setCheckState(0, Qt.CheckState.Unchecked)
        app.processEvents()
        assert len(w._principal._layers) == 1
        item.setCheckState(0, Qt.CheckState.Unchecked)
        app.processEvents()
        assert w._principal._layers == [] and w._shear._layers == []
    finally:
        w.deleteLater()


def test_stress_paths_dialog_and_plot() -> None:
    from ogr_data.gui.states_dialog import StressPathsDialog

    app, w = _window()
    try:
        w._add_material("soil")
        w.set_test_simulations([])  # spec 013: only the stress paths are checked here
        material = w._current_material()
        dlg = StressPathsDialog(w, material.name, material.stress_paths, "kPa")
        try:
            form = dlg._form
            assert dlg._name.text() == "Path 1" and dlg._test_type.currentData() == "uniaxial"
            assert form.isRowVisible(dlg._strain_type) and not form.isRowVisible(dlg._lateral)
            assert _headers(dlg._steps) == ["EpsilonZZ", "SigmaZZ (kPa)", "EpsilonXX"]
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("triaxial"))
            assert form.isRowVisible(dlg._lateral) and not form.isRowVisible(dlg._strain_type)
            assert dlg._lateral.value() == 100.0 and dlg._loading_dir.currentData() == "Lateral"
            assert _headers(dlg._steps) == ["EpsilonZZ", "SigmaXX (kPa)", "EpsilonV"]
            assert "not drawn" in dlg._note.text()
            dlg._loading_dir.setCurrentIndex(dlg._loading_dir.findData("Axial"))
            dlg._seepage.setCurrentIndex(dlg._seepage.findData("Undrained"))
            assert _headers(dlg._steps) == ["EpsilonZZ", "SigmaZZ (kPa)", "Pore Water Pressure (kPa)"]
            assert dlg._note.text() == ""
            dlg._steps.paste_text("0\t100\t0\n0.01\t200\t10\n0.02\t300\t20\n")
            dlg.add_item()
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("simple_shear"))
            assert _headers(dlg._steps) == ["SigmaZY (kPa)", "EpsilonZY", "EpsilonZZ"]
            assert form.isRowVisible(dlg._k0) and not form.isRowVisible(dlg._seepage)
            dlg._steps.paste_text("10\t0.001\t0\n")
            dlg.accept()
            items = dlg.items
        finally:
            dlg.deleteLater()
        first, second = items
        assert (first.test_type, first.loading, first.seepage) == ("triaxial", "Axial", "Undrained")
        assert first.steps == [[0.0, 100.0, 0.0], [0.01, 200.0, 10.0], [0.02, 300.0, 20.0]]
        assert second.test_type == "simple_shear" and second.steps == [[10.0, 0.001, 0.0]]
        w.set_stress_paths(items)
        app.processEvents()
        # only the triaxial/axial path is drawn: effective stresses
        layers = w._principal._layers
        assert len(layers) == 1
        assert np.allclose(layers[0].get_xdata(), [0.1, 0.09, 0.08]) and np.allclose(layers[0].get_ydata(), [0.1, 0.19, 0.28])
        s_layers = w._shear._layers
        assert len(s_layers) == 1 and np.allclose(s_layers[0].get_ydata(), [0.0, 0.05, 0.1])
        graphs = w._path_canvases
        assert all(len(c._lines) == 1 for c in graphs.values())
        x, y = graphs["pq"]._lines[0].get_data()
        assert np.allclose(x, [0.1, 0.37 / 3, 0.44 / 3]) and np.allclose(y, [0.0, 0.1, 0.2])
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "dev.csv"
            w.export_path_graph(graphs["deviatoric"], str(csv_path))
            header = csv_path.read_text(encoding="utf-8").splitlines()[0]
            assert header == "Soil: Path 1 Deviatoric Strain,Soil: Path 1 q (kPa)"
        w._delete_child("path", 0)
        assert [p.name for p in w._current_material().stress_paths] == ["Path 2"]
        assert w._principal._layers == [] and all(c._lines == [] for c in graphs.values())
    finally:
        w.deleteLater()


def test_states_follow_material_selection_and_files() -> None:
    app, w = _window()
    try:
        w._add_material("rock")
        w.set_failure_states([st.FailureState(points=[st.TestPoint(0.0, 20000.0)])])
        w._add_material("material")
        assert w._current_material().failure_states == []
        assert len(w._principal._layers) == 1  # the other visible material's data
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.ogrdata"
            project.save_project(path, w._project_for_save())
            loaded = project.load_project(path)
        from ogr_data.gui.main_window import MainWindow

        w2 = MainWindow()
        try:
            w2.open_project(loaded)
            assert len(w2._principal._layers) == 1 and w2._tree.topLevelItem(1).childCount() == 1
        finally:
            w2.deleteLater()
    finally:
        w.deleteLater()
