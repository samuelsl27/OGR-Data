"""The registry of named operations (spec 019).

An operation is a plain function ``op(ws, **kwargs) -> dict`` with a stable
name, a toolset and a flag saying whether it edits a project. The MCP
server publishes one tool per operation, written by hand; a test keeps the
two from drifting (the OGR-Slip2D pattern).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..errors import unknown


@dataclass(frozen=True)
class Operation:
    name: str
    func: Callable
    toolset: str
    mutates: bool

    @property
    def summary(self) -> str:
        doc = (self.func.__doc__ or "").strip()
        return doc.splitlines()[0] if doc else ""


REGISTRY: dict[str, Operation] = {}


def operation(name: str, *, toolset: str, mutates: bool = False):
    """Register ``func`` under ``name``."""

    def deco(func):
        if name in REGISTRY:
            raise ValueError(f"operation {name!r} registered twice")
        REGISTRY[name] = Operation(name, func, toolset, mutates)
        return func

    return deco


def call(ws, op_name: str, /, **kwargs):
    """Run the operation ``op_name`` on workspace ``ws`` (both positional-only)."""

    op = REGISTRY.get(op_name)
    if op is None:
        raise unknown("operation", op_name, sorted(REGISTRY))
    return op.func(ws, **kwargs)


# registration happens on import
from . import catalog, project, materials, data, simulation, estimation, database, output  # noqa: E402,F401
