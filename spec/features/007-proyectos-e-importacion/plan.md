# Plan 007 — Proyectos e importación

- `core/project.py`: `save_project/load_project`, JSON con
  `format: "ogr-data-project/1"`, validación de criterio.
- `core/roc_import.py`: parser de líneas `clave: valor` por secciones;
  mapa de criterios; factores de unidad MPa→kPa; parseo de los bloques
  `lab data` / `rock mass data` (índice, x, y).
- GUI: botones Save / Load / Import .roc en la barra lateral; el import
  actúa como `apply_fit_parameters`: selecciona criterio, reconstruye el
  formulario y rellena.
- Tests sobre los 11 ejemplos reales del manual de RocData.
