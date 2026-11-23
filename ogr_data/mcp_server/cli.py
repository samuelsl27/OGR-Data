"""``ogr-data-mcp``: the MCP server over stdio.

Nothing is printed on standard output: over stdio that stream IS the
protocol. Messages and logs go to standard error (or --log-file).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="ogr-data-mcp", description="MCP server for OGR Data (rock and soil strength properties), stdio.")
    p.add_argument("--workdir", help="Folder for relative paths (projects, reports, pictures). Default: the current folder.")
    p.add_argument("--database", help="User materials database (JSON). Default: the window's own file.")
    p.add_argument("--log-file", help="Write the log here instead of standard error.")
    p.add_argument("--version", action="store_true", help="Print the version (to standard error) and exit.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(sys.argv[1:] if argv is None else argv)
    from .. import __version__

    if args.version:
        print(f"ogr-data-mcp {__version__}", file=sys.stderr)
        return 0
    target = {"filename": args.log_file} if args.log_file else {"stream": sys.stderr}
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", **target)
    try:
        import mcp  # noqa: F401
    except ImportError:
        print('The MCP SDK is not installed. Install the extra:\n    pip install "ogr-data[mcp]"', file=sys.stderr)
        return 3
    if args.workdir and not Path(args.workdir).is_dir():
        print(f"--workdir {args.workdir} is not a folder.", file=sys.stderr)
        return 2
    from ..api import Workspace
    from .server import build_server

    ws = Workspace(workdir=args.workdir, database_path=args.database)
    build_server(ws).run("stdio")
    return 0
