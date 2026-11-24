"""Spec 011: multi-material projects (core model, v1 migration, GUI tree)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ogr_data.core import project
from ogr_data.core.models import defaults

EXAMPLES = Path("C:/Desarrollo/OGR_Suite/Data/Referencias/Doc_Guia/Doc_Roc_Data3_0/Examples")


# ------------------------------------------------------------------ core


def test_new_project_and_templates() -> None:
    proj = project.Project.new()
    assert len(proj.materials) == 1
    first = proj.materials[0]
    assert first.name == "Material" and first.criterion == project.DEFAULT_CRITERION
    assert first.color == ""  # theme envelope color
    rock = proj.materials[proj.add("rock")]
    soil = proj.materials[proj.add("soil")]
    assert rock.criterion == "generalized_hoek_brown" and rock.name == "Rock"
    assert rock.parameters == defaults("generalized_hoek_brown")
    assert soil.criterion == "mohr_coulomb" and soil.name == "Soil"
    # added materials get distinct palette colors
    assert rock.color and soil.color and rock.color != soil.color
    # names stay unique
    again = proj.materials[proj.add("rock")]
    assert again.name == "Rock 2"
    try:
        proj.add("granite")
    except ValueError as exc:
        assert "template" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_duplicate_remove_rename() -> None:
    proj = project.Project.new()
    index = proj.add("rock")
    proj.materials[index].parameters["sigci"] = 75000.0
    dup = proj.duplicate(index)
    assert dup == index + 1
    copy = proj.materials[dup]
    assert copy.name == "Rock - Copy" and copy.parameters["sigci"] == 75000.0
    # independent copy (no shared parameter dict)
    copy.parameters["sigci"] = 1.0
    assert proj.materials[index].parameters["sigci"] == 75000.0
    assert copy.color != proj.materials[index].color
    # rename: unique and non-empty
    assert proj.rename(dup, "Rock") == "Rock 2"
    assert proj.rename(dup, "  Weathered rock ") == "Weathered rock"
    try:
        proj.rename(dup, "   ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    # remove: returns the index to select; the last material stays
    # deleting the last item selects the new last one; a middle one, its slot
    assert dup == 2 and proj.remove(dup) == 1
    proj.add("soil")
    assert proj.remove(1) == 1 and proj.materials[1].name == "Soil"
    while len(proj.materials) > 1:
        proj.remove(0)
    try:
        proj.remove(0)
    except ValueError as exc:
        assert "at least one" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_v2_round_trip_with_mixed_criteria() -> None:
    proj = project.Project.new()
    proj.materials[0].parameters["peak_cohesion"] = 25.0
    proj.materials[0].parameters["set_residual_to_peak"] = False
    rock = proj.materials[proj.add("rock")]
    rock.parameters["sigci"] = 50000.0
    rock.application = project.Application("tunnel", 0.027, 120.0)
    joint = project.Material("Joint", "barton_bandis", {"jrc": 12.0}, 2.0, color="#123456", symbol="D", visible=False)
    proj.append(joint)
    proj.append(project.Material("Sand", "norsand", {}))
    proj.selected = 1
    proj.title = "Dam foundation"
    proj.stress_unit = "MPa"
    proj.graph_options = {"principal": {"title": "P"}}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "multi.ogrdata"
        project.save_project(path, proj)
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["format"] == "ogr-data-project/2" and len(raw["materials"]) == 4
        back = project.load_project(path)
    assert [m.criterion for m in back.materials] == ["mohr_coulomb", "generalized_hoek_brown", "barton_bandis", "norsand"]
    assert back.materials[0].parameters["peak_cohesion"] == 25.0
    assert back.materials[0].parameters["set_residual_to_peak"] is False
    assert back.materials[1].parameters["sigci"] == 50000.0
    assert back.materials[1].application == project.Application("tunnel", 0.027, 120.0)
    j = back.materials[2]
    assert (j.name, j.color, j.symbol, j.visible, j.sig3max_mpa) == ("Joint", "#123456", "D", False, 2.0)
    assert j.parameters["jrc"] == 12.0 and j.parameters["phi_r"] == 30.0  # defaults filled
    assert back.selected == 1 and back.title == "Dam foundation" and back.stress_unit == "MPa"
    assert back.graph_options == {"principal": {"title": "P"}}


def test_v1_file_migrates_to_one_material_project() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "old.ogrdata"
        path.write_text(
            json.dumps(
                {
                    "format": "ogr-data-project/1",
                    "name": "Granite",
                    "title": "Old case",
                    "criterion": "generalized_hoek_brown",
                    "sig3max_mpa": 12.0,
                    "stress_unit": "MPa",
                    "graph_options": {"shear": {"grid": False}},
                    "parameters": {"sigci": 150000.0, "gsi": 70.0},
                }
            ),
            encoding="utf-8",
        )
        proj = project.load_project(path)
    assert len(proj.materials) == 1 and proj.selected == 0
    m = proj.materials[0]
    assert m.name == "Granite" and m.criterion == "generalized_hoek_brown" and m.sig3max_mpa == 12.0
    assert m.parameters["sigci"] == 150000.0 and m.parameters["mi"] == 10.0  # default filled
    assert m.application.mode == "custom" and m.visible
    assert proj.title == "Old case" and proj.stress_unit == "MPa"
    assert proj.graph_options == {"shear": {"grid": False}}


def test_project_validation_errors() -> None:
    cases = [
        ({"format": "ogr-data-project/2", "materials": []}, "no materials"),
        ({"format": "ogr-data-project/2", "materials": [{"name": "X", "criterion": "bogus"}]}, "unknown criterion"),
        ({"format": "ogr-data-project/1", "criterion": "bogus"}, "unknown criterion"),
        ({"format": "ogr-data-project/9"}, "unsupported"),
    ]
    for data, message in cases:
        try:
            project.Project.from_dict(data)
        except ValueError as exc:
            assert message in str(exc), (data, exc)
        else:
            raise AssertionError(f"expected ValueError for {data}")
    # out-of-range selection is clamped; unknown symbol/mode fall back
    proj = project.Project.from_dict(
        {
            "format": "ogr-data-project/2",
            "selected": 7,
            "materials": [{"name": "A", "criterion": "mohr_coulomb", "symbol": "*", "application": {"mode": "dam"}}],
        }
    )
    assert proj.selected == 0
    assert proj.materials[0].symbol == "o" and proj.materials[0].application.mode == "custom"


def test_envelopes_helper_per_space() -> None:
    from ogr_data.core import criteria_envelopes as ce

    principal, shear = ce.envelopes("generalized_hoek_brown", defaults("generalized_hoek_brown"), 7.5)
    assert principal is not None and shear is not None and len(principal[0]) == len(shear[0])
    principal, shear = ce.envelopes("barton_bandis", defaults("barton_bandis"), 7.5)
    assert principal is None and shear is not None
    assert ce.envelopes("norsand", defaults("norsand"), 7.5) == (None, None)


# ------------------------------------------------------------------- GUI


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._set_stress_unit("kPa")  # QSettings may persist a previous run
    app.processEvents()
    return app, w


def _select(w, index: int) -> None:
    w._tree.setCurrentItem(w._tree.topLevelItem(index))


def test_window_tree_add_select_keeps_each_material() -> None:
    app, w = _window()
    try:
        assert w._tree.topLevelItemCount() == 1
        assert w._tree.topLevelItem(0).text(0) == "Material"
        assert w._name_edit.text() == "Material"
        # edit material 0 (MC): cohesion and a bool field
        w._widgets["peak_cohesion"].setValue(42.0)
        w._widgets["set_residual_to_peak"].setChecked(False)
        # Add Rock Template: GHB with registry defaults, selected
        w._add_material("rock")
        app.processEvents()
        assert w._tree.topLevelItemCount() == 2 and w._current == 1
        assert w._criterion_combo.currentData() == "generalized_hoek_brown"
        assert w._name_edit.text() == "Rock"
        assert w._widgets["sigci"].value() == 100000.0
        w._widgets["sigci"].setValue(60000.0)
        # GHB material in tunnel mode (spec 009 settings are per material)
        w._application_combo.setCurrentIndex(w._application_combo.findData("tunnel"))
        tunnel_sig3max = w._sig3max_mpa()
        # back to material 0: its own criterion and values
        _select(w, 0)
        app.processEvents()
        assert w._current == 0 and w._criterion_combo.currentData() == "mohr_coulomb"
        assert w._widgets["peak_cohesion"].value() == 42.0
        assert w._widgets["set_residual_to_peak"].isChecked() is False
        assert w._application_combo.currentData() == "custom"
        assert w._sig3max_mpa() == 7.5
        # and to the rock again
        _select(w, 1)
        app.processEvents()
        assert w._widgets["sigci"].value() == 60000.0
        assert w._application_combo.currentData() == "tunnel"
        assert abs(w._sig3max_mpa() - tunnel_sig3max) < 1e-12
        assert w._project.materials[0].parameters["peak_cohesion"] == 42.0
    finally:
        w.deleteLater()


def test_window_other_materials_drawn_and_visibility() -> None:
    from PySide6.QtCore import Qt

    app, w = _window()
    try:
        w._add_material("rock")
        app.processEvents()
        rock = w._project.materials[1]
        # material 0 (MC) is drawn as "other" in both plots, theme color
        assert len(w._principal._others) == 1 and len(w._shear._others) == 1
        assert w._principal._others[0].get_color() == w._principal.line_color("envelope")
        # the selected material uses its own color; a legend names both
        assert w._principal._line.get_color() == rock.color
        legend = w._principal.axes.get_legend()
        assert legend is not None
        assert [t.get_text() for t in legend.get_texts()] == ["Rock", "Material"]
        names = [name for name, _x, _y in w._principal.other_series()]
        assert names == ["Material"]
        # hide the other material: no extra curve, no legend
        w._tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Unchecked)
        app.processEvents()
        assert w._project.materials[0].visible is False
        assert w._principal._others == [] and w._principal.axes.get_legend() is None
        # hide the selected one: still edited, not drawn nor sampled
        w._tree.topLevelItem(1).setCheckState(0, Qt.CheckState.Unchecked)
        app.processEvents()
        assert not w._principal._line.get_visible()
        assert w._curves == {"principal": None, "shear": None}
        assert "envelope" not in w._principal.series_data()
        w._tree.topLevelItem(1).setCheckState(0, Qt.CheckState.Checked)
        app.processEvents()
        assert w._principal._line.get_visible() and w._curves["principal"] is not None
        # a shear-space material appears only on the shear plot
        w._tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)
        w._project.append(project.Material("Joint", "barton_bandis", {}))
        w._populate_tree()
        w.refresh()
        assert len(w._principal._others) == 1 and len(w._shear._others) == 2
        # color change from the tree
        w._set_material_color("#ff00aa")
        assert w._principal._line.get_color() == "#ff00aa"
    finally:
        w.deleteLater()


def test_window_duplicate_rename_delete() -> None:
    app, w = _window()
    try:
        w._widgets["peak_cohesion"].setValue(33.0)
        w._duplicate_material()
        app.processEvents()
        assert w._tree.topLevelItemCount() == 2 and w._current == 1
        assert w._name_edit.text() == "Material - Copy"
        assert w._widgets["peak_cohesion"].value() == 33.0
        # rename from the tree (in-place edit) and from the name field
        w._tree.topLevelItem(1).setText(0, "Clay")
        app.processEvents()
        assert w._project.materials[1].name == "Clay" and w._name_edit.text() == "Clay"
        w._name_edit.setText("Stiff clay")
        assert w._tree.topLevelItem(1).text(0) == "Stiff clay"
        # a clashing name is numbered; an empty tree edit is reverted
        w._tree.topLevelItem(1).setText(0, "Material")
        assert w._project.materials[1].name == "Material 2"
        assert w._tree.topLevelItem(1).text(0) == "Material 2"
        w._tree.topLevelItem(1).setText(0, "")
        assert w._tree.topLevelItem(1).text(0) == "Material 2"
        # symbol for spec 012 points
        w._set_material_symbol("s")
        assert w._project.materials[1].symbol == "s"
        # delete the selected material; the last one cannot be deleted
        w._delete_material(confirm=False)
        assert w._tree.topLevelItemCount() == 1 and w._current == 0
        assert not w._delete_button.isEnabled()
        w._delete_material(confirm=False)
        assert w._tree.topLevelItemCount() == 1
    finally:
        w.deleteLater()


def test_window_copy_material_is_the_selected_one() -> None:
    import time

    from ogr_data.core import clipboard

    app, w = _window()
    try:
        w._add_material("soil")
        w._add_material("rock")
        _select(w, 1)
        app.processEvents()
        # Same Windows clipboard race as test_clipboard: rewrite until it lands.
        payload = None
        for _ in range(40):
            w._copy_material()
            app.processEvents()
            payload = clipboard.parse_material(app.clipboard().text())
            if payload is not None and payload.name == "Soil":
                break
            time.sleep(0.025)
        assert payload is not None and payload.name == "Soil"
        assert payload.criterion == "mohr_coulomb"
    finally:
        w.deleteLater()


def test_window_project_save_open_and_import() -> None:
    from ogr_data.core import roc_import

    app, w = _window()
    try:
        w.set_project_title("Two materials")
        w._add_material("rock")
        w._widgets["gsi"].setValue(65.0)
        roc = roc_import.parse_roc(EXAMPLES / "Granite Triaxial Data.roc")
        w.import_material(roc.title, roc.criterion, roc.parameters, roc.sig3max_mpa)
        app.processEvents()
        assert w._tree.topLevelItemCount() == 3 and w._current == 2
        assert abs(w._widgets["sigci"].value() - 369270.0) < 1.0
        assert w._sig3max.value() == 150000.0  # 150 MPa in kPa
        _select(w, 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.ogrdata"
            project.save_project(path, w._project_for_save())
            loaded = project.load_project(path)
        from ogr_data.gui.main_window import MainWindow

        w2 = MainWindow()
        try:
            w2.open_project(loaded)
            app.processEvents()
            assert w2._tree.topLevelItemCount() == 3 and w2._current == 1
            assert w2._name_edit.text() == "Rock"
            assert w2._widgets["gsi"].value() == 65.0
            assert w2.windowTitle() == "Untitled[*] (Two materials) - OGR Data" and not w2.isWindowModified()  # just opened (spec 023)
            _select(w2, 2)
            assert abs(w2._widgets["sigci"].value() - 369270.0) < 1.0
            # New Project: back to one default material, empty title
            w2._new_project(confirm=False)
            assert w2._tree.topLevelItemCount() == 1
            assert w2._criterion_combo.currentData() == project.DEFAULT_CRITERION
            assert w2.windowTitle() == "Untitled[*] - OGR Data"
        finally:
            w2.deleteLater()
    finally:
        w.deleteLater()


def test_window_csv_export_includes_other_materials() -> None:
    import csv

    from PySide6.QtWidgets import QFileDialog

    app, w = _window()
    original = QFileDialog.getSaveFileName
    try:
        w._add_material("rock")
        app.processEvents()
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "plot.csv")
            QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (path, "CSV (*.csv)"))
            w._export_canvas_csv(w._principal)
            with open(path, newline="", encoding="utf-8") as fh:
                header = next(csv.reader(fh))
        assert "sigma3 (kPa)" in header[0]
        assert any(h.startswith("Material sigma3") for h in header)
        assert any(h.startswith("Material sigma1") for h in header)
    finally:
        QFileDialog.getSaveFileName = original
        w.deleteLater()
