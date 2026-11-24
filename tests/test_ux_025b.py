# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025b: the main window with the results in view.

T1 — the suite never writes the user's settings. Before 025b the tests
wrote theme, stress unit and language into the real
``HKCU\\Software\\OpenGeoRock\\OGR-Data`` (rule 5 of AGENTS.md), and 025b
adds the saved window state. Invariants:

- every ``QSettings`` of the program comes from ``gui.settings.app_settings``;
- under ``tests/_runner.py`` that is an INI file in a temporary folder,
  never the registry (these tests only hold under the runner).
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_suite_settings_live_in_a_temporary_ini_file() -> None:
    from PySide6.QtCore import QSettings

    from ogr_data.gui.settings import app_settings

    settings = app_settings()
    assert settings.format() == QSettings.Format.IniFormat
    path = Path(settings.fileName()).resolve()
    assert path.is_relative_to(Path(tempfile.gettempdir()).resolve()), path
    assert "HKEY" not in settings.fileName()


def test_main_window_uses_the_program_settings() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow
    from ogr_data.gui.settings import app_settings

    QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert w._settings.fileName() == app_settings().fileName()
    finally:
        w.deleteLater()


def test_no_settings_are_built_anywhere_else() -> None:
    """A QSettings built by hand would go back to the registry."""

    offenders = []
    for folder in ("ogr_data", "tests"):
        for path in (ROOT / folder).rglob("*.py"):
            if path.name == "settings.py" and path.parent.name == "gui":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if name == "QSettings":
                        offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, offenders


# ---------------------------------------------------------------- T2-T9: the window


def _window(width: int = 1366, height: int = 768):
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.ask_unsaved = lambda: "discard"  # no modal question without a screen
    w._set_stress_unit("kPa")
    w.resize(width, height)
    w.show()
    app.processEvents()
    return app, w


def _close(w) -> None:
    w.ask_unsaved = lambda: "discard"
    w.close()
    w.deleteLater()


def _select(app, w, criterion: str) -> None:
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData(criterion))
    app.processEvents()


def test_results_panel_is_in_view_on_the_right() -> None:
    """RF-1: the results show without scrolling, right of the graphs."""

    from PySide6.QtCore import QPoint, Qt

    app, w = _window()
    try:
        _select(app, w, "generalized_hoek_brown")
        dock, panel = w._results_dock, w._results
        assert dock.isVisible() and w.dockWidgetArea(dock) == Qt.DockWidgetArea.RightDockWidgetArea
        labels = [label for label, _ in panel.rows()]
        assert labels == ["mb", "s", "a", "σt", "σc", "σcm", "c", "φ", "Erm"]  # spec 025e symbols
        # the whole block, button included, lies inside the window: nothing to scroll to
        bottom = panel.copy_button.mapTo(w, QPoint(0, panel.copy_button.height())).y()
        assert bottom <= w.height(), (bottom, w.height())
        graphs_right = w._graph_tabs.mapTo(w, QPoint(w._graph_tabs.width(), 0)).x()
        assert dock.mapTo(w, QPoint(0, 0)).x() >= graphs_right - 1
    finally:
        _close(w)


def test_results_follow_the_parameters() -> None:
    """RF-2: editing a parameter updates the panel with the graphs."""

    app, w = _window()
    try:
        _select(app, w, "generalized_hoek_brown")
        before = dict(w._results.rows())["mb"]
        w._widgets["gsi"].setValue(w._widgets["gsi"].value() + 20.0)
        app.processEvents()
        assert dict(w._results.rows())["mb"] != before
        assert w._current_material().name in w._results._heading.text()
    finally:
        _close(w)


def test_panel_button_copies_the_material() -> None:
    """RF-3: the panel's button does what Edit > Copy material does."""

    from ogr_data.core import clipboard

    from PySide6.QtWidgets import QApplication

    app, w = _window()
    try:
        QApplication.clipboard().setText("")
        w._results.copy_button.click()
        app.processEvents()
        assert QApplication.clipboard().text().startswith(clipboard.PREFIX)
    finally:
        _close(w)


def test_panel_and_toolbar_state_is_remembered() -> None:
    """RF-4: a hidden panel stays hidden in the next window and through a language switch."""

    from ogr_data.gui import i18n

    app, w = _window()
    w2 = w3 = None
    try:
        view = [a.text().replace("&", "") for a in w._view_menu.actions()]
        assert "Results panel" in view and "Toolbar" in view
        w._results_dock.toggleViewAction().trigger()
        app.processEvents()
        assert not w._results_dock.isVisible()
        _close(w)
        _, w2 = _window()
        assert not w2._results_dock.isVisible()
        w3 = w2.set_language("es")
        app.processEvents()
        assert not w3._results_dock.isVisible()
        w3._results_dock.toggleViewAction().trigger()
        app.processEvents()
        assert w3._results_dock.isVisible()
    finally:
        i18n.set_language("en")
        for window in (w2, w3):
            if window is not None:
                window._results_dock.setVisible(True)
                window.save_window_state()
                _close(window)


def test_sidebar_holds_only_the_material() -> None:
    """RF-5, RF-6: titled sections in order; no unit, title, file or clipboard there."""

    from PySide6.QtWidgets import QGroupBox, QLineEdit, QPushButton, QScrollArea

    app, w = _window()
    try:
        sidebar = w.findChild(QScrollArea, "sidebar").widget()
        boxes = [b.title() for b in sidebar.findChildren(QGroupBox) if b.parentWidget() is sidebar]
        assert boxes == ["Materials", "Material", "Stress range", "Parameters", w._stiffness_box.title()], boxes
        buttons = {b.text() for b in sidebar.findChildren(QPushButton)}
        assert not buttons & {"Copy material", "Copy data", "Copy plot", "Save…", "Load…", "Import .roc…"}
        assert not sidebar.isAncestorOf(w._unit_combo)
        assert "Project title" not in {e.placeholderText() for e in sidebar.findChildren(QLineEdit)}
        assert sidebar.isAncestorOf(w._name_edit) and sidebar.isAncestorOf(w._criterion_combo)
    finally:
        _close(w)


def test_toolbar_shares_the_menu_actions() -> None:
    """RF-7: the toolbar holds the same QAction objects as the menus, and the unit."""

    app, w = _window()
    try:
        bar = w._toolbar
        actions = [a for a in bar.actions() if not a.isSeparator()]
        wanted = [w._new_act, w._open_act, w._save_act, w._undo_act, w._redo_act,
                  w._copy_material_act, w._copy_data_act, w._copy_plot_act, w._compute_act]
        assert all(a in actions for a in wanted)
        in_menus = {a for m in w.menuBar().actions() for a in m.menu().actions()}
        assert all(a in in_menus for a in wanted)
        assert bar.isAncestorOf(w._unit_combo)
        w._unit_combo.setCurrentText("MPa")
        app.processEvents()
        assert w._stress_unit == "MPa"
    finally:
        w._set_stress_unit("kPa")
        _close(w)


def test_sampler_reads_in_panel_and_status_bar() -> None:
    """RF-8: the same reading in both places; no sampler, no section."""

    app, w = _window()
    try:
        _select(app, w, "generalized_hoek_brown")
        assert w._results.sampler_text() == ""
        w._stress_sampler_act.setChecked(True)
        w._sample_at("principal", 2.0)
        status = w.statusBar().currentMessage()
        assert status and w._results.sampler_text().split() == status.split()
        w._stress_sampler_act.setChecked(False)
        app.processEvents()
        assert w._results.sampler_text() == ""
    finally:
        _close(w)


def test_other_criteria_show_derived_results_or_why_not() -> None:
    """RF-9: Power Curve shows its best-fit MC (the report's rows); Mohr-Coulomb says why it has none."""

    from ogr_data.core import report
    from ogr_data.gui.i18n import localize

    app, w = _window()
    try:
        _select(app, w, "power_curve")
        from ogr_data.core.numbers import symbols

        expected = [(symbols(label), symbols(localize(value))) for label, value in report.computed_rows(w._current_material(), "kPa")]
        assert expected and w._results.rows() == expected
        _select(app, w, "mohr_coulomb")
        assert w._results.rows() == []
        assert "no derived parameters" in w._results.results_text()
    finally:
        _close(w)


def test_project_settings_set_title_and_unit() -> None:
    """RF-6: File > Project Settings holds the title (one undo step) and the unit."""

    from ogr_data.gui.project_settings_dialog import ProjectSettingsDialog

    app, w = _window()
    try:
        files = [a.text().replace("&", "") for a in w.menuBar().actions()[0].menu().actions()]
        assert "Project Settings…" in files
        dialog = ProjectSettingsDialog("", "kPa", w)
        dialog.title_edit.setText("  Portal  ")
        dialog.unit_combo.setCurrentIndex(dialog.unit_combo.findData("MPa"))
        w.apply_project_settings(dialog.title(), dialog.stress_unit())
        dialog.deleteLater()
        assert w._project.title == "Portal" and w._stress_unit == "MPa"
        assert w.windowTitle().replace("[*]", "") == "Untitled (Portal) - OGR Data"
        w.undo()
        assert w._project.title == ""
    finally:
        w._set_stress_unit("kPa")
        _close(w)
