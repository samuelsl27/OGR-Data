"""Spec 019: the operations layer (ogr_data.api) without a window."""

from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from ogr_data.api import Conflict, InvalidArgument, NotFound, OgrApiError, Workspace, call
from ogr_data.core import clipboard, gsi_charts
from ogr_data.core import material_results as mr
from ogr_data.core import project as projects

ROOT = Path(__file__).resolve().parent.parent
ORMAS = {"sigci": 30000.0, "gsi": 50.0, "mi": 10.0, "d": 0.0, "ei": 12000000.0}  # ORMAS default material


def _ws() -> Workspace:
    # no user database: only the built-in records (the tests never read the user's file)
    return Workspace(database_path=Path(tempfile.gettempdir()) / "ogr_data_test_no_db.json")


def _raises(exc_type, fn, *args, **kwargs) -> OgrApiError:
    try:
        fn(*args, **kwargs)
    except exc_type as exc:
        return exc
    raise AssertionError(f"expected {exc_type.__name__}")


def _ghb(ws) -> str:
    pid = call(ws, "project_new", title="API")["project_id"]
    call(ws, "material_set", project_id=pid, criterion="generalized_hoek_brown", parameters=dict(ORMAS), sig3max_kpa=7500.0)
    return pid


def test_layering_no_qt_no_gui_no_sdk() -> None:
    # static: no import of them anywhere in the layer
    for f in (ROOT / "ogr_data" / "api").rglob("*.py"):
        imports = [line.strip() for line in f.read_text(encoding="utf-8").splitlines() if line.strip().startswith(("import ", "from "))]
        for banned in ("PySide6", "ogr_data.gui", "..gui", "mcp"):
            assert not any(banned in line for line in imports), (f.name, banned)
    # dynamic: importing and using it loads none of them
    code = (
        "import sys; from ogr_data.api import Workspace, call; ws = Workspace();"
        "call(ws, 'project_new'); call(ws, 'render_envelope');"
        "bad = [m for m in sys.modules if m.startswith(('PySide6', 'ogr_data.gui', 'mcp'))]; print(bad)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True)
    assert out.stdout.strip() == "[]", out.stdout + out.stderr


def test_ghb_matches_ormas_and_the_core() -> None:
    ws = _ws()
    pid = _ghb(ws)
    out = call(ws, "material_compute", project_id=pid, points=5)
    c = out["computed"]
    assert abs(c["c_kpa"] - 1494.1) < 0.5 and abs(c["phi_deg"] - 30.52) < 0.01  # ORMAS
    assert abs(c["erm_kpa"] - 3686230.0) < 10.0  # ORMAS 3686.23 MPa
    core = mr.ghb_computed("generalized_hoek_brown", {**projects.Material("x", "generalized_hoek_brown", dict(ORMAS)).parameters}, 7.5)
    assert all(math.isclose(c[k[:-4] + "_kpa" if k.endswith("_mpa") else k], v * (1000.0 if k.endswith("_mpa") else 1.0)) for k, v in core.items())
    env = out["principal_envelope"]
    assert len(env["sigma3_kpa"]) == 5 and env["sigma3_kpa"][-1] == 7500.0 and abs(env["sigma1_kpa"][0] - c["sigc_kpa"]) < 1e-6
    # sig3max by application (spec 009, ORMAS): tunnel 0.6642 MPa, slope 1.0610 MPa at 26 kN/m3 and 50 m
    tunnel = call(ws, "material_set", application_mode="tunnel", unit_weight_kn_m3=26.0, depth_m=50.0)
    assert abs(tunnel["sig3max_kpa"] - 664.2) / 664.2 < 0.005
    slope = call(ws, "material_set", application_mode="slope")
    assert abs(slope["sig3max_kpa"] - 1061.0) < 1.0
    # sig3max follows the parameters while the application holds
    weaker = call(ws, "material_set", parameters={"gsi": 30.0})
    assert weaker["sig3max_kpa"] != slope["sig3max_kpa"]
    assert isinstance(_raises(Conflict, call, ws, "material_set", sig3max_kpa=5000.0), Conflict)
    call(ws, "material_set", application_mode="custom", sig3max_kpa=5000.0)
    assert call(ws, "material_get")["sig3max_kpa"] == 5000.0


def test_same_values_as_the_window() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    ws = _ws()
    _ghb(ws)
    api = call(ws, "material_compute")["computed"]
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        app.processEvents()
        for key, value in ORMAS.items():
            w._widgets[key].setValue(value)
        w._sig3max.setValue(7500.0)
        app.processEvents()
        window = w._ghb_computed()
        for key, value in window.items():
            api_key = key[:-4] + "_kpa" if key.endswith("_mpa") else key
            factor = 1000.0 if key.endswith("_mpa") else 1.0
            assert math.isclose(api[api_key], value * factor, rel_tol=1e-12), key
        # the clipboard text of the window and of the API is the same contract
        text = call(ws, "material_copy")["text"]
        assert clipboard.parse_material(text).computed["erm_mpa"] == window["erm_mpa"]
    finally:
        w.deleteLater()


def test_projects_files_and_handles() -> None:
    ws = _ws()
    with tempfile.TemporaryDirectory() as tmp:
        ws.workdir = Path(tmp)
        pid = _ghb(ws)
        call(ws, "material_add", template="rock", name="Granite")
        call(ws, "project_set", title="Saved", display_stress_unit="MPa", selected_material="0")
        saved = call(ws, "project_save", path="demo")
        assert saved["saved_to"].endswith("demo.ogrdata") and Path(saved["saved_to"]).is_file()
        assert isinstance(_raises(Conflict, call, ws, "project_save", path="demo", project_id=call(ws, "project_new")["project_id"]), Conflict)
        _raises(Conflict, call, ws, "material_get")  # two projects open: say which
        loaded = projects.load_project(Path(tmp) / "demo.ogrdata")  # the window's own loader
        assert [m.name for m in loaded.materials] == ["Material", "Granite"] and loaded.stress_unit == "MPa"
        again = call(ws, "project_open", path="demo.ogrdata")
        assert again["title"] == "Saved" and len(again["materials"]) == 2
        call(ws, "project_close", project_id=pid)
        assert pid not in [p["project_id"] for p in call(ws, "project_list")["projects"]]
        _raises(NotFound, call, ws, "project_open", path="missing.ogrdata")


def test_validation_with_suggestions() -> None:
    ws = _ws()
    _ghb(ws)
    e = _raises(NotFound, call, ws, "material_set", parameters={"sigcj": 1.0})
    assert "Did you mean 'sigci'" in str(e) and e.code == "E_NOT_FOUND"
    e = _raises(InvalidArgument, call, ws, "material_set", parameters={"modulus_method": "Hoek 2002"})
    assert "must be one of" in str(e)
    _raises(InvalidArgument, call, ws, "material_set", parameters={"gsi": "fifty"})
    _raises(Conflict, call, ws, "material_set", criterion="mohr_coulomb", application_mode="tunnel")
    _raises(Conflict, call, ws, "material_delete")  # the last material
    _raises(NotFound, call, ws, "material_get", material="Basalt")
    _raises(NotFound, call, ws, "material_get", material="7")
    _raises(NotFound, call, ws, "no_such_operation")
    # changing criterion starts from its defaults; an application falls back to custom
    call(ws, "material_set", application_mode="tunnel")
    out = call(ws, "material_set", criterion="mohr_coulomb", parameters={"peak_cohesion": 50.0})
    assert out["application"]["mode"] == "custom" and out["notes"] and out["parameters"]["peak_cohesion"] == 50.0


def test_clipboard_roundtrip_and_roc() -> None:
    ws = _ws()
    _ghb(ws)
    text = call(ws, "material_copy")["text"]
    pasted = call(ws, "material_paste", text=text)
    assert pasted["criterion"] == "generalized_hoek_brown" and pasted["parameters"]["sigci"] == 30000.0
    assert "criterion\tGeneralized" in call(ws, "material_copy", format="tabular")["text"]
    _raises(InvalidArgument, call, ws, "material_paste", text="hello")
    _raises(NotFound, call, ws, "material_import_roc", path="nothing.roc")
    roc = Path("C:/Desarrollo/OGR_Suite/Data/Referencias/Doc_Guia/Doc_Roc_Data3_0/Examples/Granite Triaxial Data.roc")
    if roc.is_file():  # the RocData 3.0 examples of the suite references (as test_project)
        imported = call(ws, "material_import_roc", path=str(roc))
        assert imported["criterion"] == "generalized_hoek_brown" and imported["selected"]


def test_fit_and_calibration() -> None:
    ws = _ws()
    pid = _ghb(ws)
    # Mohr-Coulomb triaxial data, c = 1000 kPa, phi = 30 deg
    phi = math.radians(30.0)
    s3 = [0.0, 1000.0, 2000.0, 4000.0]
    s1 = [2 * 1000.0 * math.cos(phi) / (1 - math.sin(phi)) + (1 + math.sin(phi)) / (1 - math.sin(phi)) * x for x in s3]
    fit = call(ws, "fit_data", criterion="mohr_coulomb", data_kind="triaxial", x=s3, y=s1, apply_to="0", project_id=pid)
    assert abs(fit["parameters"]["cohesion_kpa"] - 1000.0) < 1e-6 and abs(fit["parameters"]["friction_deg"] - 30.0) < 1e-9
    assert fit["applied_to"]["criterion"] == "mohr_coulomb" and abs(fit["applied_to"]["parameters"]["peak_cohesion"] - 1000.0) < 1e-6
    _raises(InvalidArgument, call, ws, "fit_data", criterion="mohr_coulomb", data_kind="triaxial", x=[1.0], y=[2.0, 3.0])
    _raises(InvalidArgument, call, ws, "fit_data", criterion="generalized_hoek_brown", data_kind="triaxial", x=s3, y=s1)
    # calibration of intact GHB to points on a known envelope (sigci 50 MPa, mi 12)
    call(ws, "material_add", template="rock", name="Lab")
    sig3 = np.array([0.0, 2000.0, 5000.0, 10000.0])
    sig1 = sig3 + 50000.0 * (12.0 * sig3 / 50000.0 + 1.0) ** 0.5
    state = call(ws, "failure_state_set", name="State 1", material="Lab", points=[[a, b] for a, b in zip(sig3, sig1)])
    assert state["columns"] == ["Sigma3", "Sigma1"] and len(state["failure_state"]["points"]) == 4
    _raises(InvalidArgument, call, ws, "failure_state_set", name="Bad", material="Lab", points=[[10.0, 5.0]])
    out = call(ws, "calibrate", material="Lab", new_material_name="Calibrated")
    assert abs(out["fitted"]["sigci_kpa"] - 50000.0) < 1.0 and abs(out["fitted"]["mi"] - 12.0) < 1e-3
    assert out["rms_kpa"] < 1.0 and out["new_material"]["name"] == "Calibrated"
    assert call(ws, "project_summary")["materials"][-1]["selected"]
    call(ws, "failure_state_delete", name="State 1", material="Lab")
    _raises(InvalidArgument, call, ws, "calibrate", material="Lab")


def test_stress_paths_and_simulation() -> None:
    ws = _ws()
    call(ws, "project_new")
    call(ws, "material_add", template="soil", name="Sand")
    path = call(ws, "stress_path_set", name="Path 1", test_type="triaxial", loading="Axial", steps=[[0.0, 100.0, 0.0]])
    assert path["columns"] == ["EpsilonZZ", "SigmaZZ", "EpsilonV"]
    _raises(InvalidArgument, call, ws, "stress_path_set", name="Path 1", steps=[[1.0]])
    call(ws, "stress_path_delete", name="Path 1")
    call(ws, "test_simulation_set", name="Test 1", test_type="triaxial", confining_kpa=100.0)
    run = call(ws, "test_simulation_run", name="Test 1", samples=5)
    assert len(run["curves"]["q_kpa"]) == 5 and run["first_yield_step"] is not None
    assert abs(run["peak"]["q_kpa"] - run["analytic_failure_q_kpa"]) < 1e-3  # the 13a check, through the API
    _raises(InvalidArgument, call, ws, "test_simulation_set", name="Test 1", test_type="oedometer")
    call(ws, "material_set", criterion="power_curve")
    _raises(Conflict, call, ws, "test_simulation_run", name="Test 1")


def test_estimation_without_tests() -> None:
    ws = _ws()
    # RSData calculator cases (spec 022): RQD 30
    assert call(ws, "gsi_quantified", rqd=30.0, jcond89=10.0)["gsi"] == 30.0
    assert call(ws, "gsi_quantified", rqd=30.0, jcond76=10.0)["gsi"] == 35.0
    assert abs(call(ws, "gsi_quantified", rqd=30.0, jr=2.0, ja=1.0)["gsi"] - (52.0 * 2 / 3 + 15.0)) < 1e-12
    ratings = {"persistence": 4, "aperture": 4, "roughness": 3, "infilling": 2, "weathering": 5}
    assert call(ws, "gsi_quantified", jv=10.0, jcond89_ratings=ratings)["gsi"] == 1.5 * 18 + 85.0 / 2
    _raises(InvalidArgument, call, ws, "gsi_quantified", rqd=30.0)
    _raises(InvalidArgument, call, ws, "gsi_quantified", rqd=30.0, jv=3.0, jcond89=10.0)
    out = call(ws, "gsi_chart", chart="flysch_2000", rock_type="C", language="es")
    assert out["gsi"] == gsi_charts.gsi_at("flysch_2000", *gsi_charts.type_center("flysch_2000", "C")) and "tipo C" in out["summary"]
    assert call(ws, "gsi_chart", chart="general_2000", u=0.9, v=0.05)["gsi"] is None
    _raises(InvalidArgument, call, ws, "gsi_chart", chart="general_2000", rock_type="A")
    granite = call(ws, "table_get", table="mi_values", query="granite")
    assert granite["count"] >= 1 and all("ranite" in r["rock"] for r in granite["rows"])
    assert call(ws, "table_get", table="gsi_2000_ranges")["count"] == 30
    # USCS (spec 004/018) and the Mohr-Coulomb material of the group
    call(ws, "project_new")
    clay = call(ws, "classify_uscs", fines_pct=80.0, sand_pct=15.0, ll=40.0, pi=20.0, create_material=True)
    assert clay["symbol"] == "CL" and clay["new_material"]["criterion"] == "mohr_coulomb"
    barton = call(ws, "barton_estimate", jrc0=10.0, jcs0_kpa=100000.0, block_length_m=1.0, phi_b_deg=30.0, schmidt_r=30.0, schmidt_big_r=40.0)
    assert barton["phi_r_deg"] == 25.0 and barton["jrc_n"] < 10.0 and barton["jcs_n_kpa"] < 100000.0


def test_database_and_outputs() -> None:
    ws = _ws()
    pid = _ghb(ws)
    found = call(ws, "database_search", query="granite")
    assert found["results"] >= 1 and found["records"][0]["record_id"] is not None
    _raises(InvalidArgument, call, ws, "database_search", query="granite", page=99)
    record_id = found["records"][0]["record_id"]
    assert call(ws, "database_get", record_id=record_id)["record"]["record_id"] == record_id
    new = call(ws, "database_use", record_id=record_id)
    assert new["new_material"]["criterion"] == "generalized_hoek_brown"
    with_specimens = next(r for r in ws.database().records if r.get("specimens"))
    used = call(ws, "database_use", record_id=with_specimens["record_id"], use="failure_state", material="0")
    assert used["failure_state"]["points"]
    _raises(NotFound, call, ws, "database_get", record_id=999999)
    png = call(ws, "render_envelope", project_id=pid, materials=["0"], plot="shear", show_mc=True)
    assert png["png"].startswith(b"\x89PNG") and png["unit"] == "kPa"
    with tempfile.TemporaryDirectory() as tmp:
        ws.workdir = Path(tmp)
        rep = call(ws, "report_generate", path="report", views=["0"], unit="MPa")
        html = Path(rep["saved_to"]).read_text(encoding="utf-8")
        assert rep["saved_to"].endswith(".html") and "data:image/png;base64" in html and "views" in rep["sections"]
        _raises(Conflict, call, ws, "report_generate", path="report")
        only = call(ws, "report_generate", path="short", sections=["title", "material_models"])
        assert only["sections"] == ["material_models"]
        saved = call(ws, "render_envelope", save_path="env")
        assert Path(saved["saved_to"]).read_bytes() == saved["png"]


def test_catalog_kinds() -> None:
    ws = _ws()
    from ogr_data.api.ops.catalog import KINDS

    for kind in KINDS:
        assert call(ws, "catalog", kind=kind)
    crit = call(ws, "catalog", kind="criteria")["criteria"]
    ghb = next(c for c in crit if c["key"] == "generalized_hoek_brown")
    assert "triaxial" in ghb["fits"] and ghb["simulated"] and any(f["key"] == "modulus_method" and f["options"] for f in ghb["fields"])
    _raises(InvalidArgument, call, ws, "catalog", kind="materials")


def test_window_applies_a_fit_in_the_display_unit() -> None:
    """Fit to Data -> Apply writes kPa values through the display unit (the mapping moved to the core for spec 019)."""

    from PySide6.QtWidgets import QApplication

    from ogr_data.core import fitting
    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w._set_stress_unit("MPa")
        result = fitting.FitResult("mohr_coulomb", fitting.TRIAXIAL, fitting.LINEAR, {"cohesion_mpa": 1.0, "friction_deg": 30.0}, 0.0)
        w.apply_fit_parameters(result)
        app.processEvents()
        assert w._criterion_combo.currentData() == "mohr_coulomb"
        assert abs(w._widgets["peak_cohesion"].value() - 1.0) < 1e-9  # 1 MPa shown in MPa (it was 1000 before)
        assert abs(w._params()["peak_cohesion"] - 1000.0) < 1e-6  # stored in kPa
    finally:
        w._set_stress_unit("kPa")
        w.deleteLater()


def test_project_history_undo_redo() -> None:
    """Spec 023: every editing operation is one undo step of its project."""

    ws = _ws()
    pid = _ghb(ws)  # project_new (not a step) + material_set (one step)
    call(ws, "material_add", template="rock", name="Granite")
    call(ws, "material_set", material="Granite", parameters={"gsi": 30.0})
    call(ws, "material_compute")  # reading is not a step
    hist_list = call(ws, "project_history")
    assert len(hist_list["undo"]) == 3 and hist_list["undo"][0] == "Change GSI" and hist_list["redo"] == []
    out = call(ws, "project_history", action="undo", steps=2)
    assert out["steps_done"] == 2 and len(call(ws, "project_summary")["materials"]) == 1
    assert call(ws, "project_history", action="redo")["steps_done"] == 1
    assert call(ws, "material_get", material="Granite")["parameters"]["gsi"] == 50.0
    assert call(ws, "project_history", action="undo", steps=10)["steps_done"] == 2  # only what there is
    assert call(ws, "material_get")["criterion"] == "mohr_coulomb"
    _raises(InvalidArgument, call, ws, "project_history", action="rewind")
    with tempfile.TemporaryDirectory() as tmp:
        ws.workdir = Path(tmp)
        call(ws, "project_history", action="redo", steps=3)
        assert call(ws, "project_summary")["unsaved_changes"]
        call(ws, "project_save", path="h")
        assert not call(ws, "project_summary")["unsaved_changes"]
        call(ws, "project_history", action="undo")
        assert call(ws, "project_summary", project_id=pid)["unsaved_changes"]
