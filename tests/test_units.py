"""Spec 017: display units (kPa/MPa) and project title."""

from __future__ import annotations


def test_factors_and_round_trip() -> None:
    from ogr_data.core import units

    assert units.stress_factor("MPa") == 1.0
    assert units.stress_factor("kPa") == 1000.0
    assert units.to_display(7.5, "kPa") == 7500.0
    assert units.from_display(7500.0, "kPa") == 7.5
    assert units.to_display(7.5, "MPa") == 7.5
    value = 3.14159
    for unit in ("MPa", "kPa"):
        assert abs(units.from_display(units.to_display(value, unit), unit) - value) < 1e-12
    try:
        units.stress_factor("psi")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown unit")


def test_stress_text() -> None:
    from ogr_data.core import units

    assert units.stress_text(5.23, "MPa") == "5.2300 MPa"
    assert units.stress_text(5.23, "kPa") == "5230.0000 kPa"
    assert units.stress_text(3686.23, "kPa", decimals=2) == "3686230.00 kPa"


def test_project_round_trip_with_unit_and_title(tmp_path=None) -> None:
    import tempfile
    from pathlib import Path

    from ogr_data.core import project

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.ogrdata"
        params = {"sigci": 50000.0, "gsi": 55.0, "mi": 12.0, "d": 0.0}
        material = project.Material("Rock", "generalized_hoek_brown", params, 3.25)
        project.save_project(path, project.Project(materials=[material], stress_unit="MPa", title="Portal tunnel"))
        data = project.load_project(path)
        assert data.stress_unit == "MPa"
        assert data.title == "Portal tunnel"
        assert data.materials[0].sig3max_mpa == 3.25

        # old files without the new keys keep the defaults
        legacy = Path(tmp) / "legacy.ogrdata"
        legacy.write_text(
            '{"format": "ogr-data-project/1", "name": "Old", "criterion": "mohr_coulomb", '
            '"sig3max_mpa": 1.0, "parameters": {}}',
            encoding="utf-8",
        )
        data = project.load_project(legacy)
        assert data.stress_unit == "kPa"
        assert data.title == ""


def test_units_window_offscreen() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")  # QSettings may persist a previous run
        app.processEvents()
        assert w._stress_unit == "kPa"
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        app.processEvents()
        sigci = w._widgets["sigci"]
        assert sigci.value() == 100000.0 and sigci.suffix() == " kPa"
        assert w._sig3max.value() == 7500.0  # 7.5 MPa in kPa

        # switch to MPa: display scales, internals unchanged
        w._set_stress_unit("MPa")
        app.processEvents()
        assert sigci.value() == 100.0 and sigci.suffix() == " MPa"
        assert w._sig3max.value() == 7.5 and w._sig3max.suffix() == " MPa"
        assert w._params()["sigci"] == 100000.0
        assert w._sig3max_mpa() == 7.5
        assert "sigma3 (MPa)" == w._principal.axes.get_xlabel()
        # tick labels follow the display unit (plotted data stay in MPa)
        assert w._principal.axes.xaxis.get_major_formatter()(7.5, 0) == "7.5"
        assert w._shear.axes.yaxis.get_major_formatter()(2.0, 0) == "2"
        assert "normal stress (MPa)" == w._shear.axes.get_xlabel()
        assert "MPa" in w._outputs.text() and "kPa" not in w._outputs.text()

        # round trip back to kPa is idempotent
        w._set_stress_unit("kPa")
        app.processEvents()
        assert sigci.value() == 100000.0 and sigci.suffix() == " kPa"
        assert w._sig3max.value() == 7500.0
        assert w._params()["sigci"] == 100000.0
        assert w._principal.axes.xaxis.get_major_formatter()(7.5, 0) == "7500"

        # project title drives the window title
        w._title_edit.setText("Portal tunnel")
        assert w.windowTitle() == "OGR Data - Portal tunnel"

        # save keeps the display unit and title; loading applies them
        import tempfile
        from pathlib import Path

        from ogr_data.core import project

        w._set_stress_unit("MPa")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.ogrdata"
            project.save_project(path, w._project_for_save())
            data = project.load_project(path)
            w2 = MainWindow()
            try:
                assert w2.windowTitle() == "OGR Data"
                w2.open_project(data)
                app.processEvents()
                assert w2._stress_unit == "MPa"
                assert abs(w2._widgets["sigci"].value() - 100.0) < 1e-6
                assert w2.windowTitle() == "OGR Data - Portal tunnel"
            finally:
                w2._set_stress_unit("kPa")
                w2.deleteLater()
    finally:
        w._set_stress_unit("kPa")
        w.deleteLater()
