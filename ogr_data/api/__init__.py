"""OGR Data — the operations layer (spec 019).

Everything an agent or a script can do with OGR Data, as named operations
with JSON-safe answers, without Qt and without the MCP SDK:

    from ogr_data.api import Workspace, call

    ws = Workspace()
    pid = call(ws, "project_new", title="Demo")["project_id"]
    call(ws, "material_set", project_id=pid, criterion="generalized_hoek_brown",
         parameters={"sigci": 50000, "gsi": 45, "mi": 10, "d": 0})
    out = call(ws, "material_compute", project_id=pid)

Same pattern as OGR-Slip2D's ``ogr_api`` (spec 008 there): handles
(``project_id``), validation with suggestions, coded errors. The
operations call the SAME core functions as the window (``core.*``, with
the derived values in ``core.material_results`` and the created materials
in ``core.material_factory``), so a value never differs between the two.

It never imports PySide6, ``ogr_data.gui`` or ``mcp``;
``tests/test_api.py`` fails if it does.

Units, in and out: stresses kPa, unit weight kN/m3, lengths m, angles deg.
"""

from .errors import Conflict, InvalidArgument, NotFound, OgrApiError
from .ops import REGISTRY as OPERATIONS
from .ops import call
from .workspace import Workspace

__all__ = ["Workspace", "call", "OPERATIONS", "OgrApiError", "NotFound", "InvalidArgument", "Conflict"]
