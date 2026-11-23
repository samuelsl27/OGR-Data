# Tasks 019 — Capa de operaciones y servidor MCP

- [x] Alcance revisado (specs 012–022) y plan
- [x] Núcleo compartido: `core/material_results.py`, `core/material_factory.py`; ventana e informe delegan en él
- [x] Corrección: aplicar un ajuste respeta la unidad de visualización
- [x] `ogr_data/api`: errores, workspace, registro y 36 operaciones; PNG sin Qt
- [x] `ogr_data/mcp_server`: herramientas a mano, guía, `ogr-data-mcp` (stdio); extra `[mcp]`
- [x] Tests: `test_api.py`, `test_mcp_server.py`; suite en verde
- [x] Comprobado por stdio real con el cliente del SDK
- [ ] (fuera de v1) `--attach` a una ventana abierta, deshacer, transporte HTTP
- [ ] (suite) registrar OGR-Data en `suite.toml` con su `mcp` para `configurar_mcp.py`
