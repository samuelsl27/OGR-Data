# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025e: notation, decimals and units.

Invariants:

- numbers on screen: at most 6 significant figures and no padding zeros
  (angles: 4 decimals), as RSData 1.009 shows them; never scientific
  notation for the usual magnitudes; float noise shows as 0;
- what is copied, exported or saved keeps every decimal;
- a value typed with more decimals than shown is the value used;
- Greek letters and the degree sign on screen; files keep ASCII;
- every dialog works in the window's stress unit;
- no internal key on screen.
"""

from __future__ import annotations

from ogr_data.core.numbers import format_number, symbols


# ---------------------------------------------------------------- T1: the format


def test_format_matches_rsdata_captures() -> None:
    # RSData 1.009, captures 39 and 74 (../Referencias/Ejemplos/RSData_analisis/capturas)
    assert format_number(100000.0) == "100000"
    assert format_number(100.0) == "100"
    assert format_number(0.0) == "0"
    assert format_number(0.000233284) == "0.000233284"
    assert format_number(40.5662, "angle") == "40.5662"
    # 6 significant figures, no padding
    assert format_number(1.676834) == "1.67683"
    assert format_number(0.0038659211) == "0.00386592"
    assert format_number(-230.55721) == "-230.557"
    assert format_number(10.5) == "10.5"
    assert format_number(3686230.82) == "3686231"  # all integer digits, never 3.68623e+06
    assert format_number(35.0, "angle") == "35"
    assert format_number(40.48123456, "angle") == "40.4812"
    # float noise of a fit is zero; genuinely tiny values keep their digits
    assert format_number(7.48901e-13) == "0"
    assert format_number(1.33e-7) == "1.33e-07"
    assert format_number(float("nan")) == "-"


def test_symbols_on_screen_only() -> None:
    assert symbols("sigma3 (kPa)") == "σ₃ (kPa)"
    assert symbols("sigma1 = 5 kPa   sigma_n = 2 kPa   tau = 1 kPa") == "σ₁ = 5 kPa   σn = 2 kPa   τ = 1 kPa"
    assert symbols("sig3max (envelope range)") == "σ₃max (envelope range)"
    assert symbols("phi = 35 deg") == "φ = 35°"
    assert symbols("sigt sigc sigcm sigci phi_b phi_r") == "σt σc σcm σci φb φr"
    assert symbols("Application (sigma3max range)") == "Application (σ₃max range)"
    assert symbols("sigma'1") == "σ'₁"
    # words that merely contain the letters are left alone
    assert symbols("design degree phial") == "design degree phial"


def test_stress_text_uses_the_format() -> None:
    from ogr_data.core import units

    assert units.stress_text(5.23, "MPa") == "5.23 MPa"
    assert units.stress_text(5.23, "kPa") == "5230 kPa"
    assert units.stress_text(3686.23082, "kPa") == "3686231 kPa"


# ---------------------------------------------------------------- the window


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.ask_unsaved = lambda: "discard"
    w._set_stress_unit("kPa")
    w.resize(1366, 768)
    w.show()
    app.processEvents()
    return app, w


def _close(w) -> None:
    w.ask_unsaved = lambda: "discard"
    w.close()
    w.deleteLater()


def test_fields_show_no_padding_and_keep_what_is_typed() -> None:
    """RF-2, RF-5: no padding zeros; a value with many decimals is kept."""

    app, w = _window()
    try:
        cohesion = w._widgets["peak_cohesion"]
        assert cohesion.text() == "10.5 kPa", cohesion.text()
        assert w._widgets["peak_friction"].text() == "35°"
        assert w._sig3max.text() == "7500 kPa"
        cohesion.lineEdit().setText("10.123456789")
        cohesion.interpretText()
        app.processEvents()
        assert abs(w._params()["peak_cohesion"] - 10.123456789) < 1e-9
        assert cohesion.text() == "10.1235 kPa"  # 6 significant figures shown
    finally:
        _close(w)


def test_copy_keeps_every_decimal() -> None:
    """RF-4: the clipboard carries the full value, not the shown one."""

    import json

    from PySide6.QtWidgets import QApplication

    from ogr_data.core import clipboard

    app, w = _window()
    try:
        w._widgets["peak_cohesion"].setValue(10.123456789)
        QApplication.clipboard().setText("")
        w._copy_material()
        text = QApplication.clipboard().text()
        payload = json.loads(text[len(clipboard.PREFIX):])
        assert "10.123456789" in json.dumps(payload), text
    finally:
        _close(w)


def test_screen_uses_symbols_and_the_format() -> None:
    """RF-1, RF-3: axes, results and sampler with Greek letters and the format."""

    app, w = _window()
    try:
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        app.processEvents()
        assert w._principal.axes.get_xlabel() == "σ₃ (kPa)" and w._principal.axes.get_ylabel() == "σ₁ (kPa)"
        rows = dict(w._results.rows())
        assert {"mb", "s", "a", "σt", "σc", "σcm", "c", "φ", "Erm"} <= set(rows)
        assert rows["φ"].endswith("°") and "deg" not in w._results.results_text()
        assert "e+" not in rows["Erm"]
        w._stress_sampler_act.setChecked(True)
        w._sample_at("principal", 2.0)
        message = w.statusBar().currentMessage()
        assert "σ₃ = " in message and "sigma" not in message
    finally:
        w._stress_sampler_act.setChecked(False)
        _close(w)


def test_fit_dialog_works_in_the_window_unit() -> None:
    """RF-7: the fit dialog reads and shows the window's unit (it was always MPa)."""

    from ogr_data.gui.fit_dialog import FitDialog

    app, w = _window()
    try:
        dialog = FitDialog(w)
        headers = [dialog._table.horizontalHeaderItem(i).text() for i in range(2)]
        assert headers == ["σ₃ (kPa)", "σ₁ (kPa)"], headers
        # MC, friction 30 deg, cohesion 20 kPa: sigma1 = 2c sqrt(N) + N sigma3, N = 3
        from PySide6.QtWidgets import QTableWidgetItem

        for row, s3 in enumerate((0.0, 1000.0, 2000.0, 4000.0)):
            dialog._table.setItem(row, 0, QTableWidgetItem(str(s3)))
            dialog._table.setItem(row, 1, QTableWidgetItem(str(2 * 20.0 * 3 ** 0.5 + 3.0 * s3)))
        dialog._method.setCurrentIndex(0)
        dialog._run_fit()
        assert dialog._result is not None
        assert abs(dialog._result.parameters["cohesion_mpa"] - 0.020) < 1e-9
        assert abs(dialog._result.parameters["friction_deg"] - 30.0) < 1e-9
        shown = dialog._output.toPlainText()
        assert "kPa" in shown and "_mpa" not in shown and "_deg" not in shown, shown
        dialog.deleteLater()
    finally:
        _close(w)


def test_calibration_result_shows_no_internal_keys() -> None:
    """RF-8: the calibration summary names parameters, not dictionary keys."""

    from ogr_data.core import states as st
    from ogr_data.gui.calibration_dialog import CalibrationDialog

    app, w = _window()
    try:
        w.set_failure_states([st.FailureState(points=[st.TestPoint(0, 40.3), st.TestPoint(100, 409), st.TestPoint(200, 778)])])
        dialog = CalibrationDialog(w, w._project, w._current, "kPa")
        dialog.strength.setCurrentIndex(dialog.strength.findData("mohr_coulomb"))
        text = dialog.output.text()
        assert dialog.result is not None
        assert "_" not in text.split("<br>")[0] and "deg" not in text, text
        assert "φ" in text
        dialog.deleteLater()
    finally:
        _close(w)
