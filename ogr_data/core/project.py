"""OGR Data project files (.ogrdata): specs 007 and 011.

Format v2 (spec 011) holds a list of materials, as the RSData project
model: each material carries its criterion, parameters (registry units,
kPa and degrees), envelope range, application settings (spec 009) and its
display properties (color, symbol, visibility). Project-level keys are the
title, the display stress unit (spec 017) and the graph options (spec 016).

Format v1 (spec 007) stored one loose material at the top level; it loads
as a project of one material.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Union

from .models import CRITERIA, defaults
from .states import FailureState, StressPath

FORMAT_V1 = "ogr-data-project/1"
FORMAT = "ogr-data-project/2"

Params = Mapping[str, Union[float, bool, str]]

# Criterion of the first material of a new project (first registry entry,
# the one the window shows at start).
DEFAULT_CRITERION = next(iter(CRITERIA))

# Add Rock Template / Add Soil Template (RSData's Add Material drop-down).
# RSData documents the templates only as "Material Model + Failure State
# Set" (rock) and "Material Model + Test, Stress Path" (soil); the criterion
# each one starts with is an OGR Data choice: the rock-mass criterion of
# reference (Generalized Hoek-Brown) and the soil one (Mohr-Coulomb), with
# the registry defaults captured from RSData. Spec 012: the rock template
# also brings an (empty) failure state and the soil one a stress path.
TEMPLATES: dict[str, tuple[str, str]] = {
    "material": ("Material", DEFAULT_CRITERION),
    "rock": ("Rock", "generalized_hoek_brown"),
    "soil": ("Soil", "mohr_coulomb"),
}

APPLICATION_MODES = ("custom", "tunnel", "slope")
# GUI defaults of spec 009 (the ORMAS validation case: 0.026 MN/m3, 50 m).
DEFAULT_UNIT_WEIGHT = 0.026
DEFAULT_DEPTH = 50.0
DEFAULT_SIG3MAX_MPA = 7.5

# Display palette for added materials ("" = theme envelope color, kept by
# the first material so a one-material project looks as before spec 011).
PALETTE = ("#e67e22", "#8e44ad", "#16a085", "#b7950b", "#c2185b", "#5d6d7e")

# Point symbols (matplotlib markers) for the material's test data (spec 012).
SYMBOLS: dict[str, str] = {
    "o": "Circle",
    "s": "Square",
    "^": "Triangle",
    "D": "Diamond",
    "v": "Inverted triangle",
}


@dataclass
class Application:
    """sigma3max by application (spec 009): custom, tunnel or slope."""

    mode: str = "custom"
    unit_weight: float = DEFAULT_UNIT_WEIGHT  # MN/m3
    depth: float = DEFAULT_DEPTH  # m (tunnel depth or slope height)

    def to_dict(self) -> dict:
        return {"mode": self.mode, "unit_weight": self.unit_weight, "depth": self.depth}

    @classmethod
    def from_dict(cls, data: Mapping | None) -> "Application":
        data = data or {}
        mode = str(data.get("mode", "custom"))
        return cls(
            mode=mode if mode in APPLICATION_MODES else "custom",
            unit_weight=float(data.get("unit_weight", DEFAULT_UNIT_WEIGHT)),
            depth=float(data.get("depth", DEFAULT_DEPTH)),
        )


@dataclass
class Material:
    name: str
    criterion: str
    parameters: dict[str, Union[float, bool, str]]
    sig3max_mpa: float = DEFAULT_SIG3MAX_MPA
    application: Application = field(default_factory=Application)
    color: str = ""  # "" = theme envelope color
    symbol: str = "o"
    visible: bool = True
    failure_states: list[FailureState] = field(default_factory=list)  # spec 012
    stress_paths: list[StressPath] = field(default_factory=list)  # spec 012

    def __post_init__(self) -> None:
        if self.criterion not in CRITERIA:
            raise ValueError(f"unknown criterion {self.criterion!r}")
        # missing keys (older files, registry growth) take the defaults
        self.parameters = {**defaults(self.criterion), **dict(self.parameters)}
        if self.symbol not in SYMBOLS:
            self.symbol = "o"

    @classmethod
    def from_template(cls, template: str, name: str | None = None, color: str = "") -> "Material":
        if template not in TEMPLATES:
            raise ValueError(f"unknown material template {template!r}")
        label, criterion = TEMPLATES[template]
        material = cls(name=name or label, criterion=criterion, parameters=defaults(criterion), color=color)
        if template == "rock":
            material.failure_states.append(FailureState())
        elif template == "soil":
            material.stress_paths.append(StressPath())
        return material

    def copy(self) -> "Material":
        return Material.from_dict(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "criterion": self.criterion,
            "parameters": dict(self.parameters),
            "sig3max_mpa": float(self.sig3max_mpa),
            "application": self.application.to_dict(),
            "color": self.color,
            "symbol": self.symbol,
            "visible": self.visible,
            "failure_states": [s.to_dict() for s in self.failure_states],
            "stress_paths": [p.to_dict() for p in self.stress_paths],
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "Material":
        criterion = data.get("criterion")
        if criterion not in CRITERIA:
            raise ValueError(f"unknown criterion {criterion!r}")
        return cls(
            name=str(data.get("name", "")) or "Material",
            criterion=criterion,
            parameters=dict(data.get("parameters", {})),
            sig3max_mpa=float(data.get("sig3max_mpa", DEFAULT_SIG3MAX_MPA)),
            application=Application.from_dict(data.get("application")),
            color=str(data.get("color", "")),
            symbol=str(data.get("symbol", "o")),
            visible=bool(data.get("visible", True)),
            failure_states=[FailureState.from_dict(s) for s in data.get("failure_states", [])],
            stress_paths=[StressPath.from_dict(p) for p in data.get("stress_paths", [])],
        )


@dataclass
class Project:
    materials: list[Material] = field(default_factory=list)
    selected: int = 0
    title: str = ""
    stress_unit: str = "kPa"
    graph_options: dict = field(default_factory=dict)

    @classmethod
    def new(cls) -> "Project":
        return cls(materials=[Material.from_template("material")])

    # ------------------------------------------------------------ names

    def unique_name(self, base: str, exclude: int | None = None) -> str:
        """base, or base 2, base 3... not used by another material."""

        taken = {m.name for i, m in enumerate(self.materials) if i != exclude}
        if base not in taken:
            return base
        n = 2
        while f"{base} {n}" in taken:
            n += 1
        return f"{base} {n}"

    def next_color(self) -> str:
        used = {m.color for m in self.materials}
        for color in PALETTE:
            if color not in used:
                return color
        return PALETTE[len(self.materials) % len(PALETTE)]

    # ------------------------------------------------------- operations

    def add(self, template: str = "material") -> int:
        """Append a material from a template; returns its index."""

        label = TEMPLATES[template][0] if template in TEMPLATES else template
        material = Material.from_template(template, self.unique_name(label), self.next_color())
        self.materials.append(material)
        return len(self.materials) - 1

    def append(self, material: Material) -> int:
        """Append an existing material (e.g. an import), renaming on clash."""

        material.name = self.unique_name(material.name)
        if not material.color and self.materials:
            material.color = self.next_color()
        self.materials.append(material)
        return len(self.materials) - 1

    def duplicate(self, index: int) -> int:
        source = self.materials[index]
        material = source.copy()
        material.name = self.unique_name(f"{source.name} - Copy")
        material.color = self.next_color()
        self.materials.insert(index + 1, material)
        return index + 1

    def remove(self, index: int) -> int:
        """Delete a material; returns the index to select next.

        A project always keeps one material (the form edits a material).
        """

        if len(self.materials) <= 1:
            raise ValueError("a project keeps at least one material")
        del self.materials[index]
        return min(index, len(self.materials) - 1)

    def rename(self, index: int, name: str) -> str:
        """Rename a material; empty names are rejected, clashes numbered."""

        name = name.strip()
        if not name:
            raise ValueError("material name cannot be empty")
        name = self.unique_name(name, exclude=index)
        self.materials[index].name = name
        return name

    # -------------------------------------------------------------- file

    def to_dict(self) -> dict:
        if not self.materials:
            raise ValueError("a project keeps at least one material")
        return {
            "format": FORMAT,
            "title": self.title,
            "stress_unit": self.stress_unit,
            "graph_options": dict(self.graph_options),
            "selected": max(0, min(self.selected, len(self.materials) - 1)),
            "materials": [m.to_dict() for m in self.materials],
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "Project":
        fmt = data.get("format")
        if fmt == FORMAT_V1:
            return cls._from_v1(data)
        if fmt != FORMAT:
            raise ValueError(f"unsupported project format {fmt!r}")
        materials = [Material.from_dict(m) for m in data.get("materials", [])]
        if not materials:
            raise ValueError("project has no materials")
        selected = int(data.get("selected", 0))
        return cls(
            materials=materials,
            selected=max(0, min(selected, len(materials) - 1)),
            title=str(data.get("title", "")),
            stress_unit=str(data.get("stress_unit", "kPa")),
            graph_options=dict(data.get("graph_options", {})),
        )

    @classmethod
    def _from_v1(cls, data: Mapping) -> "Project":
        """Spec 007 file: one loose material -> project of one material."""

        material = Material.from_dict(
            {
                "name": data.get("name", ""),
                "criterion": data.get("criterion"),
                "parameters": data.get("parameters", {}),
                "sig3max_mpa": data.get("sig3max_mpa", DEFAULT_SIG3MAX_MPA),
            }
        )
        return cls(
            materials=[material],
            title=str(data.get("title", "")),
            stress_unit=str(data.get("stress_unit", "kPa")),
            graph_options=dict(data.get("graph_options", {})),
        )


def save_project(path: str | Path, project: Project) -> None:
    Path(path).write_text(json.dumps(project.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def load_project(path: str | Path) -> Project:
    return Project.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
