"""OGR Data — MCP server (spec 019).

A thin layer: every tool is one operation of ``ogr_data.api``, published
with the official MCP SDK (``mcp``, MIT) over stdio:

    pip install "ogr-data[mcp]"
    ogr-data-mcp --workdir C:\\path\\to\\projects

Importable WITHOUT the SDK (nothing here imports ``mcp`` at module level),
so the command line can say "install the [mcp] extra" instead of crashing.
"""
