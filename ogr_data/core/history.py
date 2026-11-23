"""Undo / redo of project edits (spec 023), without Qt.

The history keeps STATES (``Project.to_dict()`` snapshots), not commands:
the window records the project after every edit and the API after every
operation that edits; a step is the pair (before, after) and its text is
deduced by comparing the two (:func:`describe`). Consecutive edits of the
same thing (the same field of the same material) merge into one step
while the group is open, so typing "45" or ten clicks on a spin box
arrow is one step.

States are compared through :func:`comparable`: the selection and the
display unit are not edits, and floats are rounded to 10 significant
digits because the form returns values that went through the display
unit.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any

from .models import CRITERIA

DEFAULT_LIMIT = 100
IGNORED_KEYS = ("selected", "stress_unit", "format")


def snapshot(project) -> dict:
    """A detached state of a project (to_dict shares table rows with the material)."""

    return copy.deepcopy(project.to_dict())


def _round(value: Any) -> Any:
    if isinstance(value, float):
        if value == 0.0 or not math.isfinite(value):
            return value
        return float(f"{value:.10g}")
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round(v) for v in value]
    return value


def comparable(state: dict) -> dict:
    return _round({k: v for k, v in state.items() if k not in IGNORED_KEYS})


def _param_label(criterion: str, key: str) -> str:
    crit = CRITERIA.get(criterion)
    if crit is not None:
        for f in crit.fields:
            if f.key == key:
                return f.label
    return key


def describe(before: dict, after: dict) -> tuple[str, tuple | None]:
    """(text, key) of the edit that turns ``before`` into ``after``.

    The key identifies edits that may merge (same field of the same
    material); None for edits that never merge.
    """

    b, a = comparable(before), comparable(after)
    bm, am = b.get("materials", []), a.get("materials", [])
    if len(am) > len(bm):
        names = {m["name"] for m in bm}
        new = next((m["name"] for m in am if m["name"] not in names), am[-1]["name"])
        return f"Add Material '{new}'", None
    if len(am) < len(bm):
        names = {m["name"] for m in am}
        gone = next((m["name"] for m in bm if m["name"] not in names), "")
        return f"Delete Material '{gone}'", None
    changed = [i for i, (x, y) in enumerate(zip(bm, am)) if x != y]
    if len(changed) > 1:
        return "Edit Materials", None
    if changed:
        i = changed[0]
        x, y = bm[i], am[i]
        if x["criterion"] != y["criterion"]:
            return f"Change Criterion to {CRITERIA[y['criterion']].label}", ("criterion", i)
        if x["application"] != y["application"]:
            return "Change Application", ("application", i)
        if x["parameters"] != y["parameters"]:
            keys = [k for k in y["parameters"] if x["parameters"].get(k) != y["parameters"].get(k)]
            if len(keys) == 1:
                return f"Change {_param_label(y['criterion'], keys[0])}", ("param", i, keys[0])
            return "Change Parameters", None
        if x["sig3max_mpa"] != y["sig3max_mpa"]:
            return "Change sig3max", ("sig3max", i)
        if x["name"] != y["name"]:
            return f"Rename Material '{x['name']}' to '{y['name']}'", ("name", i)
        for key, text in (("failure_states", "Edit Failure States"), ("test_simulations", "Edit Test Simulations"),
                          ("stress_paths", "Edit Stress Paths")):
            if x[key] != y[key]:
                return text, None
        if x["stiffness"] != y["stiffness"]:
            keys = [k for k in y["stiffness"] if x["stiffness"].get(k) != y["stiffness"].get(k)]
            return "Change Stiffness", ("stiffness", i, tuple(keys))
        if x["color"] != y["color"]:
            return "Change Color", None
        if x["symbol"] != y["symbol"]:
            return "Change Symbol", None
        if x["visible"] != y["visible"]:
            return ("Show Material" if y["visible"] else "Hide Material"), None
        return "Edit Material", None
    if b.get("title") != a.get("title"):
        return "Change Project Title", ("title",)
    if b.get("graph_options") != a.get("graph_options"):
        return "Change Graph Options", None
    return "Edit", None


@dataclass
class Step:
    text: str
    key: tuple | None
    before: dict
    after: dict


class History:
    """Undo / redo stacks over project states."""

    def __init__(self, state: dict, limit: int = DEFAULT_LIMIT) -> None:
        self.limit = max(1, int(limit))
        self.reset(state)

    def reset(self, state: dict) -> None:
        """A new history starting (and saved) at ``state`` (new project, open)."""

        self.current = state
        self._current_cmp = comparable(state)
        self.undo_steps: list[Step] = []
        self.redo_steps: list[Step] = []
        self._open = False
        self._saved_cmp = self._current_cmp

    # ------------------------------------------------------------ recording

    def record(self, state: dict, text: str | None = None) -> Step | None:
        """Record ``state`` as the result of an edit; None if nothing changed."""

        cmp = comparable(state)
        if cmp == self._current_cmp:
            self.current = state  # same edit-wise; keep the newest (selection)
            return None
        label, key = describe(self.current, state)
        if text is not None:
            label, key = text, None
        top = self.undo_steps[-1] if self.undo_steps else None
        if self._open and key is not None and top is not None and top.key == key:
            top.after = state
            step = top
            if comparable(top.before) == cmp:  # the merged edits came back to the start
                self.undo_steps.pop()
                step = None
        else:
            step = Step(label, key, self.current, state)
            self.undo_steps.append(step)
            if len(self.undo_steps) > self.limit:
                del self.undo_steps[0]
        self.redo_steps.clear()
        self.current, self._current_cmp = state, cmp
        self._open = key is not None
        return step

    def rebase(self, state: dict) -> None:
        """Take ``state`` as current without a step (no edit: rounding, a preference)."""

        self.current, self._current_cmp = state, comparable(state)

    def close_group(self) -> None:
        """The next edit starts a new step even if it touches the same field."""

        self._open = False

    # ------------------------------------------------------------ moving

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_steps)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_steps)

    @property
    def undo_text(self) -> str:
        return self.undo_steps[-1].text if self.undo_steps else ""

    @property
    def redo_text(self) -> str:
        return self.redo_steps[-1].text if self.redo_steps else ""

    def undo(self) -> dict | None:
        """The state to restore (a copy), or None."""

        if not self.undo_steps:
            return None
        step = self.undo_steps.pop()
        self.redo_steps.append(step)
        self._open = False
        self.rebase(step.before)
        return copy.deepcopy(step.before)

    def redo(self) -> dict | None:
        if not self.redo_steps:
            return None
        step = self.redo_steps.pop()
        self.undo_steps.append(step)
        self._open = False
        self.rebase(step.after)
        return copy.deepcopy(step.after)

    def texts(self) -> dict[str, list[str]]:
        return {"undo": [s.text for s in reversed(self.undo_steps)], "redo": [s.text for s in reversed(self.redo_steps)]}

    # ------------------------------------------------------------ saved point

    def mark_saved(self) -> None:
        self._saved_cmp = self._current_cmp

    @property
    def modified(self) -> bool:
        return self._current_cmp != self._saved_cmp
