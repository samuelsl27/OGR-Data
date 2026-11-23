"""Spec 018: pick dialogs for Barton-Bandis (phi r, JRC, JCS) and typical c, phi of USCS soils."""

from __future__ import annotations

import math

from ogr_data.core import barton, tables


def _raises(call) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ------------------------------------------------------------------ core


def test_barton_bandis_equations() -> None:
    # eq. 5: phi r = (phi b - 20) + 20 r / R
    assert barton.phi_r_from_schmidt(30.0, 40.0, 40.0) == 30.0  # unweathered: phi r = phi b
    assert barton.phi_r_from_schmidt(30.0, 20.0, 40.0) == 20.0
    _raises(lambda: barton.phi_r_from_schmidt(30.0, 20.0, 0.0))
    # eq. 6 and 7 with L0 = 100 mm
    assert barton.jrc_scaled(10.0, 0.1) == 10.0
    assert math.isclose(barton.jrc_scaled(10.0, 1.0), 10.0 * 10.0 ** (-0.2))
    assert math.isclose(barton.jcs_scaled(100.0, 10.0, 1.0), 100.0 * 10.0 ** (-0.3))
    assert math.isclose(barton.jcs_scaled(100.0, 0.0, 5.0), 100.0)  # smooth joints: no scale effect
    _raises(lambda: barton.jrc_scaled(10.0, 0.0))
    _raises(lambda: barton.jcs_scaled(100.0, 10.0, 1.0, 0.0))


def test_source_tables() -> None:
    phi = tables.basic_friction_angle()
    assert "FHWA-TS-89-045" in phi["source"] and len(phi["values"]) == 14
    assert all(v["phi_lo"] <= v["phi_hi"] for v in phi["values"])
    limestone = next(v for v in phi["values"] if v["rock"] == "Limestone")
    assert (limestone["phi_lo"], limestone["phi_hi"]) == (33, 40)
    soils = tables.soil_field_strength()
    assert [g["grade"] for g in soils["grades"]] == ["S1", "S2", "S3", "S4", "S5"]
    assert [g["ucs_pick_mpa"] for g in soils["grades"]] == [0.04, 0.06, 0.115, 0.375, 0.8]
    ufc = tables.uscs_compacted_properties()
    assert "UFC 3-220-01N" in ufc["source"] and len(ufc["values"]) == 15
    assert "SP" not in {v["symbol"] for v in ufc["values"]}


def test_uscs_typical_strength() -> None:
    assert barton.mohr_coulomb_from_symbol("CL") == {"peak_cohesion": 13.0, "peak_friction": 28.0}
    assert barton.mohr_coulomb_from_symbol("CL", saturated=False) == {"peak_cohesion": 86.0, "peak_friction": 28.0}
    assert barton.mohr_coulomb_from_symbol("CL-ML") == {"peak_cohesion": 22.0, "peak_friction": 32.0}  # = ML-CL
    assert barton.mohr_coulomb_from_symbol("gw") == {"peak_cohesion": 0.0, "peak_friction": 38.0}  # '>38'
    assert barton.phi_value(">38") == (38.0, True) and barton.phi_value("28") == (28.0, False)
    assert barton.compacted_properties("SP") is None
    _raises(lambda: barton.mohr_coulomb_from_symbol("SP"))  # not in the table
    _raises(lambda: barton.mohr_coulomb_from_symbol("GM"))  # cohesion '-----'
    _raises(lambda: barton.mohr_coulomb_from_symbol("OH"))  # insufficient data


# ------------------------------------------------------------------- GUI


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_phi_r_dialog() -> None:
    from ogr_data.gui.estimation import PhiRDialog

    _app()
    dlg = PhiRDialog()
    try:
        index = next(i for i, r in enumerate(tables.basic_friction_angle()["values"]) if r["rock"] == "Limestone")
        dlg.table.setCurrentCell(index, 0)
        assert dlg.value() == 40.0  # dry
        dlg.surface.setCurrentIndex(1)
        assert dlg.value() == 33.0  # wet
        dlg.schmidt.setCurrentIndex(1)
        dlg.r.setValue(20.0)
        dlg.big_r.setValue(40.0)
        assert dlg.value() == 23.0 and "23.00" in dlg.result.text()
    finally:
        dlg.deleteLater()


def test_jrc_and_jcs_dialogs() -> None:
    from ogr_data.gui.estimation import JcsDialog, JrcDialog

    _app()
    jrc = JrcDialog(10.0)
    try:
        jrc.length.setValue(1.0)
        assert math.isclose(jrc.value(), barton.jrc_scaled(10.0, 1.0))
    finally:
        jrc.deleteLater()
    jcs = JcsDialog(10.0, "MPa")
    try:
        grades = tables.rock_strength_grades()["grades"]
        index = next(i for i, g in enumerate(grades) if g["grade"] == "R3")
        jcs.table.setCurrentCell(index, 0)
        assert math.isclose(jcs.jcs0.value(), grades[index]["ucs_pick_mpa"])  # shown in MPa
        assert math.isclose(jcs.value(), grades[index]["ucs_pick_mpa"] * 1000.0)  # returns kPa at L = L0
        jcs.length.setValue(1.0)
        assert math.isclose(jcs.value(), barton.jcs_scaled(grades[index]["ucs_pick_mpa"] * 1000.0, 10.0, 1.0))
        jcs._filters["material"].setCurrentIndex(jcs._filters["material"].findData("Soil"))
        assert jcs.visible_rows() == 5
        jcs.table.setCurrentCell(len(grades) + 3, 0)  # S4 stiff soil
        assert math.isclose(jcs.jcs0.value(), 0.375)
    finally:
        jcs.deleteLater()


def test_compacted_soil_dialog_and_window_pick() -> None:
    from ogr_data.core.models import CRITERIA
    from ogr_data.gui.estimation import CompactedSoilDialog
    from ogr_data.gui.main_window import MainWindow

    app = _app()
    dlg = CompactedSoilDialog("CL-ML")
    try:
        assert dlg.selected()["symbol"] == "ML-CL"
        assert dlg.value() == {"peak_cohesion": 22.0, "peak_friction": 32.0}
        dlg.cohesion.setCurrentIndex(1)
        assert dlg.value()["peak_cohesion"] == 65.0
    finally:
        dlg.deleteLater()
    picks = {f.key: f.pick for f in CRITERIA["barton_bandis"].fields}
    assert (picks["phi_r"], picks["jrc"], picks["jcs"]) == ("barton_phi", "barton_jrc", "barton_jcs")
    w = MainWindow()
    try:
        w._set_stress_unit("MPa")
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("mohr_coulomb"))
        app.processEvents()
        field = next(f for f in CRITERIA["mohr_coulomb"].fields if f.key == "peak_cohesion")
        assert field.pick == "compacted_soil"
        w.pick_value = lambda key: {"peak_cohesion": 13.0, "peak_friction": 28.0}  # CL, kPa
        w._pick(field, w._widgets["peak_cohesion"])
        assert math.isclose(w._widgets["peak_cohesion"].value(), 0.013)  # both fields, display unit
        assert w._widgets["peak_friction"].value() == 28.0
    finally:
        w._set_stress_unit("kPa")
        w.deleteLater()


def test_classifier_creates_material() -> None:
    from ogr_data.gui.main_window import MainWindow
    from ogr_data.gui.soil_classifier import SoilClassifierDialog

    _app()
    w = MainWindow()
    created = []
    dlg = SoilClassifierDialog(w, on_create=lambda s, p: created.append(w.add_soil_material(s, p)))
    try:
        dlg._fields["sand_pct"].setValue(10.0)
        dlg._fields["fines_pct"].setValue(80.0)
        dlg._fields["ll"].setValue(30.0)
        dlg._fields["pi"].setValue(15.0)
        assert dlg.symbol == "CL", dlg.symbol
        assert "c' saturated 13 kPa" in dlg._numeric.text()
        assert dlg._create.isEnabled()
        count = len(w._project.materials)
        dlg.create_material()
        assert len(w._project.materials) == count + 1
        material = w._project.materials[created[0]]
        assert material.criterion == "mohr_coulomb" and material.name.startswith("CL")
        assert material.parameters["peak_cohesion"] == 13.0 and material.parameters["peak_friction"] == 28.0
        dlg._fields["fines_pct"].setValue(80.0 + 20.0)  # fines + sand > 100 %: message, no crash
        assert dlg.symbol == "" and not dlg._create.isEnabled()
        dlg._fields["fines_pct"].setValue(2.0)  # clean sand
        dlg._fields["ll"].setValue(0.0)
        dlg._fields["pi"].setValue(0.0)
        dlg._fields["cu"].setValue(2.0)
        dlg._fields["cc"].setValue(0.5)
        dlg._fields["sand_pct"].setValue(90.0)
        assert dlg.symbol == "SP", dlg.symbol
        assert "not listed" in dlg._numeric.text() and not dlg._create.isEnabled()
    finally:
        dlg.deleteLater()
        w.deleteLater()
