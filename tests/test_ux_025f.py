# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025f: help, accessibility and progress.

Invariants:

- every parameter of the registry has a sourced help text (definition and
  bibliographic reference, typical range when the source gives one), or is
  listed as pending with what is missing — never an invented one;
- every menu action has a status tip;
- every input has a label pointing at it or an accessible name, and Tab
  goes down the sidebar in reading order;
- text contrast reaches WCAG AA (4.5:1) in both themes;
- Compute with several simulations shows progress and can be cancelled;
- the soil classifier needs no Classify button; Pick… says what it opens.
"""

from __future__ import annotations


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


def test_every_menu_action_has_a_status_tip() -> None:
    """RF-2."""

    from ogr_data.gui import i18n
    from ogr_data.gui.accelerators import plain

    for language in ("en", "es"):
        i18n.set_language(language)
        app, w = _window()
        try:
            missing = []

            def walk(menu, dynamic=()):
                for action in menu.actions():
                    if action.isSeparator() or not action.isVisible():
                        continue
                    if action.menu() is not None:
                        # submenus whose entries are data (themes, languages, units, symbols, recent files)
                        if not action.statusTip():
                            missing.append(plain(action.text()))
                        continue
                    if not action.statusTip():
                        missing.append(plain(action.text()))

            for top in w.menuBar().actions():
                walk(top.menu())
            assert not missing, (language, missing)
        finally:
            _close(w)
            i18n.set_language("en")


def test_inputs_have_labels_or_names() -> None:
    """RF-3: in the sidebar and the main dialogs, every input is labelled for a screen reader."""

    from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QLabel, QLineEdit, QScrollArea

    from ogr_data.gui.calibration_dialog import CalibrationDialog
    from ogr_data.gui.fit_dialog import FitDialog
    from ogr_data.gui.project_settings_dialog import ProjectSettingsDialog
    from ogr_data.gui.simulation_dialog import TestSimulationsDialog
    from ogr_data.gui.soil_classifier import SoilClassifierDialog
    from ogr_data.gui.states_dialog import FailureStatesDialog, StressPathsDialog

    app, w = _window()
    try:
        for criterion in ("generalized_hoek_brown", "mohr_coulomb", "norsand", "barton_bandis"):
            w._criterion_combo.setCurrentIndex(w._criterion_combo.findData(criterion))
            app.processEvents()
            roots = {"sidebar": w.findChild(QScrollArea, "sidebar").widget()}
            m = w._current_material()
            roots.update({
                "calibration": CalibrationDialog(w, w._project, w._current, "kPa"),
                "fit": FitDialog(w),
                "project settings": ProjectSettingsDialog("", "kPa", w),
                "simulations": TestSimulationsDialog(w, m.name, [], "kPa", 0),
                "states": FailureStatesDialog(w, m.name, [], "kPa", 0),
                "paths": StressPathsDialog(w, m.name, [], "kPa", 0),
                "classifier": SoilClassifierDialog(w),
            })
            problems = []
            for name, root in roots.items():
                buddies = {label.buddy() for label in root.findChildren(QLabel) if label.buddy() is not None}
                inputs = [w for kind in (QLineEdit, QComboBox, QAbstractSpinBox) for w in root.findChildren(kind)]
                for widget in inputs:
                    if widget.parent() is not None and isinstance(widget.parent(), QAbstractSpinBox):
                        continue  # the line edit inside a spin box
                    if isinstance(widget, QLineEdit) and isinstance(widget.parent(), QComboBox):
                        continue
                    if widget not in buddies and not widget.accessibleName():
                        problems.append(f"{name}: {type(widget).__name__} {widget.objectName()!r}")
                for button in root.findChildren(QAbstractButton):
                    if button.metaObject().className() == "QTableCornerButton" or button in buddies:
                        continue  # a table's select-all corner; a check box named by its label
                    if not button.text() and not button.accessibleName() and button.isVisibleTo(root):
                        problems.append(f"{name}: button without text or name")
                if name != "sidebar":
                    root.deleteLater()
            assert not problems, (criterion, problems)
    finally:
        _close(w)


def test_tab_goes_down_the_sidebar() -> None:
    """RF-4: following Tab from the tree visits the sidebar inputs top to bottom."""

    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QAbstractSpinBox, QScrollArea

    app, w = _window()
    try:
        sidebar = w.findChild(QScrollArea, "sidebar").widget()
        for criterion in ("generalized_hoek_brown", "mohr_coulomb"):
            w._criterion_combo.setCurrentIndex(w._criterion_combo.findData(criterion))
            app.processEvents()
            widget, seen, positions = w._tree, set(), []
            while widget is not None and widget not in seen and len(seen) < 200:
                seen.add(widget)
                inner = isinstance(widget.parent(), QAbstractSpinBox)  # the line edit inside a spin box
                if not inner and sidebar.isAncestorOf(widget) and widget.isVisibleTo(sidebar) and widget.focusPolicy() & 0x1:
                    positions.append((widget.mapTo(sidebar, QPoint(0, 0)).y(), type(widget).__name__))
                widget = widget.nextInFocusChain()
            ys = [y for y, _ in positions]
            assert len(ys) > 10
            assert ys == sorted(ys), (criterion, positions)
    finally:
        _close(w)


def test_text_contrast_reaches_wcag_aa() -> None:
    """RF-5: text on its background, both themes (WCAG 2.1 relative luminance)."""

    from ogr_data.gui.themes import THEMES

    def luminance(color: str) -> float:
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def contrast(a: str, b: str) -> float:
        hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    pairs = {
        "light": [("#202020", "#f3f3f3"), ("#202020", "#e9e9e9"), ("#202020", "#ffffff"),
                  ("#40607a", "#f3f3f3"), ("#202020", "#fffddc")],
        "dark": [("#e0e0e0", "#2b2b2b"), ("#e0e0e0", "#3a3a3a"), ("#e0e0e0", "#353535"),
                 ("#e0e0e0", "#404040"), ("#9ab6d6", "#2b2b2b"), ("#ffffff", "#4a5a75")],
    }
    for theme, theme_pairs in pairs.items():
        for text, background in theme_pairs:
            assert text in THEMES[theme] and background in THEMES[theme], (theme, text, background)
            assert contrast(text, background) >= 4.5, (theme, text, background, contrast(text, background))


def test_compute_shows_progress_and_can_be_cancelled() -> None:
    """RF-6: several simulations: a progress dialog; Cancel stops and says so."""

    from PySide6.QtWidgets import QProgressDialog

    from ogr_data.core import simulation as sm

    app, w = _window()
    original = QProgressDialog.wasCanceled
    try:
        tests = [sm.TestSimulation(name=f"T{i}", test_type="triaxial", confining=100.0 * (i + 1)) for i in range(3)]
        w.set_test_simulations(tests)
        w.compute(report_problems=False)
        progress = w._compute_progress
        assert progress is not None and progress.maximum() == 3 and progress.minimumDuration() == 1000
        assert "3" in w.statusBar().currentMessage()
        calls = []
        QProgressDialog.wasCanceled = lambda self: calls.append(1) or len(calls) > 1
        w.compute(report_problems=False)
        message = w.statusBar().currentMessage()
        assert "1 of 3" in message, message
    finally:
        QProgressDialog.wasCanceled = original
        _close(w)


def test_classifier_is_live_and_pick_buttons_say_what_they_open() -> None:
    """RF-7, RF-8."""

    from PySide6.QtWidgets import QPushButton

    from ogr_data.gui.soil_classifier import SoilClassifierDialog

    app, w = _window()
    try:
        dialog = SoilClassifierDialog(w)
        assert "Classify" not in [b.text() for b in dialog.findChildren(QPushButton)]
        dialog._fields["sand_pct"].setValue(20.0)
        dialog._fields["fines_pct"].setValue(60.0)
        dialog._fields["ll"].setValue(40.0)
        dialog._fields["pi"].setValue(20.0)
        assert dialog._symbol.text() not in ("", "—")
        dialog.deleteLater()
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        app.processEvents()
        for key in ("sigci", "gsi", "mi", "d", "ei"):
            button = w._pick_buttons[key]
            assert button.toolTip() and "(" in button.toolTip(), key
            assert button.accessibleName().startswith("Pick")
    finally:
        _close(w)


# ---------------------------------------------------------------- RF-1: sourced help


def test_every_parameter_has_sourced_help_or_is_pending() -> None:
    """RF-1: no registry or stiffness parameter is left without help or a pending note."""

    from ogr_data.core import parameter_help as ph
    from ogr_data.core.models import CRITERIA

    sources = ph.sources()
    for entry in ph.entries():
        assert entry.definition["en"] and entry.definition["es"], entry.key
        assert entry.sources and entry.locator, entry.key
    for raw in ph._data()["parameters"]:
        assert all(s in sources for s in raw["sources"]), raw["key"]
    pending = {(c, p["key"]) for p in ph.pending() for c in p["criteria"]}
    missing = []
    for criterion, model in CRITERIA.items():
        for field in model.fields:
            if ph.help_for(criterion, field.key) is None and (criterion, field.key) not in pending:
                missing.append((criterion, field.key))
    stiffness = ["poisson", "young", "elastic_parameter", "shear_modulus", "g_ref", "p_ref", "g_exp", "ns_poisson", "g_min"]
    for key in stiffness:
        if not any(e.key == key for e in ph.entries()) and ("*", key) not in pending:
            missing.append(("stiffness", key))
    assert not missing, missing
    # what is pending says what is missing
    assert all(p["missing"] for p in ph.pending())


def test_tooltips_show_definition_unit_range_and_source() -> None:
    """RF-1: the GSI field of a GHB material, in English and Spanish."""

    from ogr_data.gui import i18n

    for language, word in (("en", "Source"), ("es", "Fuente")):
        i18n.set_language(language)
        app, w = _window()
        try:
            w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
            app.processEvents()
            tip = w._widgets["gsi"].toolTip()
            assert "Marinos" in tip and word in tip, tip
            sigci = w._widgets["sigci"].toolTip()
            assert "kPa" in sigci and "Hoek" in sigci, sigci
            assert w._stiffness_box.spins["poisson"].toolTip()
            assert w._sig3max.toolTip()
        finally:
            _close(w)
            i18n.set_language("en")
