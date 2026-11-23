"""Spec 010: material properties database (RocProp equivalent, own data)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ogr_data.core import database as mdb


def _user_record(**kw) -> dict:
    record = mdb.empty_record()
    record.update({"rock_name": "Granite", "notes": "pink"})
    record["location"].update({"country": "Spain", "place": "Guadarrama"})
    record["reference"].update({"title": "Site investigation report", "author": "A. Author", "year": 2020})
    record["tests"] = {"compression": {"ucs_mpa": 180.0, "information_quality": 7}, "hoek_brown": {"mi": 30.0}}
    record.update(kw)
    return record


def test_builtin_records_from_sourced_tables() -> None:
    records = mdb.builtin_records()
    assert len(records) == 49  # 42 rocks of Hoek's mi table + 7 UCS field-estimate grades
    assert len({r["record_id"] for r in records}) == len(records)
    for r in records:
        mdb.validate(r)  # every built-in record has a source
        assert r["origin"] == "builtin" and r["reference"]["author"] == "E. Hoek"
    granite = next(r for r in records if r["rock_name"] == "Granite")
    assert granite["tests"]["hoek_brown"] == {"mi": 32.0, "mi_std": 3.0, "modulus_ratio": "300-550"}
    r5 = next(r for r in records if r["rock_name"].startswith("Field estimate R5"))
    assert r5["tests"]["compression"]["ucs_mpa"] == 175.0 and r5["tests"]["compression"]["ucs_range_mpa"] == "100-250"
    assert mdb.available_tests(granite) == ["Hoek-Brown"] and mdb.available_tests(r5) == ["Compression"]


def test_search_wildcards_phrases_and_paging() -> None:
    db = mdb.MaterialDatabase(None)
    names = lambda q: [r["rock_name"] for r in db.search(q)]
    assert "Granite" in names("granite") and "Granodiorite" not in names("granite")  # whole words
    assert {"Granite", "Granodiorite"} <= set(names("gran*"))  # wildcard
    assert names('"micritic limestones"') == ["Micritic Limestones"]  # exact phrase
    assert names('"limestones micritic"') == []
    assert all("Igneous" in r["notes"] for r in db.search("igneous coarse"))  # AND of terms
    # case-insensitive, whole words (the R6/R5 grades list gneiss among their examples)
    assert names("GNEISS")[0] == "Gneiss" and set(names("GNEISS")[1:]) == {"Field estimate R6 (Extremely strong)", "Field estimate R5 (Very strong)"}
    assert names("gneis") == []
    assert len(db.search("")) == len(db.records)
    everything = db.search("")
    assert mdb.MaterialDatabase.page_count(everything) == 4  # 49 records / 14 per page
    assert len(mdb.MaterialDatabase.page(everything, 3)) == 49 - 3 * 14


def test_user_records_validation_and_storage() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "materials_db.json"
        db = mdb.MaterialDatabase(path)
        # a record without source is not saved
        no_source = _user_record()
        no_source["reference"]["author"] = ""
        for bad, message in ((no_source, "without source"), (_user_record(rock_name=" "), "rock name")):
            try:
                db.save_record(bad)
            except ValueError as exc:
                assert message in str(exc)
            else:
                raise AssertionError("expected ValueError")
        bad_quality = _user_record()
        bad_quality["tests"]["compression"]["information_quality"] = 12
        try:
            db.save_record(bad_quality)
        except ValueError as exc:
            assert "Information Quality" in str(exc)
        else:
            raise AssertionError("expected ValueError")
        stored = db.save_record(_user_record())
        assert stored["record_id"] == 50 and stored["origin"] == "user"
        assert json.loads(path.read_text(encoding="utf-8"))["format"] == "ogr-data-materials-db/1"
        # reload, search, edit, delete
        db2 = mdb.MaterialDatabase(path)
        assert [r["rock_name"] for r in db2.search("guadarrama")] == ["Granite"]
        stored["notes"] = "grey"
        db2.save_record(stored)
        assert mdb.MaterialDatabase(path).get(50)["notes"] == "grey"
        # built-in records are read-only
        for call in (lambda: db2.save_record(db2.get(1)), lambda: db2.delete(1)):
            try:
                call()
            except ValueError:
                pass
            else:
                raise AssertionError("expected ValueError")
        db2.delete(50)
        assert mdb.MaterialDatabase(path).get(50) is None


def test_material_parameters_and_clipboard() -> None:
    record = _user_record()
    assert mdb.to_material_parameters(record) == {"sigci": 180000.0, "mi": 30.0, "mi_residual": 30.0}
    record["tests"]["hoek_brown"]["sigci_mpa"] = 150.0  # the Hoek-Brown block wins over UCS
    assert mdb.to_material_parameters(record)["sigci"] == 150000.0
    try:
        mdb.to_material_parameters(mdb.empty_record())
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    text = mdb.clipboard_text(record)
    assert "Rock Name\tGranite" in text and "Compression: Compressive Strength (MPa)\t180.0" in text
    assert mdb.title(record) == "Granite, Spain, Guadarrama"


def test_database_dialog_and_use_as_material() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.database_dialog import DatabaseDialog
    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as tmp:
        w = MainWindow()
        w.database_path = Path(tmp) / "db.json"
        try:
            w._set_stress_unit("kPa")
            db = mdb.MaterialDatabase(w._database_file())
            dlg = DatabaseDialog(db, w, on_use=w.use_database_record)
            try:
                assert "of 49" in dlg.summary.text() and dlg.list.count() == 14
                dlg.go_page(3)
                assert dlg.list.count() == 7 and not dlg.next.isEnabled()
                dlg.query.setText("granite")
                dlg.search()
                assert dlg.current["rock_name"] == "Granite"
                assert not dlg.edit.isEnabled() and not dlg.delete.isEnabled()  # built-in
                dlg.use_record()
                app.processEvents()
                material = w._current_material()
                assert material.name == "Granite" and material.criterion == "generalized_hoek_brown"
                assert material.parameters["mi"] == 32.0 and w._widgets["mi"].value() == 32.0
                # user record through the dialog API (no modal editor)
                stored = dlg.save(_user_record())
                assert dlg.current["record_id"] == stored["record_id"] and dlg.edit.isEnabled()
                dlg.origin.setCurrentIndex(2)  # My records
                assert dlg.list.count() == 1
                dlg.use_record()
                assert w._current_material().parameters["sigci"] == 180000.0
                dlg.delete_record(confirm=False)
                assert dlg.list.count() == 0
            finally:
                dlg.deleteLater()
            assert "Material Database…" in [a.text() for m in w.menuBar().actions() if m.text() == "Analysis" for a in m.menu().actions()]
        finally:
            w.deleteLater()


def test_record_edit_dialog_validates() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.database_dialog import RecordEditDialog

    QApplication.instance() or QApplication([])
    dlg = RecordEditDialog(mdb.empty_record())
    try:
        dlg._edits[("rock_name",)].setText("Basalt")
        dlg._edits[("reference", "title")].setText("Field notes")
        dlg._edits[("reference", "author")].setText("B. Author")
        dlg._edits[("reference", "isbn")].setText("0660159252")
        dlg._edits[("tests", "compression", "ucs_mpa")].setText("210,5")
        record = dlg.collect()
        mdb.validate(record)
        assert record["tests"] == {"compression": {**{k: "" for k, *_ in mdb.COMPRESSION_FIELDS}, "ucs_mpa": 210.5}}
        assert record["reference"]["isbn"] == "0660159252"  # stays text
    finally:
        dlg.deleteLater()
