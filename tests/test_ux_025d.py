# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025d: empty states and confirmations.

Invariants:

- an empty graph, panel or list says what is missing and how to fill it;
- deleting what undo brings back asks nothing and says how to undo it;
- an action that cannot run is disabled with its reason, not refused in a
  message box after the click.
"""

from __future__ import annotations


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


def test_empty_path_graphs_say_what_is_missing() -> None:
    """RF-1: no paths, no simulations: a hint with the actions; the graphs say it too."""

    from ogr_data.core import simulation as sm

    app, w = _window()
    try:
        w._graph_tabs.setCurrentIndex(1)
        app.processEvents()
        assert w._path_hint.isVisible()
        names = {b.text() for b in w._path_hint_buttons}
        assert names == {"Define Stress Paths…", "Define Test Simulations…"}
        assert all(canvas.empty_message() for canvas in w._path_canvases.values())
        w.set_test_simulations([sm.TestSimulation(name="TC", test_type="triaxial", confining=150.0)])
        app.processEvents()
        assert not w._path_hint.isVisible()
        assert not any(canvas.empty_message() for canvas in w._path_canvases.values())
    finally:
        _close(w)


def test_animation_panel_says_what_it_needs() -> None:
    """RF-2: without computed simulations the panel says how to get one."""

    from ogr_data.core import simulation as sm

    app, w = _window()
    try:
        w._graph_tabs.setCurrentIndex(1)
        app.processEvents()
        assert w._animation.hint.isVisible() and "Compute" in w._animation.hint.text()
        w.set_test_simulations([sm.TestSimulation(name="TC", test_type="triaxial", confining=150.0)])
        app.processEvents()
        assert not w._animation.hint.isVisible()
    finally:
        _close(w)


def test_empty_item_dialogs_show_the_first_step() -> None:
    """RF-3: an empty dialog shows a hint instead of a disabled editor; Add has a text."""

    from PySide6.QtWidgets import QPushButton

    from ogr_data.gui.simulation_dialog import TestSimulationsDialog
    from ogr_data.gui.states_dialog import FailureStatesDialog, StressPathsDialog

    app, w = _window()
    try:
        for cls in (FailureStatesDialog, StressPathsDialog, TestSimulationsDialog):
            dialog = cls(w, "Material", [], "kPa", 0)
            dialog.show()
            app.processEvents()
            texts = [b.text() for b in dialog.findChildren(QPushButton)]
            assert "Add" in texts and "+" not in texts, texts
            assert dialog._empty.isVisible() and not dialog._editor.isVisible()
            assert dialog._empty.text()
            assert not any(b.isEnabled() for b in dialog._list_buttons[1:])  # nothing to delete or move
            dialog.add_item()
            app.processEvents()
            assert not dialog._empty.isVisible() and dialog._editor.isVisible()
            dialog.close()
            dialog.deleteLater()
    finally:
        _close(w)


def test_delete_asks_nothing_and_says_how_to_undo() -> None:
    """RF-4, RF-6: undoable deletions without a question, with an undo note."""

    from ogr_data.core import states as st

    app, w = _window()
    try:
        w._add_material("rock")
        name = w._current_material().name
        w._delete_material()  # no modal: this would block without a screen
        assert len(w._project.materials) == 1
        message = w.statusBar().currentMessage()
        assert name in message and "Ctrl+Z" in message
        w.undo()
        assert len(w._project.materials) == 2
        w.set_failure_states([st.FailureState(name="S1")])
        w._delete_child("state", 0)
        assert "S1" in w.statusBar().currentMessage() and "Ctrl+Z" in w.statusBar().currentMessage()
    finally:
        _close(w)


def test_unavailable_actions_are_disabled_with_a_reason() -> None:
    """RF-5: Delete Material with one material; export of an empty graph."""

    app, w = _window()
    try:
        assert len(w._project.materials) == 1
        w._update_action_states()
        assert not w._delete_material_act.isEnabled() and w._delete_material_act.toolTip()
        assert not w._delete_button.isEnabled() and w._delete_button.toolTip()
        empty = w._path_canvases["axial"]
        assert not empty.can_export() and empty.export_reason()
        assert w._principal.can_export()
        w._add_material("soil")
        w._update_action_states()
        assert w._delete_material_act.isEnabled() and w._delete_button.isEnabled()
    finally:
        _close(w)
