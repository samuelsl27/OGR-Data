# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025c: menus and Windows conventions.

Invariants:

- at most 9 menus, none with a single entry, every window action in one
  (rule 3 of AGENTS.md), the established action names kept;
- every menu entry has an Alt accelerator, never repeated inside a menu, in
  English and in Spanish; the standard shortcuts are there;
- Save writes to the project's file (Save As only without one); recent
  projects are remembered and a vanished one is dropped, said in the
  status bar (no modal);
- Supr deletes in the materials tree and never steals it from a field;
- the window title names the file (or Untitled).
"""

from __future__ import annotations

import os
import tempfile

from ogr_data.gui.accelerators import assign, plain


# ---------------------------------------------------------------- T1


def test_accelerators_are_unique_per_menu() -> None:
    from PySide6.QtWidgets import QApplication, QMenu

    QApplication.instance() or QApplication([])
    for texts in (
        ["New Project", "Open…", "Save", "Save As…", "Import .roc…", "Exit"],
        ["Nuevo proyecto", "Abrir…", "Guardar", "Guardar como…", "Importar .roc…", "Salir"],
        ["Undo", "Undo Change GSI", "Copy material", "Copy data", "Copy plot", "Delete"],
    ):
        menu = QMenu()
        actions = [menu.addAction(text) for text in texts]
        menu.addSeparator()
        assign(menu)
        letters = []
        for action, text in zip(actions, texts):
            shown = action.text()
            assert plain(shown) == text, (shown, text)
            assert shown.count("&") == 1, shown
            letters.append(shown[shown.index("&") + 1].lower())
        assert len(set(letters)) == len(letters), list(zip(texts, letters))
        # a second pass keeps the letters (texts already marked)
        before = [a.text() for a in actions]
        assign(menu)
        assert [a.text() for a in actions] == before


def test_word_initials_come_first() -> None:
    from PySide6.QtWidgets import QApplication, QMenu

    QApplication.instance() or QApplication([])
    menu = QMenu()
    save, save_as = menu.addAction("Save"), menu.addAction("Save As…")
    assign(menu)
    assert save.text() == "&Save" and save_as.text() == "Save &As…"


# ---------------------------------------------------------------- T2-T6: the window


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.ask_unsaved = lambda: "discard"
    w.resize(1366, 768)
    w.show()
    app.processEvents()
    return app, w


def _close(w) -> None:
    w.ask_unsaved = lambda: "discard"
    w.close()
    w.deleteLater()


def _menus(w) -> dict:
    return {plain(a.text()): a.menu() for a in w.menuBar().actions()}


def _entries(menu) -> list[str]:
    return [plain(a.text()) for a in menu.actions() if not a.isSeparator()]


def test_eight_menus_none_with_one_entry() -> None:
    """RF-1, RF-3: the grouped menus, with the established action names."""

    app, w = _window()
    try:
        menus = _menus(w)
        assert list(menus) == ["File", "Edit", "View", "Materials", "Tests", "Analysis", "Report", "Help"]
        assert all(len(_entries(m)) >= 2 for m in menus.values()), {k: _entries(m) for k, m in menus.items()}
        assert _entries(menus["Tests"]) == [
            "Define Failure States…", "Define Stress Paths…", "Define Test Simulations…", "Compute", "Calibrate…",
        ]
        assert _entries(menus["Report"]) == ["Report Generator…", "Add View To Report", "Manage Report View…"]
        assert "Material Database…" in _entries(menus["Materials"])
    finally:
        _close(w)


def test_every_window_action_is_in_the_menu_bar() -> None:
    """RF-2: sidebar buttons and the tree's context menu have a menu-bar entry."""

    from PySide6.QtWidgets import QPushButton, QScrollArea

    app, w = _window()
    try:
        in_bar = set()
        for menu in _menus(w).values():
            in_bar |= set(_entries(menu))
            for action in menu.actions():
                if action.menu() is not None:
                    in_bar |= set(_entries(action.menu()))
        sidebar = w.findChild(QScrollArea, "sidebar").widget()
        buttons = {b.text() for b in sidebar.findChildren(QPushButton) if b.text() and b.isVisibleTo(sidebar)}
        buttons -= {"Pick…", "Erm"}  # per-field pickers, not window actions
        buttons -= {"Duplicate", "Delete"}  # short labels of Duplicate / Delete Material
        assert buttons <= in_bar, sorted(buttons - in_bar)
        for name in ("Color…", "Automatic color", "Symbol", "Duplicate Material", "Delete Material"):
            assert name in in_bar, name
    finally:
        _close(w)


def test_shortcuts_and_accelerators_in_both_languages() -> None:
    """RF-4: standard shortcuts; one Alt letter per entry, unique in each menu, EN and ES."""

    from PySide6.QtGui import QKeySequence

    from ogr_data.gui import i18n

    for language in ("en", "es"):
        i18n.set_language(language)
        app, w = _window()
        try:
            def keys(action):
                return {s.toString() for s in action.shortcuts()}

            assert QKeySequence(QKeySequence.StandardKey.New).toString() in keys(w._new_act)
            assert QKeySequence(QKeySequence.StandardKey.Open).toString() in keys(w._open_act)
            assert QKeySequence(QKeySequence.StandardKey.Save).toString() in keys(w._save_act)
            assert "Ctrl+Shift+S" in keys(w._save_as_act)
            assert "F5" in keys(w._compute_act) and "F1" in keys(w._shortcuts_act)
            for title in [a.text() for a in w.menuBar().actions()]:
                assert title.count("&") == 1, title
            menus = [a.menu() for a in w.menuBar().actions()]
            bar_letters = [t[t.index("&") + 1].lower() for t in (a.text() for a in w.menuBar().actions())]
            assert len(set(bar_letters)) == len(bar_letters), bar_letters
            for menu in menus:
                texts = [a.text() for a in menu.actions() if not a.isSeparator()]
                assert all(t.count("&") == 1 for t in texts), texts
                letters = [t[t.index("&") + 1].lower() for t in texts]
                assert len(set(letters)) == len(letters), texts
        finally:
            _close(w)
            i18n.set_language("en")


def test_f1_lists_the_shortcuts() -> None:
    """RF-9: a non-modal list generated from the menus."""

    app, w = _window()
    try:
        w._shortcuts_act.trigger()
        app.processEvents()
        dialog = w._shortcuts_dialog
        assert dialog.isVisible() and not dialog.isModal()
        rows = dialog.rows()
        assert ("Save", "Ctrl+S") in rows and ("Compute", "F5") in rows
        dialog.close()
    finally:
        _close(w)


def test_save_writes_to_the_project_file_and_title_names_it() -> None:
    """RF-5, RF-8, RF-10: Save As only without a file; the title names the file."""

    app, w = _window()
    folder = tempfile.mkdtemp()
    try:
        assert "Open…" in _entries(_menus(w)["File"])
        assert w.windowTitle().replace("[*]", "") == "Untitled - OGR Data"
        asked = []
        w._ask_save_path = lambda: asked.append(True) or os.path.join(folder, "slope.ogrdata")
        assert w._save_project() and asked == [True]
        assert w.windowTitle().replace("[*]", "") == "slope.ogrdata - OGR Data"
        w.set_project_title("Portal")
        assert w.windowTitle().replace("[*]", "") == "slope.ogrdata (Portal) - OGR Data"
        assert w._save_project() and asked == [True]  # no second dialog
        # a language switch keeps the file (the new window saves to it too)
        from ogr_data.gui import i18n

        w2 = w.set_language("es")
        try:
            assert w2._file_path == w._file_path
            assert w2.windowTitle().replace("[*]", "") == "slope.ogrdata (Portal) - OGR Data"
        finally:
            i18n.set_language("en")
            w2.ask_unsaved = lambda: "discard"
            w2.close()
            w2.deleteLater()
        w._new_project(confirm=False)
        assert w.windowTitle().replace("[*]", "") == "Untitled - OGR Data"
    finally:
        _close(w)


def test_recent_projects() -> None:
    """RF-6: last first, at most 8, a vanished one is dropped with a status-bar note."""

    from ogr_data.gui.settings import app_settings

    app, w = _window()
    folder = tempfile.mkdtemp()
    try:
        app_settings().remove("recent_projects")
        paths = []
        for i in range(10):
            path = os.path.join(folder, f"p{i}.ogrdata")
            assert w.save_project_to(path)
            paths.append(path)
        recent = w.recent_projects()
        assert recent == list(reversed(paths))[:8]
        w._rebuild_recent_menu()
        assert _entries(w._recent_menu)[0].endswith("p9.ogrdata")
        os.remove(paths[9])
        w.open_project_file(paths[9])
        assert paths[9] not in w.recent_projects()
        assert "p9.ogrdata" in w.statusBar().currentMessage()
        w.open_project_file(paths[3])
        assert w.recent_projects()[0] == paths[3] and w._file_path == paths[3]
    finally:
        app_settings().remove("recent_projects")
        _close(w)


def test_delete_key_in_the_tree_only() -> None:
    """RF-7: Supr deletes the selected material from the tree, never from a field."""

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    app, w = _window()
    try:
        w._add_material("rock")
        app.processEvents()
        assert len(w._project.materials) == 2
        w._name_edit.setFocus()
        app.processEvents()
        QTest.keyClick(w._name_edit, Qt.Key.Key_Delete)
        assert len(w._project.materials) == 2
        w._tree.setFocus()
        app.processEvents()
        QTest.keyClick(w._tree, Qt.Key.Key_Delete)
        app.processEvents()
        assert len(w._project.materials) == 1
        QTest.keyClick(w._tree, Qt.Key.Key_Delete)  # the last one stays
        assert len(w._project.materials) == 1
    finally:
        _close(w)
