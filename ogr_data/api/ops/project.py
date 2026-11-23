"""Projects: new, open, save, close, list, summary, settings (.ogrdata, spec 011)."""

from __future__ import annotations

import json

from ...core import project as projects
from ...core import history as hist
from ...core import units
from ..errors import Conflict, InvalidArgument, NotFound, choice
from . import operation
from ._common import material_index, number, project_summary

SUFFIX = ".ogrdata"


@operation("project_new", toolset="project", mutates=True)
def project_new(ws, title: str | None = None) -> dict:
    """Create a project with one material (as the window starts); returns its project_id."""

    project = projects.Project.new()
    if title:
        project.title = str(title)
    return project_summary(ws.add(project))


@operation("project_open", toolset="project", mutates=True)
def project_open(ws, path: str) -> dict:
    """Open a .ogrdata project file (format v1 or v2); returns its project_id."""

    p = ws.resolve(path)
    if not p.is_file():
        raise NotFound(f"{p} does not exist.")
    try:
        project = projects.load_project(p)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise InvalidArgument(f"{p.name} is not an OGR Data project: {exc}") from None
    return project_summary(ws.add(project, p))


@operation("project_save", toolset="project", mutates=True)
def project_save(ws, project_id: str | None = None, path: str | None = None, overwrite: bool = False) -> dict:
    """Save a project (.ogrdata); without path, to the file it was opened from or saved to."""

    handle = ws.get(project_id)
    if path is None:
        if handle.path is None:
            raise InvalidArgument("This project has no file yet: give a path.")
        target = handle.path
    else:
        target = ws.resolve(path)
        if target.suffix.lower() != SUFFIX:
            target = target.with_name(target.name + SUFFIX)
        if target.exists() and target != handle.path and not overwrite:
            raise Conflict(f"{target} already exists.", hint="Pass overwrite=true to replace it.")
    target.parent.mkdir(parents=True, exist_ok=True)
    projects.save_project(target, handle.project)
    handle.path = target
    handle.history.rebase(hist.snapshot(handle.project))
    handle.history.mark_saved()
    return {"project_id": handle.id, "saved_to": str(target)}


@operation("project_close", toolset="project", mutates=True)
def project_close(ws, project_id: str | None = None) -> dict:
    """Close a project (unsaved changes are lost: save first)."""

    handle = ws.close(project_id)
    return {"closed": handle.id, "open": list(ws.projects)}


@operation("project_list", toolset="project")
def project_list(ws) -> dict:
    """The open projects."""

    return {"projects": [{"project_id": h.id, "title": h.project.title, "path": str(h.path) if h.path else None,
                          "materials": len(h.project.materials)} for h in ws.projects.values()]}


@operation("project_summary", toolset="project")
def project_summary_op(ws, project_id: str | None = None) -> dict:
    """Title, file, display unit and the materials of a project."""

    return project_summary(ws.get(project_id))


@operation("project_set", toolset="project", mutates=True)
def project_set(ws, project_id: str | None = None, title: str | None = None, display_stress_unit: str | None = None,
                selected_material: str | None = None) -> dict:
    """Project title, the stress unit the window shows (kPa / MPa / ...) and the selected material."""

    handle = ws.get(project_id)
    p = handle.project
    if title is not None:
        p.title = str(title)
    if display_stress_unit is not None:
        p.stress_unit = choice("display_stress_unit", display_stress_unit, units.STRESS_FACTORS)
    if selected_material is not None:
        p.selected = material_index(p, selected_material)
    return project_summary(handle)


@operation("project_history", toolset="project", mutates=True)
def project_history(ws, project_id: str | None = None, action: str = "list", steps: int = 1) -> dict:
    """Undo or redo edits of a project, or list them; every editing operation is one step (spec 023)."""

    handle = ws.get(project_id)
    choice("action", action, ("list", "undo", "redo"))
    h = handle.history
    done = 0
    if action != "list":
        for _ in range(int(number("steps", steps, lo=1, hi=1000))):
            state = h.undo() if action == "undo" else h.redo()
            if state is None:
                break
            unit = handle.project.stress_unit  # a preference, not an edit
            handle.project = projects.Project.from_dict(state)
            handle.project.stress_unit = unit
            done += 1
    texts = h.texts()
    return {"project_id": handle.id, "action": action, "steps_done": done, "undo": texts["undo"],
            "redo": texts["redo"], "unsaved_changes": h.modified}
