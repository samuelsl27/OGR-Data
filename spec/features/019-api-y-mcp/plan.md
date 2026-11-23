# Plan 019 — Capa de operaciones y servidor MCP

Patrón de OGR-Slip2D (`ogr_api` + `ogr_mcp`, spec 008 de Slip2D), en
pequeño: sin trabajos en segundo plano, sin deshacer, sin puente a la
ventana y sin HTTP (nada de eso hace falta en v1: todos los cálculos de
OGR-Data duran milisegundos).

## Núcleo compartido (antes de la API)

- `core/material_results.py`: `ghb_input`, `modulus_method`, `hb_terms`,
  `rock_mass_strength_mpa`, `application_sig3max`, `ghb_computed`,
  `overlay_mc`, `computed`, `fit_to_parameters`. La ventana delega en
  ellas (`_ghb_computed`, `_application_sig3max`, `_overlay_mc_params`,
  `apply_fit_parameters`...) y el informe usa `modulus_method`.
- `core/material_factory.py`: `from_uscs`, `from_record`,
  `state_from_record`, `from_calibration`, `from_roc`.
- Al mover `apply_fit_parameters` apareció un fallo: escribía kPa en
  campos que muestran la unidad de visualización (con MPa, una cohesión
  de 1 MPa salía como 1000 MPa). Corregido; test en `test_api.py`.

## `ogr_data/api`

- `errors.py`: `OgrApiError` con código estable (`E_NOT_FOUND`,
  `E_INVALID_ARGUMENT`, `E_CONFLICT`, `E_INTERNAL`) y sugerencias
  (`did_you_mean`).
- `workspace.py`: `Workspace` (handles `p1, p2...`, carpeta de trabajo,
  base de datos del usuario en la misma ruta que usa la ventana, sin Qt);
  un material se nombra por nombre o índice 0-based.
- `ops/`: registro (`operation`, `call`, `REGISTRY`) y 36 operaciones en
  `catalog`, `project`, `materials`, `data`, `simulation`, `estimation`,
  `database`, `output`. `_common.py` es el único sitio que convierte
  unidades (σ3max y calculados MPa → kPa, peso específico MN/m3 → kN/m3).
- `render.py`: PNG de la envolvente con matplotlib Agg (sin Qt).
- Nunca importa PySide6, `ogr_data.gui` ni `mcp` (test).

## `ogr_data/mcp_server`

- `server.py`: `build_server(ws)` con una herramienta escrita a mano por
  operación (descripción y tipos para el modelo), `server_info` y el
  recurso `ogr-data://guide`; errores con código vía `ToolError`.
- `guide.py`: `INSTRUCTIONS` (corto, viaja con cada conexión) y `GUIDE`.
- `cli.py` / `__main__.py`: `ogr-data-mcp --workdir ... --database ...`
  por stdio; sin el SDK, mensaje y código 3.
- `pyproject.toml`: extra `[mcp]` (`mcp>=2.1,<3`) y script `ogr-data-mcp`.

## Tests

- `tests/test_api.py`: capas, caso ORMAS (c, φ, Erm, σ3max túnel/talud),
  mismos valores que la ventana, ficheros, validación, portapapeles,
  ajuste y calibración, rutas y simulación, estimación, base de datos,
  PNG e informe, catálogo, aplicar un ajuste en la unidad de visualización.
- `tests/test_mcp_server.py`: herramientas = operaciones, parámetros que
  llegan, descripciones, errores con código, caso ORMAS por el protocolo,
  línea de órdenes.
