"""Spec 022: estimation of properties without tests (GSI 2013, D, Ei/MR, Erm method)."""

from __future__ import annotations

import math

from ogr_data.core import gsi, tables

# ------------------------------------------------------------- quantified GSI


def test_gsi_equations_of_hoek_carter_diederichs_2013() -> None:
    # eq. 1: the RSData calculator case RQD = 30, JCond89 = 10 -> 30
    assert gsi.gsi_from_jcond89(10.0, 30.0) == 30.0
    assert gsi.gsi_from_jcond89(30.0, 100.0) == 95.0
    # eq. 2 as published (2 JCond76): 35 (RSData shows 34, from 1.95 and truncation)
    assert gsi.gsi_from_jcond76(10.0, 30.0) == 35.0
    # eq. 3 as published: 52 (Jr/Ja)/(1 + Jr/Ja) + RQD/2
    assert math.isclose(gsi.gsi_from_jr_ja(2.0, 1.0, 30.0), 52.0 * 2.0 / 3.0 + 15.0)
    assert math.isclose(gsi.jcond89_from_jr_ja(2.0, 1.0), 35.0 * 2.0 / 3.0)
    # Table 1: sum of the five guideline ratings
    assert gsi.jcond89_from_ratings(6, 6, 6, 6, 6) == 30.0
    assert gsi.jcond89_from_ratings(4, 4, 3, 2, 5) == 18.0
    for bad in ((7, 0, 0, 0, 0), (-1, 0, 0, 0, 0)):
        try:
            gsi.jcond89_from_ratings(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
    for call in (lambda: gsi.gsi_from_jcond89(31, 50), lambda: gsi.gsi_from_jcond89(10, 101), lambda: gsi.gsi_from_jr_ja(0, 1, 50)):
        try:
            call()
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


def test_rqd_estimates() -> None:
    # eq. 4 (Priest & Hudson): lambda = 0 -> 100; lambda = 10 -> 200/e
    assert gsi.rqd_from_lambda(0.0) == 100.0
    assert math.isclose(gsi.rqd_from_lambda(10.0), 200.0 / math.e)
    # eqs. 5-6 (Palmstrom), clipped to 0-100
    assert gsi.rqd_from_jv(10.0) == 85.0 and gsi.rqd_from_jv(10.0, palmstrom_2005=False) == 82.0
    assert gsi.rqd_from_jv(2.0) == 100.0 and gsi.rqd_from_jv(60.0) == 0.0


def test_quantified_chart() -> None:
    assert gsi.chart_gsi(30.0, 20.0) == 50.0
    assert gsi.chart_gsi(46.0, 10.0) is None and gsi.chart_gsi(10.0, 41.0) is None
    assert gsi.chart_row(35.0)["label"] == "BLOCKY" and gsi.chart_row(5.0)["label"] == "DISINTEGRATED"
    data = tables.gsi_quantified()
    assert "ARMA 13-672" in data["source"]
    assert [c["rating"] for c in data["jcond89_conditions"]] == [30, 25, 20, 10, 0]
    assert [c["rating"] for c in data["jcond76_conditions"]] == [25, 20, 12, 6, 0]
    assert [v for _, v in data["jr"]] == [4.0, 3.0, 2.0, 1.5, 1.5, 1.0, 0.5]
    assert [v for _, v in data["ja"]] == [0.75, 1.0, 2.0, 3.0, 4.0]
    for param in data["jcond89_parameters"]:
        assert max(r for _, r in param["options"]) == 6 and min(r for _, r in param["options"]) == 0


# ------------------------------------------------------------- D and MR tables


def test_disturbance_and_modulus_ratio_tables() -> None:
    d = tables.disturbance_factor()
    assert "Figure 9" in d["source"] and len(d["values"]) == 8
    assert sorted({v["d"] for v in d["values"]}) == [0.0, 0.5, 0.7, 0.8, 1.0]
    assert {v["application"] for v in d["values"]} == {"Tunnel", "Slope"}
    mr = tables.modulus_ratio()
    assert "Figure 13" in mr["source"] and len(mr["values"]) == 41
    by = {v["rock"]: v for v in mr["values"]}
    # spot checks read from the rendered figure (PRE 2023, p. 110)
    assert (by["Granite"]["mr_lo"], by["Granite"]["mr_hi"], by["Granite"]["mr_pick"]) == (300.0, 550.0, 425.0)
    assert (by["Marble"]["mr_lo"], by["Marble"]["mr_hi"]) == (700.0, 1000.0)
    assert (by["Schists"]["mr_lo"], by["Schists"]["mr_hi"]) == (250.0, 1100.0)
    assert by["Chalk"]["mr_pick"] == 1000.0 and by["Gypsum"]["estimated"]
    assert by["Shales"]["note"].startswith("highly anisotropic")


# ------------------------------------------------------------------- GUI


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_gsi_dialog_modes() -> None:
    from ogr_data.gui.estimation import GsiDialog

    app = _app()
    dlg = GsiDialog(None)
    try:
        dlg._tabs.setCurrentWidget(dlg._chart_page)
        assert dlg.value is None  # nothing clicked yet
        assert dlg._chart.set_point(30.0, 20.0) == 50.0
        assert dlg.value == 50.0 and "VERY BLOCKY" in dlg._chart_label.text()
        dlg._tabs.setCurrentIndex(dlg._tabs.count() - 1)  # calculator
        dlg._rqd.setValue(30.0)
        dlg._j89.setValue(10.0)
        assert dlg.value == 30.0
        dlg._joint_mode.setCurrentIndex(2)  # JCond76
        dlg._j76.setValue(10.0)
        assert dlg.value == 35.0
        dlg._joint_mode.setCurrentIndex(3)  # Jr/Ja: smooth undulating (2) / unaltered (1)
        assert math.isclose(dlg.value, 52.0 * 2.0 / 3.0 + 15.0)
        assert "49.67" in dlg._result.text()  # not truncated
        dlg._rqd_mode.setCurrentIndex(1)  # from lambda
        dlg._lambda.setValue(10.0)
        assert math.isclose(dlg.rqd(), 200.0 / math.e)
        dlg._tabs.setCurrentIndex(0)
        assert dlg.value is not None  # chart 2000 selector
        app.processEvents()
    finally:
        dlg.deleteLater()


def test_filtered_pickers() -> None:
    from ogr_data.gui import estimation

    _app()
    mi = estimation.mi_dialog()
    try:
        rows = tables.mi_values()["values"]
        mi._filters["rock_type"].setCurrentIndex(mi._filters["rock_type"].findData("Igneous"))
        mi._filters["texture"].setCurrentIndex(mi._filters["texture"].findData("Coarse"))
        expected = sum(1 for r in rows if r["rock_type"] == "Igneous" and r["texture"] == "Coarse")
        assert mi.visible_rows() == expected > 0
        index = next(i for i, r in enumerate(rows) if r["rock"] == "Granite")
        mi.table.setCurrentCell(index, 0)
        assert mi.value() == 32.0
    finally:
        mi.deleteLater()
    dd = estimation.disturbance_dialog()
    try:
        dd._filters["application"].setCurrentIndex(dd._filters["application"].findData("Slope"))
        assert dd.visible_rows() == 4
        dd.table.setCurrentCell(2, 0)  # Tunnel, no invert
        assert dd.value() == 0.5
    finally:
        dd.deleteLater()
    ei = estimation.ModulusRatioDialog(30000.0, "MPa")
    try:
        index = next(i for i, r in enumerate(tables.modulus_ratio()["values"]) if r["rock"] == "Granite")
        ei.table.setCurrentCell(index, 0)
        assert ei.mr.value() == 425.0 and ei.value() == 425.0 * 30000.0
        assert ei.ei_label.text() == "12,750 MPa"
        ei.mr.setValue(500.0)  # editable MR
        assert ei.value() == 500.0 * 30000.0
    finally:
        ei.deleteLater()


def test_window_ei_method_and_pick_units() -> None:
    from ogr_data.core.hoek_brown import HbInput, ModulusMethod, rock_mass_modulus
    from ogr_data.core.models import CRITERIA, MODULUS_METHODS
    from ogr_data.gui.main_window import MainWindow

    app = _app()
    keys = [f.key for f in CRITERIA["generalized_hoek_brown"].fields]
    assert "ei" in keys and "modulus_method" in keys
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        app.processEvents()
        w._widgets["sigci"].setValue(30000.0)  # ORMAS default material
        w._widgets["ei"].setValue(12000000.0)
        inp = HbInput(sigci=30.0, gsi=50.0, mi=10.0, disturbance=0.0, ei=12000.0)
        for label, method in zip(MODULUS_METHODS, ModulusMethod):
            w._widgets["modulus_method"].setCurrentIndex(w._widgets["modulus_method"].findText(label))
            erm_mpa = rock_mass_modulus(inp, method)
            assert f"{erm_mpa * 1000.0:.2f} kPa" in w._outputs.text(), (label, w._outputs.text())
        # ORMAS values: 3686.23 / 9340.70 / 5477.23 MPa (checked in test_hoek_brown)
        # picks return kPa; the form shows the display unit (MPa here)
        w._set_stress_unit("MPa")
        w.pick_value = lambda key: 175000.0  # sigci class R5 in kPa
        field = next(f for f in CRITERIA["generalized_hoek_brown"].fields if f.key == "sigci")
        w._pick(field, w._widgets["sigci"])
        assert w._widgets["sigci"].value() == 175.0
        field_d = next(f for f in CRITERIA["generalized_hoek_brown"].fields if f.key == "d")
        assert field_d.pick == "disturbance"
        w.pick_value = lambda key: 0.7
        w._pick(field_d, w._widgets["d"])
        assert w._widgets["d"].value() == 0.7
    finally:
        w._set_stress_unit("kPa")
        w.deleteLater()
