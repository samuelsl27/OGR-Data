"""Spec 003: bibliographic tables and pickers."""

from __future__ import annotations

from ogr_data.core import tables


def test_rock_strength_grades_table():
    data = tables.rock_strength_grades()
    grades = data["grades"]
    assert len(grades) == 7
    by = {g["grade"]: g for g in grades}
    assert by["R6"]["ucs_lo_mpa"] == 250.0 and by["R6"]["ucs_hi_mpa"] is None
    assert by["R5"]["ucs_lo_mpa"] == 100.0 and by["R5"]["ucs_hi_mpa"] == 250.0
    assert by["R0"]["ucs_lo_mpa"] == 0.25
    # descending order
    los = [g["ucs_lo_mpa"] for g in grades]
    assert los == sorted(los, reverse=True)
    assert "source" in data and "Hoek" in data["source"]


def test_mi_values_table():
    data = tables.mi_values()
    values = data["values"]
    by = {v["rock"]: v for v in values}
    # spot checks read from the rendered Table 3 (Hoek ch.11)
    assert by["Granite"]["mi"] == 32 and by["Granite"]["std"] == 3 and not by["Granite"]["estimated"]
    assert by["Gneiss"]["mi"] == 28 and by["Gneiss"]["std"] == 5
    assert by["Tuff"]["mi"] == 13 and by["Tuff"]["std"] == 5 and by["Tuff"]["estimated"]
    assert by["Breccias"]["mi"] == 19 and by["Breccias"]["std"] == 5
    assert by["Sandstones"]["mi"] == 17 and by["Sandstones"]["std"] == 4
    assert all(v["mi"] > 0 for v in values)
    assert "source" in data


def test_gsi_chart():
    data = tables.gsi_chart()
    assert len(data["structures"]) == 6
    assert len(data["surfaces"]) == 5
    # all cells within the published chart bounds and only valid combos
    for key, cell in data["cells"].items():
        lo, hi = cell
        assert 5 <= lo < hi <= 100, key
    assert tables.gsi_range("blocky", "good") == (50.0, 70.0)
    assert tables.gsi_range("intact_massive", "very_poor") is None
    assert tables.gsi_range("laminated_sheared", "very_good") is None
    # descriptions present
    assert all(s["description"] for s in data["structures"])
    assert all(s["description"] for s in data["surfaces"])


def test_picker_fields_registered():
    from ogr_data.core.models import CRITERIA

    ghb = {f.key: f for f in CRITERIA["generalized_hoek_brown"].fields}
    assert ghb["sigci"].pick == "sigci_grades"
    assert ghb["mi"].pick == "mi_values"
    assert ghb["gsi"].pick == "gsi_chart"
    hb = {f.key: f for f in CRITERIA["hoek_brown"].fields}
    assert hb["compressive_strength"].pick == "sigci_grades"


def test_picker_dialogs_offscreen():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui import pickers

    app = QApplication.instance() or QApplication([])
    dlg = pickers.GsiPickerDialog()
    # default selection: intact_massive + very_good -> range 80-100
    assert dlg.gsi() == 90.0
    # a mid-chart cell: blocky + good -> 50-70
    idx_b = dlg._structure.findText("BLOCKY")
    dlg._structure.setCurrentIndex(idx_b)
    idx_g = dlg._surface.findText("GOOD")
    dlg._surface.setCurrentIndex(idx_g)
    assert dlg.gsi() == 60.0
    # pick an N/A combination
    idx = dlg._structure.findText("LAMINATED/SHEARED")
    dlg._structure.setCurrentIndex(idx)
    idx_vg = dlg._surface.findText("VERY GOOD")
    dlg._surface.setCurrentIndex(idx_vg)
    assert dlg.gsi() is None
    dlg.reject()


def test_sigci_pick_values_match_the_reference_and_ormas() -> None:
    from ogr_data.core import tables

    data = tables.rock_strength_grades()
    key = next(k for k, v in data.items() if isinstance(v, list))
    picks = [g["ucs_pick_mpa"] for g in data[key]]
    assert picks == [250.0, 175.0, 75.0, 35.0, 15.0, 3.0, 0.6]
