# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025a: the four visible bugs of the UX review (2026-11-24).

Invariants protected, one per bug:

- B1: the fit dialog never shows an internal criterion key; it shows the
  translated criterion name and keeps the key as item data.
- B2: under the dark theme every plain panel (the sidebar inside its scroll
  area) is painted dark: the sheet alone left it light.
- B3: the plasticity chart of the soil classifier keeps a usable width (the
  source text wraps instead of widening the results column).
- B4: the calibration dialog opens without an error the user did not cause;
  with no failure state it says what to do and offers to define one.
"""

from __future__ import annotations

from ogr_data.core.models import CRITERIA


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_fit_dialog_shows_criterion_names_not_keys() -> None:
    from ogr_data.core import fitting
    from ogr_data.gui import i18n
    from ogr_data.gui.fit_dialog import FitDialog

    _app()
    for language in ("en", "es"):
        i18n.set_language(language)
        try:
            dialog = FitDialog()
            combo = dialog._criterion
            keys = [combo.itemData(i) for i in range(combo.count())]
            texts = [combo.itemText(i) for i in range(combo.count())]
            assert keys == list(fitting.COMPATIBILITY)
            assert texts == [i18n.tr(CRITERIA[k].label) for k in keys]
            assert not set(texts) & set(keys), texts
            dialog.deleteLater()
        finally:
            i18n.set_language("en")


def test_dark_theme_paints_the_sidebar_dark() -> None:
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QScrollArea

    from ogr_data.gui.main_window import MainWindow

    app = _app()
    light_window = QColor(app.palette().color(QPalette.ColorRole.Window))
    w = MainWindow()
    try:
        w.resize(1366, 768)
        w.show()
        w._set_theme("dark")
        app.processEvents()
        sidebar = w.findChild(QScrollArea, "sidebar").widget()
        assert sidebar.palette().color(QPalette.ColorRole.Window).name() == "#2b2b2b"
        # what is really painted: a pixel of the sidebar's margin
        pixel = sidebar.grab().toImage().pixelColor(2, 2)
        assert max(pixel.red(), pixel.green(), pixel.blue()) < 0x60, pixel.name()
        w._set_theme("light")
        app.processEvents()
        assert app.palette().color(QPalette.ColorRole.Window) == light_window
    finally:
        w._set_theme("light")
        w.ask_unsaved = lambda: "discard"
        w.close()
        w.deleteLater()


def test_soil_classifier_chart_keeps_its_width() -> None:
    from PySide6.QtWidgets import QLabel

    from ogr_data.gui.soil_classifier import SoilClassifierDialog

    app = _app()
    dialog = SoilClassifierDialog()
    try:
        dialog.show()
        app.processEvents()
        # the offscreen font is wider than Segoe UI, so the dialog's own width
        # is not checked here (1198 px with Windows fonts, measured 2026-11-24)
        assert dialog._chart.width() >= 300, dialog._chart.width()
        long_labels = [lbl for lbl in dialog.findChildren(QLabel) if len(lbl.text()) > 60]
        assert long_labels and all(lbl.wordWrap() for lbl in long_labels)
    finally:
        dialog.close()
        dialog.deleteLater()


def test_calibration_opens_without_error_and_offers_failure_states() -> None:
    from PySide6.QtCore import Qt

    from ogr_data.core import states as st
    from ogr_data.gui.calibration_dialog import CalibrationDialog
    from ogr_data.gui.main_window import MainWindow

    app = _app()
    w = MainWindow()
    try:
        dialog = CalibrationDialog(w, w._project, w._current, "kPa")
        text = dialog.output.text()
        assert "#c0392b" not in text and "non-excluded" not in text, text
        assert "Failure States" in text
        assert dialog.define_states_button.isVisibleTo(dialog)
        dialog.define_states_button.click()
        app.processEvents()
        assert dialog.wants_failure_states and dialog.result is None
        dialog.deleteLater()

        # with states, nothing selected: a hint, not an error
        w.set_failure_states([st.FailureState(points=[st.TestPoint(0, 40.3), st.TestPoint(100, 409), st.TestPoint(200, 778)])])
        dialog = CalibrationDialog(w, w._project, w._current, "kPa")
        assert not dialog.define_states_button.isVisibleTo(dialog)
        dialog.states.item(0).setCheckState(Qt.CheckState.Unchecked)
        assert "#c0392b" not in dialog.output.text()
        assert dialog.result is None
        dialog.deleteLater()
    finally:
        w.ask_unsaved = lambda: "discard"  # no modal question without a screen
        w.close()
        w.deleteLater()
