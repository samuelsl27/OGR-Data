"""``python -m ogr_data.mcp_server`` (everything under the guard: Windows re-imports the main module in child processes)."""

if __name__ == "__main__":
    import sys

    from ogr_data.mcp_server.cli import main

    sys.exit(main())
