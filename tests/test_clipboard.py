"""Spec 005: clipboard contract."""

from __future__ import annotations

from ogr_data.core import clipboard
from ogr_data.core.models import CRITERIA, defaults


def test_round_trip():
    params = defaults("generalized_hoek_brown")
    params["sigci"] = 50000.0
    computed = {"mb": 1.234, "s": 0.0039, "c_mpa": 1.4941}
    text = clipboard.material_text("Granite", "generalized_hoek_brown", params, computed)
    assert text.startswith(clipboard.PREFIX)
    payload = clipboard.parse_material(text)
    assert payload is not None
    assert payload.name == "Granite"
    assert payload.criterion == "generalized_hoek_brown"
    assert payload.parameters["sigci"] == 50000.0
    assert payload.computed["c_mpa"] == 1.4941


def test_all_ten_criteria_round_trip():
    for key in CRITERIA:
        params = defaults(key)
        text = clipboard.material_text("M", key, params)
        payload = clipboard.parse_material(text)
        assert payload is not None and payload.criterion == key


def test_non_material_text_returns_none():
    assert clipboard.parse_material("hello world") is None
    assert clipboard.parse_material("") is None
    assert clipboard.parse_material("OGR-DATA-MATERIAL") is None  # no colon


def test_bad_payload_raises_clear_error():
    try:
        clipboard.parse_material(clipboard.PREFIX + "not json")
    except ValueError as exc:
        assert "invalid" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    try:
        clipboard.parse_material(clipboard.PREFIX + '{"format": "other/9"}')
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    try:
        clipboard.parse_material(
            clipboard.PREFIX + '{"format": "ogr-material/1", "criterion": "nope", "parameters": {}}'
        )
    except ValueError as exc:
        assert "unknown criterion" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_unknown_criterion_rejected_on_serialize():
    try:
        clipboard.material_text("X", "not_a_criterion", {})
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_tabular_data_lists_all_parameters():
    params = defaults("mohr_coulomb")
    text = clipboard.tabular_data("mohr_coulomb", params, {"sigc_mpa": 0.5})
    lines = text.split("\n")
    assert lines[0].startswith("criterion\t")
    for key in params:
        assert any(line.startswith(f"{key}\t") for line in lines)
    assert any(line.startswith("sigc_mpa\t0.5") for line in lines)


def test_gui_copy_buttons_offscreen():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
    app.processEvents()
    w._name_edit.setText("Test granite")
    # The first clipboard write after earlier GUI tests can be lost on
    # Windows (previous owner window destroyed); rewrite until it lands.
    import time

    text = ""
    for _ in range(40):
        w._copy_material()
        app.processEvents()
        text = QApplication.clipboard().text()
        if text:
            break
        time.sleep(0.025)
    payload = clipboard.parse_material(text)
    assert payload is not None and payload.name == "Test granite"
    w._copy_data()
    assert "sigci" in QApplication.clipboard().text()
    w._copy_plot_image()
    # Same Windows clipboard race for the image write.
    pm = QApplication.clipboard().pixmap()
    for _ in range(40):
        if not pm.isNull():
            break
        w._copy_plot_image()
        app.processEvents()
        pm = QApplication.clipboard().pixmap()
        time.sleep(0.025)
    assert not pm.isNull()
