# Plan 003 — Pick dialogs

## Datos

JSON versionados en `ogr_data/data/` (convención de la constitution), con
campo `source` en cada tabla. Extracción verificada contra los PDF de
`Referencias/Bibliografia/Rocas/` el 2026-11-22 (Tabla 3 leída de la página
renderizada porque la extracción de texto la corrupta: Gneiss 28±5, Breccias
19±5, Rhyolite 25±5).

## Código

- `ogr_data/core/tables.py`: carga de los JSON + funciones de consulta
  (sin Qt): `rock_strength_grades()`, `mi_values()`, `gsi_chart()`, y
  `gsi_estimate(structure, surface) -> (lo, hi)`.
- Campo `pick` nuevo en `Field` (models.py): clave del picker
  ("sigci_grades" | "mi_values" | "gsi_chart").
- `ogr_data/gui/pickers.py`: `TablePickerDialog` (búsqueda + tabla) y
  `GsiPickerDialog` (dos desplegables con descripciones + rango resultante).
- `main_window`: botón "Pick…" por campo habilitado; al aceptar, escribe el
  valor en el spinbox (GSI: punto medio del rango, ajustable).

## Riesgos

- Lectura de celdas GSI aproximada → se etiqueta como tal en el diálogo y
  en el JSON ("contour reading, indicative").

## Revisión 2026-11-23 (análisis del programa de referencia y ORMAS)

- Valores que escribe el pick de σci: los del programa de referencia y ORMAS (250, 175,
  75, 35, 15, 3, 0,6 MPa); antes R3 = 37,5 y R0 = 0,625 (puntos medios).
  Hecho, con test.
- mi: la tabla (Hoek, Tabla 3) coincide con el programa de referencia en las nueve rocas en
  que ORMAS difiere: la fuente es correcta; ORMAS tiene erratas.
- La ampliación (clic sobre la carta GSI, calculadora, filtros de mi, D,
  Ei/MR, un solo clic) pasa a la **spec 022**.
