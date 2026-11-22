# Plan 005 — Portapapeles

## Núcleo (`core/clipboard.py`, sin Qt)

- `FORMAT = "ogr-material/1"`, `PREFIX = "OGR-DATA-MATERIAL:"`.
- `material_text(name, criterion_key, params, computed=None) -> str`.
- `parse_material(text) -> MaterialPayload | None` (None si no lleva el
  prefijo; ValueError si el prefijo está pero JSON/version no cuadran).
- `tabular_data(criterion_key, params, computed) -> str` (líneas
  `clave\tvalor`).

## GUI

Barra de botones en la ventana principal: **Copy material** (contrato),
**Copy data** (tabulado), **Copy plot image** (canvas actual → clipboard).

El payload `computed` solo se rellena para GHB (los valores derivados que
ya calcula la ventana); para el resto va vacío — los consumidores usan
`parameters`.
