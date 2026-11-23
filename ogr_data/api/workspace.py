"""Open projects under handles, the working folder and the materials database."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ..core import history as hist
from ..core.database import MaterialDatabase
from ..core.project import Material, Project
from .errors import Conflict, InvalidArgument, NotFound, unknown


def default_database_path() -> Path:
    """The user's materials database, where the window keeps it.

    The window asks Qt for GenericDataLocation; these are the same folders
    (Windows %LOCALAPPDATA%, macOS ~/Library/Application Support,
    elsewhere $XDG_DATA_HOME or ~/.local/share), so that the API sees the
    records the user saved without importing Qt.
    """

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "OpenGeoRock" / "OGR-Data" / "materials_db.json"


@dataclass
class Handle:
    id: str
    project: Project
    path: Path | None = None
    history: hist.History | None = None  # spec 023: one undo history per project

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = hist.History(hist.snapshot(self.project))

    @property
    def name(self) -> str:
        return self.project.title or (self.path.stem if self.path else "Untitled")


class Workspace:
    """Projects open in memory, without a window (spec 019)."""

    def __init__(self, workdir: str | Path | None = None, database_path: str | Path | None = None) -> None:
        self.workdir = Path(workdir).resolve() if workdir else None
        self.database_path = Path(database_path) if database_path else None
        self.projects: dict[str, Handle] = {}
        self._counter = 0
        self._database: MaterialDatabase | None = None

    # ------------------------------------------------------------ handles

    def add(self, project: Project, path: Path | None = None) -> Handle:
        self._counter += 1
        handle = Handle(f"p{self._counter}", project, path)
        self.projects[handle.id] = handle
        return handle

    def get(self, project_id: str | None) -> Handle:
        if project_id is None:
            if len(self.projects) == 1:
                return next(iter(self.projects.values()))
            if not self.projects:
                raise NotFound("No project is open.", hint="Call project_new or project_open first.")
            raise Conflict("Several projects are open: say which one with project_id.",
                           hint=f"Open: {', '.join(self.projects)}.")
        if project_id not in self.projects:
            raise unknown("project_id", project_id, self.projects)
        return self.projects[project_id]

    def close(self, project_id: str | None) -> Handle:
        handle = self.get(project_id)
        del self.projects[handle.id]
        return handle

    # ------------------------------------------------------------ files

    def resolve(self, path: str | Path) -> Path:
        """A path given by the caller: absolute, or relative to the working folder."""

        if not str(path).strip():
            raise InvalidArgument("The path is empty.")
        p = Path(os.path.expandvars(os.path.expanduser(str(path))))
        if not p.is_absolute():
            p = (self.workdir or Path.cwd()) / p
        return p

    def database(self) -> MaterialDatabase:
        if self._database is None:
            self._database = MaterialDatabase(self.database_path or default_database_path())
        return self._database


def material_index(project: Project, material) -> int:
    """Index of a material given by name, 0-based index (int or digits) or None (the selected one)."""

    if material is None:
        return project.selected if 0 <= project.selected < len(project.materials) else 0
    names = [m.name for m in project.materials]
    if isinstance(material, int) or (isinstance(material, str) and material.strip().isdigit() and material.strip() not in names):
        index = int(material)
        if not 0 <= index < len(project.materials):
            raise NotFound(f"There is no material {index}: the project has {len(project.materials)} (0-based).",
                           hint=f"Materials: {', '.join(repr(n) for n in names)}.")
        return index
    if material in names:
        return names.index(material)
    lowered = [n.lower() for n in names]
    if str(material).lower() in lowered:
        return lowered.index(str(material).lower())
    raise unknown("material", material, names)


def get_material(project: Project, material) -> tuple[int, Material]:
    index = material_index(project, material)
    return index, project.materials[index]
