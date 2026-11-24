"""Spec 007: project files and .roc import."""

from __future__ import annotations

from pathlib import Path

from ogr_data.core import project, roc_import
from ogr_data.core.models import CRITERIA, defaults
from tests._references import roc_examples

EXAMPLES = roc_examples()  # found by search (spec 027)


def test_project_round_trip(tmp_path=None):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "m.ogrdata"
        params = defaults("generalized_hoek_brown")
        params["sigci"] = 50000.0
        material = project.Material("Granite", "generalized_hoek_brown", params, 7.5)
        project.save_project(path, project.Project(materials=[material]))
        data = project.load_project(path).materials[0]
        assert data.name == "Granite"
        assert data.criterion == "generalized_hoek_brown"
        assert data.parameters["sigci"] == 50000.0
        assert data.sig3max_mpa == 7.5


def test_project_rejects_bad_format(tmp_path=None):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.ogrdata"
        path.write_text('{"format": "other/1"}', encoding="utf-8")
        try:
            project.load_project(path)
        except ValueError as exc:
            assert "unsupported" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_import_all_official_examples():
    files = sorted(EXAMPLES.glob("*.roc"))
    assert len(files) >= 10  # the user's guide of the format ships 10 .roc examples
    imported = {}
    for f in files:
        imported[f.name] = roc_import.parse_roc(f)
    # criterion codes: 0=HB, 1=MC, 2=BB, 3=PC (from the example set)
    assert imported["Granite Triaxial Data.roc"].criterion == "generalized_hoek_brown"
    assert imported["MC Direct Shear Lab Data.roc"].criterion == "mohr_coulomb"
    assert imported["BB Lab Data.roc"].criterion == "barton_bandis"
    assert imported["PC Lab Data.roc"].criterion == "power_curve"
    return imported


def test_granite_parameters_and_data():
    roc = roc_import.parse_roc(EXAMPLES / "Granite Triaxial Data.roc")
    # MPa -> kPa conversion
    assert abs(roc.parameters["sigci"] - 369270.0) < 1.0
    assert roc.parameters["gsi"] == 100.0
    assert abs(roc.parameters["mi"] - 21.914) < 1e-9
    assert roc.sig3max_mpa == 150.0
    # lab data block: 7 triaxial points, first pair (-21, 30) MPa
    assert len(roc.lab_data.points) == 7
    assert roc.lab_data.points[0] == (-21.0, 30.0)


def test_mc_and_bb_parameter_mapping():
    mc = roc_import.parse_roc(EXAMPLES / "MC Direct Shear Lab Data.roc")
    assert "peak_cohesion" in mc.parameters and "peak_friction" in mc.parameters
    bb = roc_import.parse_roc(EXAMPLES / "BB Lab Data.roc")
    assert "phi_r" in bb.parameters and "jrc" in bb.parameters and "jcs" in bb.parameters
    # BB example: JRC 15.42, JCS 77.344 MPa -> 77344 kPa
    assert abs(bb.parameters["jrc"] - 15.42) < 1e-9
    assert abs(bb.parameters["jcs"] - 77344.0) < 1.0


def test_import_rejects_non_roc():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "x.roc"
        path.write_text("hello\n", encoding="utf-8")
        try:
            roc_import.parse_roc(path)
        except ValueError as exc:
            assert "not a .roc file" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_import_rejects_unsupported_units():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "u.roc"
        path.write_text(roc_import.FORMAT_TAG + "\n  version: 3.013\n\nproject settings:\n  units: 4\n  failure criterion: 0\n", encoding="utf-8")
        try:
            roc_import.parse_roc(path)
        except ValueError as exc:
            assert "units code 4" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_apply_project_and_roc_to_window_offscreen():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._set_stress_unit("kPa")  # display unit; widgets show kPa (spec 017)
    roc = roc_import.parse_roc(EXAMPLES / "Granite Triaxial Data.roc")
    w._apply_project(roc.criterion, roc.parameters, roc.sig3max_mpa)
    assert w._criterion_combo.currentData() == "generalized_hoek_brown"
    assert abs(w._widgets["sigci"].value() - 369270.0) < 1.0
    assert w._sig3max.value() == 150000.0  # 150 MPa in kPa
