"""Spec 023: undo / redo of project edits and unsaved changes."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from ogr_data.core import history as hist
from ogr_data.core import project as projects
from ogr_data.core import states as st
from ogr_data.core.models import defaults
from ogr_data.gui.accelerators import plain

# ------------------------------------------------------------------ core


def _rich_project(n: int = 3) -> projects.Project:
    p = projects.Project.new()
    for i in range(n - 1):
        p.add("rock" if i % 2 else "soil")
    for m in p.materials:
        m.failure_states.append(st.FailureState(name="S", points=[st.TestPoint(float(k), 3.0 * k + 100.0) for k in range(50)]))
    p.title = "Rich"
    return p


def test_snapshot_round_trip_is_identity() -> None:
    p = _rich_project(5)
    p.materials[1].parameters["sigci"] = 12345.678
    state = hist.snapshot(p)
    again = hist.snapshot(projects.Project.from_dict(state))
    assert again == state
    # detached: editing the project does not touch the snapshot (table rows included)
    p.materials[0].parameters["peak_cohesion"] = 1.0
    assert state["materials"][0]["parameters"]["peak_cohesion"] != 1.0


def test_describe_and_merge() -> None:
    p = projects.Project.new()
    h = hist.History(hist.snapshot(p))
    p.materials[0].parameters["peak_cohesion"] = 10.0
    h.record(hist.snapshot(p))
    p.materials[0].parameters["peak_cohesion"] = 11.0
    h.record(hist.snapshot(p))  # same field, group open: merged
    assert len(h.undo_steps) == 1 and h.undo_text.startswith("Change ")
    h.close_group()
    p.materials[0].parameters["peak_cohesion"] = 12.0
    h.record(hist.snapshot(p))
    assert len(h.undo_steps) == 2
    p.add("rock")
    h.record(hist.snapshot(p))
    assert h.undo_text == "Add Material 'Rock'"
    # selection and display unit are not edits
    p.selected, p.stress_unit = 1, "MPa"
    assert h.record(hist.snapshot(p)) is None
    # undo / redo and the redo branch
    before = h.undo()
    assert len(before["materials"]) == 1 and h.can_redo and h.redo_text == "Add Material 'Rock'"
    assert len(h.redo()["materials"]) == 2
    h.undo()
    p = projects.Project.from_dict(h.current)
    p.materials[0].name = "Other"
    h.record(hist.snapshot(p))
    assert not h.can_redo and h.undo_text == "Rename Material 'Material' to 'Other'"
    # merged edits that come back to the start leave no step
    h.close_group()
    count = len(h.undo_steps)
    p.materials[0].parameters["peak_friction"] = 31.0
    h.record(hist.snapshot(p))
    p.materials[0].parameters["peak_friction"] = defaults("mohr_coulomb")["peak_friction"]
    h.record(hist.snapshot(p))
    assert len(h.undo_steps) == count


def test_limit_and_saved_point() -> None:
    p = projects.Project.new()
    h = hist.History(hist.snapshot(p), limit=5)
    for k in range(8):
        h.close_group()
        p.materials[0].parameters["peak_cohesion"] = float(k)
        h.record(hist.snapshot(p))
    assert len(h.undo_steps) == 5 and h.modified
    h.mark_saved()
    assert not h.modified
    h.undo()
    assert h.modified
    h.redo()
    assert not h.modified


def test_snapshot_is_fast() -> None:
    p = _rich_project(20)
    start = time.perf_counter()
    state = hist.snapshot(p)
    hist.comparable(state)
    assert time.perf_counter() - start < 0.05


# ------------------------------------------------------------------ window


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._set_stress_unit("kPa")
    w._history.reset(w._state())
    w._update_history_ui()
    return app, w


def _cmp(w) -> dict:
    return hist.comparable(w._state())


def test_window_field_criterion_and_grouping() -> None:
    app, w = _window()
    try:
        assert not w._undo_act.isEnabled() and not w._redo_act.isEnabled() and not w.isWindowModified()
        start = _cmp(w)
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        app.processEvents()
        assert plain(w._undo_act.text()).startswith("Undo Change Criterion")
        after_criterion = _cmp(w)
        gsi = w._widgets["gsi"]
        for value in (51.0, 52.0, 53.0, 45.0):  # typing / arrow clicks in one field: one step
            gsi.setValue(value)
        assert len(w._history.undo_steps) == 2 and plain(w._undo_act.text()) == "Undo Change GSI"
        gsi.editingFinished.emit()  # leaving the field closes the group
        gsi.setValue(40.0)
        assert len(w._history.undo_steps) == 3
        w.undo()
        assert w._widgets["gsi"].value() == 45.0 and w._redo_act.isEnabled()
        w.undo()
        assert _cmp(w) == after_criterion and w._widgets["gsi"].value() == 50.0
        w.undo()
        assert _cmp(w) == start and w._criterion_combo.currentData() == "mohr_coulomb"
        assert not w._undo_act.isEnabled() and not w.isWindowModified()
        w.redo()
        w.redo()
        assert w._widgets["gsi"].value() == 45.0
        w._widgets["mi"].setValue(12.0)  # a new edit drops the redo branch
        assert not w._redo_act.isEnabled()
    finally:
        w.deleteLater()


def test_window_material_actions() -> None:
    app, w = _window()
    try:
        w._add_material("rock")
        assert plain(w._undo_act.text()) == "Undo Add Material 'Rock'" and len(w._project.materials) == 2
        w._duplicate_material()
        assert len(w._project.materials) == 3
        w._name_edit.setText("Granite")
        w._name_edit.editingFinished.emit()
        assert plain(w._undo_act.text()).startswith("Undo Rename Material")
        w._set_material_color("#123456")
        assert plain(w._undo_act.text()) == "Undo Change Color"
        item = w._tree.topLevelItem(w._current)
        from PySide6.QtCore import Qt

        item.setCheckState(0, Qt.CheckState.Unchecked)
        assert plain(w._undo_act.text()) == "Undo Hide Material"
        w._delete_material()
        assert plain(w._undo_act.text()).startswith("Undo Delete Material") and len(w._project.materials) == 2
        w.undo()
        assert len(w._project.materials) == 3 and w._project.materials[w._current].name == "Granite"
        assert w._tree.topLevelItemCount() == 3
        for _ in range(5):
            w.undo()
        assert len(w._project.materials) == 1 and not w._undo_act.isEnabled()
        # selecting another material is not an edit
        w.redo()
        steps = len(w._history.undo_steps)
        w._tree.setCurrentItem(w._tree.topLevelItem(0))
        app.processEvents()
        assert len(w._history.undo_steps) == steps
    finally:
        w.deleteLater()


def test_window_dialog_like_edits() -> None:
    app, w = _window()
    try:
        w.set_failure_states([st.FailureState(name="State 1", points=[st.TestPoint(0.0, 100.0)])])
        assert plain(w._undo_act.text()) == "Undo Edit Failure States"
        from ogr_data.core import fitting

        w.apply_fit_parameters(fitting.FitResult("mohr_coulomb", fitting.TRIAXIAL, fitting.LINEAR,
                                                 {"cohesion_mpa": 2.0, "friction_deg": 35.0}, 0.0))
        assert w._undo_act.isEnabled() and abs(w._params()["peak_cohesion"] - 2000.0) < 1e-6
        w.undo()
        assert w._params()["peak_cohesion"] != 2000.0 and len(w._current_material().failure_states) == 1
        # a pick is a step
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        w._close_history_group()
        w.pick_value = lambda key: 55.0
        field = next(f for f in w._criterion().fields if f.key == "gsi")
        w._pick(field, w._widgets["gsi"])
        assert plain(w._undo_act.text()) == "Undo Change GSI"
        # sigma3max and the application
        w._sig3max.setValue(1000.0)
        assert plain(w._undo_act.text()) == "Undo Change sig3max"
        w._application_combo.setCurrentIndex(w._application_combo.findData("tunnel"))
        assert plain(w._undo_act.text()) == "Undo Change Application"
        w.undo()
        assert w._application_combo.currentData() == "custom" and w._sig3max.value() == 1000.0
        # project title: one step
        w.set_project_title("Portal")  # spec 025b: File > Project Settings
        assert plain(w._undo_act.text()) == "Undo Change Project Title"
        w.undo()
        assert w._project.title == ""
        # the display unit is a preference: no step, values kept
        steps = len(w._history.undo_steps)
        w._set_stress_unit("MPa")
        assert len(w._history.undo_steps) == steps
        w.undo()
        assert w._stress_unit == "MPa" and w._sig3max.suffix() == " MPa"
    finally:
        w._set_stress_unit("kPa")
        w.deleteLater()


def test_window_shortcuts() -> None:
    from PySide6.QtGui import QKeySequence

    app, w = _window()
    try:
        assert w._undo_act.shortcut() == QKeySequence(QKeySequence.StandardKey.Undo)
        assert {s.toString() for s in w._redo_act.shortcuts()} == {"Ctrl+Y", "Ctrl+Shift+Z"}
        edit_menu = next(a.menu() for a in w.menuBar().actions() if plain(a.text()) == "Edit")
        assert edit_menu.actions()[:2] == [w._undo_act, w._redo_act]
    finally:
        w.deleteLater()


def test_window_unsaved_changes() -> None:
    app, w = _window()
    try:
        assert "[*]" in w.windowTitle() and not w.isWindowModified()
        w._widgets["peak_cohesion"].setValue(50.0)
        assert w.isWindowModified()
        with tempfile.TemporaryDirectory() as tmp:
            assert w.save_project_to(str(Path(tmp) / "p"))
            assert not w.isWindowModified() and (Path(tmp) / "p.ogrdata").is_file()
        assert w._undo_act.isEnabled()  # saving keeps the history
        w.undo()
        assert w.isWindowModified()
        w.redo()
        assert not w.isWindowModified()
        # new / load ask only when there are changes
        w._widgets["peak_cohesion"].setValue(60.0)
        asked = []
        w.ask_unsaved = lambda: asked.append(1) or "cancel"
        w._new_project()
        assert asked and w._params()["peak_cohesion"] == 60.0  # cancelled
        w.ask_unsaved = lambda: "save"
        w._save_project = lambda: False  # the save dialog cancelled: stay
        w._new_project()
        assert w._params()["peak_cohesion"] == 60.0
        w.ask_unsaved = lambda: "discard"
        w._new_project()
        assert w._params()["peak_cohesion"] != 60.0 and not w.isWindowModified() and not w._undo_act.isEnabled()
        asked.clear()
        w.ask_unsaved = lambda: asked.append(1) or "cancel"
        assert w._confirm_discard() and not asked  # nothing to save: no question

        class Event:
            accepted = None

            def accept(self):
                self.accepted = True

            def ignore(self):
                self.accepted = False

        w._widgets["peak_cohesion"].setValue(70.0)
        event = Event()
        w.closeEvent(event)
        assert event.accepted is False
        w.ask_unsaved = lambda: "discard"
        w.closeEvent(event)
        assert event.accepted is True
    finally:
        w.deleteLater()
