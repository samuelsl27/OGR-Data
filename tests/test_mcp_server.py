"""Spec 019: the MCP tools are the operations, faithfully (as OGR-Slip2D's test_mcp_server).

Driven through the SDK's in-memory client, so the real protocol layer
(schemas, validation, content) is crossed without a process. Protected:
every operation has a tool and back; every tool parameter reaches its
operation with the value given; every tool and parameter is described;
errors keep their code; the ORMAS case gives the same numbers through the
protocol; the command line starts.

Without the ``mcp`` SDK the tests return early, except in CI.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise AssertionError("the mcp SDK must be installed in CI (pip install -e .[mcp])")
        return False
    return True


def _server():
    import logging

    from ogr_data.api import Workspace
    from ogr_data.mcp_server.server import build_server

    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    ws = Workspace(database_path=Path(tempfile.gettempdir()) / "ogr_data_test_no_db.json")
    srv = build_server(ws)
    root.handlers[:], root.level = handlers, level  # building a server may configure logging
    return ws, srv


async def _tools(srv):
    from mcp import Client

    async with Client(srv) as c:
        return (await c.list_tools()).tools


def _value(name, schema):
    """A NON-default value of the declared type."""

    default = schema.get("default")
    options = [s for s in schema.get("anyOf", [schema]) if s.get("type") != "null"] or [schema]
    s = options[0]
    if "enum" in s:
        return next((o for o in s["enum"] if o != default), s["enum"][0])
    kind = s.get("type")
    if kind == "boolean":
        return not (default or False)
    if kind == "integer":
        return 7
    if kind == "number":
        return 2.5
    if kind == "array":
        return [_value(name, s.get("items", {})), _value(name, s.get("items", {}))]
    if kind == "object":
        return {"k": 1}
    return f"v_{name}"


def test_every_operation_has_a_tool_and_back() -> None:
    if not _have_mcp():
        return
    from ogr_data.api import OPERATIONS

    _, srv = _server()
    names = {t.name for t in asyncio.run(_tools(srv))}
    assert names - {"server_info"} == set(OPERATIONS), sorted(names ^ (set(OPERATIONS) | {"server_info"}))


def test_tool_parameters_are_operation_parameters() -> None:
    if not _have_mcp():
        return
    from ogr_data.api import OPERATIONS

    _, srv = _server()
    for t in asyncio.run(_tools(srv)):
        if t.name == "server_info":
            continue
        op = set(inspect.signature(OPERATIONS[t.name].func).parameters) - {"ws"}
        tool = set(t.input_schema.get("properties", {}))
        assert tool == op, (t.name, sorted(tool ^ op))


def test_every_parameter_reaches_its_operation() -> None:
    if not _have_mcp():
        return
    import ogr_data.mcp_server.server as S
    from mcp import Client

    _, srv = _server()
    seen = {}

    def spy(_ws, op, /, **kwargs):
        seen[op] = kwargs
        if op == "render_envelope":
            return {"png": b"\x89PNG\r\n\x1a\n", "saved_to": None}
        return {"ok": True}

    saved = S.call
    S.call = spy
    try:
        async def scenario():
            async with Client(srv) as c:
                for t in (await c.list_tools()).tools:
                    if t.name == "server_info":
                        continue
                    args = {n: _value(n, s) for n, s in t.input_schema.get("properties", {}).items()}
                    r = await c.call_tool(t.name, args)
                    assert not r.is_error, (t.name, r.content)
                    got = seen.pop(t.name)
                    for n, v in args.items():
                        assert got.get(n) == v, (t.name, n, v, got.get(n))

        asyncio.run(scenario())
    finally:
        S.call = saved


def test_tools_are_described_and_annotated() -> None:
    if not _have_mcp():
        return
    _, srv = _server()
    for t in asyncio.run(_tools(srv)):
        assert t.description and len(t.description) > 20, t.name
        assert t.annotations is not None, t.name
        for n, s in t.input_schema.get("properties", {}).items():
            assert s.get("description"), (t.name, n)


def test_errors_keep_their_code_and_the_ormas_case() -> None:
    if not _have_mcp():
        return
    from mcp import Client

    _, srv = _server()

    async def scenario():
        async with Client(srv) as c:
            info = json.loads((await c.call_tool("server_info", {})).content[0].text)
            assert info["server"] == "ogr-data" and "kPa" in info["units"] and len(info["tools"]) == len((await c.list_tools()).tools)
            r = await c.call_tool("material_get", {})
            assert r.is_error and "[E_NOT_FOUND]" in r.content[0].text and "project_new" in r.content[0].text
            await c.call_tool("project_new", {"title": "MCP"})
            r = await c.call_tool("material_set", {"criterion": "generalized_hoek_brown", "parameters": {"sigci": 30000, "gsi": 50, "mi": 10, "d": 0}, "sig3max_kpa": 7500})
            assert not r.is_error, r.content
            r = await c.call_tool("material_set", {"parameters": {"gsj": 40}})
            assert r.is_error and "Did you mean 'gsi'" in r.content[0].text
            out = json.loads((await c.call_tool("material_compute", {"points": 3})).content[0].text)
            assert abs(out["computed"]["c_kpa"] - 1494.1) < 0.5 and abs(out["computed"]["erm_kpa"] - 3686230.0) < 10.0
            r = await c.call_tool("render_envelope", {"plot": "principal"})
            assert [type(x).__name__ for x in r.content] == ["ImageContent", "TextContent"]
            guide = await c.read_resource("ogr-data://guide")
            assert "Units" in guide.contents[0].text

    asyncio.run(scenario())


def test_internal_errors_say_their_type() -> None:
    if not _have_mcp():
        return
    import ogr_data.mcp_server.server as S
    from mcp import Client

    _, srv = _server()

    def boom(_ws, op, /, **kwargs):
        raise ZeroDivisionError("division by zero")

    saved = S.call
    S.call = boom
    try:
        async def scenario():
            async with Client(srv) as c:
                r = await c.call_tool("project_list", {})
                assert r.is_error and "[E_INTERNAL] ZeroDivisionError" in r.content[0].text

        asyncio.run(scenario())
    finally:
        S.call = saved


def test_command_line() -> None:
    out = subprocess.run([sys.executable, "-m", "ogr_data.mcp_server", "--version"], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0 and out.stdout == "" and "ogr-data-mcp" in out.stderr
    bad = subprocess.run([sys.executable, "-m", "ogr_data.mcp_server", "--workdir", str(ROOT / "no_such_folder")],
                         capture_output=True, text=True, cwd=ROOT)
    assert bad.returncode in (2, 3) and bad.stdout == ""
