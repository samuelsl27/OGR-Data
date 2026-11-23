"""Spec 012: failure states and stress paths (core, persistence, dialogs, plots)."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np

from ogr_data.core import project
from ogr_data.core import states as st

EXAMPLES = Path("C:/Desarrollo/OGR_Suite/Data/Referencias/Doc_Guia/Doc_Roc_Data3_0/Examples")


# ------------------------------------------------------------------ core


def test_parse_rows_variants() -> None:
    # Excel (tab) with header and decimal comma; Exclude flag column
    text = "Sigma3\tSigma1\tExclude\n0\t30,5\t0\n5\t60\tx\n\n10\t80\n"
    assert st.parse_rows(text, 2, flag_column=True) == [(0.0, 30.5, False), (5.0, 60.0, True), (10.0, 80.0, False)]
    # CSV with semicolons and decimal comma; CSV with commas; whitespace
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
    top = int(np.argmax(shear))
    assert math.isclose(normal[top], 6.0, abs_tol=1e-9) and math.isclose(shear[top], 4.0)
    assert np.all(shear >= -1e-12)
    # every point lies on the circle
    assert np.allclose((normal - 6.0) ** 2 + shear**2, 16.0)


def test_stress_path_principal_mapping() -> None:
    steps = [st.PathStep(0.0, 0.0, 0.0), st.PathStep(0.01, 500.0, -0.003), st.PathStep(0.02, 900.0, -0.006)]
    uniaxial = st.StressPath(test_type="uniaxial", steps=steps)
    sig3, sig1 = uniaxial.principal_path()
    assert list(sig3) == [0.0, 0.0, 0.0] and list(sig1) == [0.0, 500.0, 900.0]
    # triaxial, Axial loading: radial stress stays at the initial lateral stress
    axial = st.StressPath(test_type="triaxial", loading="Axial", lateral_stress=100.0, steps=steps[1:])
    sig3, sig1 = axial.principal_path()
    assert list(sig3) == [100.0, 100.0] and list(sig1) == [500.0, 900.0]
    # triaxial, Lateral loading: SigmaXX varies, axial = sigma_h0 / K0
    lateral = st.StressPath(
        test_type="triaxial", loading="Lateral", lateral_stress=100.0, k0=0.5,
        steps=[st.PathStep(0.0, 100.0, 0.0), st.PathStep(-0.01, 50.0, 0.002)],
    )
    sig3, sig1 = lateral.principal_path()
    assert list(sig1) == [200.0, 200.0] and list(sig3) == [100.0, 50.0]
    # not drawable (layout not verified) or empty
    assert st.StressPath(test_type="biaxial", steps=steps).principal_path() is None
    assert st.StressPath(test_type="triaxial").principal_path() is None


def test_path_invariants_and_shear_points() -> None:
    # uniaxial with lateral strain: ev = ea + 2 er, eq = 2 (ea - er)/3
    path = st.StressPath(
        test_type="uniaxial", strain_type="Lateral",
        steps=[st.PathStep(0.0, 0.0, 0.0), st.PathStep(0.03, 600.0, -0.01)],
    )
    inv = path.invariants()
    assert np.allclose(inv.eps_v, [0.0, 0.01]) and np.allclose(inv.eps_q, [0.0, 2.0 * 0.04 / 3.0])
    assert np.allclose(inv.p, [0.0, 200.0]) and np.allclose(inv.q, [0.0, 600.0])
    # a volumetric strain column gives the same radial strain back
    vol = st.StressPath(
        test_type="uniaxial", strain_type="Volumetric",
        steps=[st.PathStep(0.0, 0.0, 0.0), st.PathStep(0.03, 600.0, 0.01)],
    )
    assert np.allclose(vol.invariants().eps_r, [0.0, -0.01])
    # stress points on tau-sigma: Mohr circle tops ((s1+s3)/2, (s1-s3)/2)
    s, t = path.shear_path()
    assert np.allclose(s, [0.0, 300.0]) and np.allclose(t, [0.0, 300.0])
    # axial stress below lateral: q negative, t (radius) positive
    ext = st.StressPath(
        test_type="triaxial", loading="Axial", lateral_stress=300.0,
        steps=[st.PathStep(0.0, 300.0, 0.0), st.PathStep(-0.01, 120.0, 0.0)],
    )
    inv = ext.invariants()
    assert np.allclose(inv.q, [0.0, -180.0]) and np.allclose(inv.t, [0.0, 90.0])


def test_path_columns_follow_rsdata_dialog() -> None:
    assert st.StressPath(test_type="uniaxial").columns() == ("EpsilonZZ", "SigmaZZ", "EpsilonXX")
    assert st.StressPath(test_type="uniaxial", strain_type="Volumetric").columns() == ("EpsilonZZ", "SigmaZZ", "EpsilonV")
    # official RSData help figure: triaxial, Loading Direction Lateral
    assert st.StressPath(test_type="triaxial").columns() == ("EpsilonZZ", "SigmaXX", "EpsilonV")
    assert st.StressPath(test_type="triaxial", loading="Axial").columns() == ("EpsilonZZ", "SigmaZZ", "EpsilonV")


def test_defaults_and_validation() -> None:
    state = st.FailureState()
    assert (state.name, state.color, state.test_type) == ("State 1", "#800000", "triaxial")
    assert state.columns == ("Sigma3", "Sigma1")
    assert st.FailureState(test_type="direct_shear").columns == ("Normal Stress", "Shear Stress")
    path = st.StressPath(test_type="bogus", seepage="x", loading="y", strain_type="z")
    assert (path.test_type, path.seepage, path.loading, path.strain_type) == ("uniaxial", "Drained", "Lateral", "Lateral")
    # RSData defaults (official help figure): lateral stress 100 kPa, K0 = 1
    assert (st.StressPath().lateral_stress, st.StressPath().k0) == (100.0, 1.0)
    # files of the first 012 version (Compression/Extension) fall back to Lateral
    assert st.StressPath.from_dict({"loading": "Compression"}).loading == "Lateral"
    assert st.next_color([]) == "#800000" and st.next_color(["#800000"]) == st.PALETTE[0]
    assert st.unique_name("State 1", ["State 1"]) == "State 1 2"


def test_templates_and_project_round_trip() -> None:
    proj = project.Project.new()
    assert proj.materials[0].failure_states == [] and proj.materials[0].stress_paths == []
    rock = proj.materials[proj.add("rock")]
    soil = proj.materials[proj.add("soil")]
    assert [s.name for s in rock.failure_states] == ["State 1"] and rock.stress_paths == []
    assert [p.name for p in soil.stress_paths] == ["Path 1"] and soil.failure_states == []
    rock.failure_states[0].peak = [st.TestPoint(0.0, 30000.0), st.TestPoint(5000.0, 61000.0, True)]
    rock.failure_states[0].residual = [st.TestPoint(5000.0, 40000.0)]
    rock.failure_states.append(st.FailureState("Shear box", "#123456", "s", "direct_shear", [st.TestPoint(100.0, 80.0)], visible=False))
    soil.stress_paths[0] = st.StressPath(
        "CD 100", "#00aa00", "triaxial", "Undrained", "Axial", 100.0, 0.5, "Lateral",
        [st.PathStep(0.0, 100.0, 0.0), st.PathStep(0.01, 250.0, -0.004)],
    )
    # duplicate copies states independently
    dup = proj.materials[proj.duplicate(1)]
    dup.failure_states[0].peak[0].y = 1.0
    assert rock.failure_states[0].peak[0].y == 30000.0
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "states.ogrdata"
        project.save_project(path, proj)
        back = project.load_project(path)
    r = back.materials[1]
    assert r.failure_states[0].peak == [st.TestPoint(0.0, 30000.0), st.TestPoint(5000.0, 61000.0, True)]
    assert r.failure_states[0].residual == [st.TestPoint(5000.0, 40000.0)]
    assert r.failure_states[1] == st.FailureState("Shear box", "#123456", "s", "direct_shear", [st.TestPoint(100.0, 80.0)], visible=False)
    assert back.materials[3].stress_paths[0] == soil.stress_paths[0]
    # 011 files (no state keys) still load
    data = proj.to_dict()
    for m in data["materials"]:
        m.pop("failure_states")
        m.pop("stress_paths")
    assert project.Project.from_dict(data).materials[1].failure_states == []


# ------------------------------------------------------------------- GUI


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._set_stress_unit("kPa")
    app.processEvents()
    return app, w


def test_failure_states_dialog_edit_and_apply() -> None:
    from ogr_data.gui.states_dialog import FailureStatesDialog

    app, w = _window()
    try:
        w._add_material("rock")
        material = w._current_material()
        dlg = FailureStatesDialog(w, material.name, material.failure_states, "MPa")
        try:
            assert dlg._list.count() == 1 and dlg._name.text() == "State 1"
            # pasted values are in the displayed unit (MPa here)
            assert dlg._peak.paste_text("Sigma3\tSigma1\n0\t30\n5\t61,5\t1\n") == 2
            dlg._tabs.setCurrentIndex(1)
            dlg._residual.paste_text("5\t40\n")
            assert dlg._peak.table.horizontalHeaderItem(0).text() == "Sigma3 (MPa)"
            # a second state: direct shear columns, then back to the first
            dlg.add_item()
            assert dlg._name.text() == "State 2" and len(dlg.items) == 2
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("direct_shear"))
            assert dlg._peak.table.horizontalHeaderItem(0).text() == "Normal Stress (MPa)"
            dlg._peak.paste_text("0.1\t0.08\n")
            dlg._list.setCurrentRow(0)
            assert dlg._peak.table.rowCount() == 2  # the first state's points are back
            # invalid cell blocks OK (store raises ValueError)
            dlg._peak.table.item(0, 1).setText("abc")
            try:
                dlg.store_current()
            except ValueError as exc:
                assert "row 1" in str(exc)
            else:
                raise AssertionError("expected ValueError")
            dlg._peak.table.item(0, 1).setText("30")
            # export / import of the table
            with tempfile.TemporaryDirectory() as tmp:
                csv_path = Path(tmp) / "peak.csv"
                dlg._peak.export_csv(str(csv_path))
                assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "Sigma3 (MPa),Sigma1 (MPa),Exclude"
                dlg._peak.set_rows([])
                assert dlg._peak.import_csv(str(csv_path)) == 2
            dlg.store_current()
            items = dlg.items
        finally:
            dlg.deleteLater()
        # stored in kPa
        first, second = items
        assert first.peak == [st.TestPoint(0.0, 30000.0), st.TestPoint(5000.0, 61500.0, True)]
        assert first.residual == [st.TestPoint(5000.0, 40000.0)]
        assert second.test_type == "direct_shear" and second.peak == [st.TestPoint(100.0, 80.0)]
        assert second.color != first.color
        # the dialog edited copies: the material is unchanged until applied
        assert material.failure_states[0].peak == []
        w.set_failure_states(items)
        app.processEvents()
        # tree children under the material
        rock_item = w._tree.topLevelItem(1)
        assert [rock_item.child(i).text(0) for i in range(rock_item.childCount())] == ["State 1", "State 2"]
        # principal: peak (included), peak (excluded), residual point layers
        p_layers = w._principal._layers
        assert len(p_layers) == 3
        x, y = p_layers[0].get_data()
        assert list(x) == [0.0] and list(y) == [30.0]  # MPa on the canvas
        assert p_layers[1].get_alpha() == 0.35  # excluded point drawn faded
        assert p_layers[2].get_markerfacecolor() == "none"  # residual hollow
        # shear: three Mohr circles + the direct shear point
        s_layers = w._shear._layers
        circles = [l for l in s_layers if l.get_linestyle() != "None"]
        points = [l for l in s_layers if l.get_linestyle() == "None"]
        assert len(circles) == 3 and len(points) == 1
        assert math.isclose(max(circles[0].get_ydata()), 15.0)  # radius (30-0)/2 MPa
        assert list(points[0].get_xdata()) == [0.1]
        legend = [t.get_text() for t in w._principal.axes.get_legend().get_texts()]
        assert "Rock: State 1" in legend and "Rock: State 1 (residual)" in legend
        # hide the state from the tree
        from PySide6.QtCore import Qt

        rock_item.child(0).setCheckState(0, Qt.CheckState.Unchecked)
        app.processEvents()
        assert w._current_material().failure_states[0].visible is False
        assert w._principal._layers == []
        assert len(w._shear._layers) == 1
        # hiding the material hides its data
        rock_item.child(0).setCheckState(0, Qt.CheckState.Checked)
        rock_item.setCheckState(0, Qt.CheckState.Unchecked)
        app.processEvents()
        assert w._principal._layers == [] and w._shear._layers == []
    finally:
        w.deleteLater()


def test_stress_paths_dialog_and_plot() -> None:
    from ogr_data.gui.states_dialog import StressPathsDialog

    app, w = _window()
    try:
        w._add_material("soil")
        material = w._current_material()
        dlg = StressPathsDialog(w, material.name, material.stress_paths, "kPa")
        try:
            assert dlg._name.text() == "Path 1" and dlg._test_type.currentData() == "uniaxial"
            assert not dlg._lateral.isEnabled()  # triaxial-only settings
            assert dlg._strain_type.isEnabled()  # uniaxial-only setting
            assert dlg._steps.table.horizontalHeaderItem(2).text() == "EpsilonXX"
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("triaxial"))
            assert dlg._lateral.isEnabled() and not dlg._strain_type.isEnabled()
            assert dlg._lateral.value() == 100.0  # RSData default
            assert dlg._steps.table.horizontalHeaderItem(1).text() == "SigmaXX (kPa)"
            dlg._loading_dir.setCurrentIndex(dlg._loading_dir.findData("Axial"))
            assert dlg._steps.table.horizontalHeaderItem(1).text() == "SigmaZZ (kPa)"
            dlg._lateral.setValue(100.0)
            dlg._k0.setValue(0.5)
            dlg._seepage.setCurrentIndex(dlg._seepage.findData("Undrained"))
            dlg._steps.paste_text("EpsilonZZ\tSigmaZZ\tEpsilonXX\n0\t100\t0\n0.01\t250\t-0.004\n0.02\t320\t-0.007\n")
            dlg.add_item()
            dlg._test_type.setCurrentIndex(dlg._test_type.findData("general"))
            assert "spec 021" in dlg._note.text()
            dlg._steps.paste_text("0\t50\t0\n")
            dlg.accept()
            items = dlg.items
        finally:
            dlg.deleteLater()
        first = items[0]
        assert (first.test_type, first.seepage, first.loading, first.lateral_stress, first.k0) == ("triaxial", "Undrained", "Axial", 100.0, 0.5)
        assert first.steps[1] == st.PathStep(0.01, 250.0, -0.004)
        w.set_stress_paths(items)
        app.processEvents()
        # only the triaxial path is drawable: one polyline on the principal plot
        layers = w._principal._layers
        assert len(layers) == 1 and layers[0].get_linestyle() == "-"
        x, y = layers[0].get_data()
        assert np.allclose(x, [0.1, 0.1, 0.1]) and np.allclose(y, [0.1, 0.25, 0.32])
        # stress points on the tau-sigma plot: ((s1+s3)/2, (s1-s3)/2)
        s_layers = w._shear._layers
        assert len(s_layers) == 1
        assert np.allclose(s_layers[0].get_xdata(), [0.1, 0.175, 0.21])
        assert np.allclose(s_layers[0].get_ydata(), [0.0, 0.075, 0.11])
        # Stress Path Graphs tab: four graphs with one series each
        graphs = w._path_canvases
        assert w._graph_tabs.tabText(1) == "Stress Path Graphs"
        assert all(len(c._lines) == 1 for c in graphs.values())
        x, y = graphs["axial"]._lines[0].get_data()
        assert np.allclose(x, [0.0, 0.01, 0.02]) and np.allclose(y, [0.1, 0.25, 0.32])
        x, y = graphs["pq"]._lines[0].get_data()
        assert np.allclose(x, [0.1, 0.15, 0.52 / 3.0]) and np.allclose(y, [0.0, 0.15, 0.22])
        ev = graphs["volumetric"]._lines[0].get_ydata()
        assert np.allclose(ev, [0.0, -0.004, -0.007])  # EpsilonV column as given
        assert graphs["pq"].axes.get_xlabel() == "p (kPa)"
        assert graphs["volumetric"].axes.get_ylabel() == "Volumetric Strain"
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "dev.csv"
            w.export_path_graph(graphs["deviatoric"], str(csv_path))
            header = csv_path.read_text(encoding="utf-8").splitlines()[0]
            assert header == "Soil: Path 1 Deviatoric Strain,Soil: Path 1 q (kPa)"
        # exported with the plot (CSV columns per layer)
        series = w._principal.layer_series()
        assert series[0][0] == "Soil: Path 1 sigma3" and series[0][1] == "Soil: Path 1 sigma1"
        # delete the path from the tree context action
        w._delete_child("path", 0)
        assert [p.name for p in w._current_material().stress_paths] == ["Path 2"]
        assert w._principal._layers == []
        assert all(c._lines == [] for c in graphs.values())
    finally:
        w.deleteLater()


def test_states_follow_material_selection_and_files() -> None:
    app, w = _window()
    try:
        w._add_material("rock")
        w.set_failure_states([st.FailureState(peak=[st.TestPoint(0.0, 20000.0)])])
        w._add_material("material")
        assert w._current_material().failure_states == []
        # data of the other visible material is still drawn
        assert len(w._principal._layers) == 1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.ogrdata"
            project.save_project(path, w._project_for_save())
            loaded = project.load_project(path)
        assert loaded.materials[1].failure_states[0].peak == [st.TestPoint(0.0, 20000.0)]
        from ogr_data.gui.main_window import MainWindow

        w2 = MainWindow()
        try:
            w2.open_project(loaded)
            assert len(w2._principal._layers) == 1
            assert w2._tree.topLevelItem(1).childCount() == 1
        finally:
            w2.deleteLater()
    finally:
        w.deleteLater()
