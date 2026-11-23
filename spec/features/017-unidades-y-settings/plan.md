# Plan 017 — Unidades y configuración del proyecto

- `core/units.py`: capa de conversión de unidades de visualización.
  Interno del núcleo: MPa; registro (`core/models.py`) y contrato de
  portapapeles (spec 005): kPa inalterados. Factores por magnitud:
  tensión `{"MPa": 1.0, "kPa": 1000.0}` (display = MPa × factor) y peso
  unitario `{"MN/m3": 1.0, "kN/m3": 1000.0}` (soporte de magnitud; el
  combo de UI solo expone tensión). `to_display`, `from_display`,
  `stress_text` para mensajes.
- `core/project.py`: `project_dict/save_project` aceptan `stress_unit` y
  `title` (opcionales, por defecto "kPa"/""); los `.ogrdata` antiguos
  sin esas claves cargan con los valores por defecto.
- GUI (`main_window.py`):
  - Combo "Stress unit" (kPa | MPa) persistido en QSettings; cambiarlo
    reescala **in situ** los spinbox kPa del formulario (sin reconstruir
    ni perder valores), el spin σ3max, las salidas, las etiquetas de
    ejes de ambas gráficas (`EnvelopeCanvas.set_axes_labels`) y los
    mensajes del muestreador. Los valores internos (params en kPa,
    σ3max en MPa) no cambian: round-trip kPa→MPa→kPa idempotente.
  - Helper `_sig3max_mpa()`; el spin σ3max muestra el valor en la
    unidad elegida.
  - Campo "Project title": va a la barra de título de la ventana y se
    guarda en el `.ogrdata` (los informes de la spec 015 lo usarán).
- Tests: `tests/test_units.py` — factores y round-trip del núcleo,
  round-trip de `.ogrdata` con unidad/título, y test offscreen de la
  GUI (cambio kPa↔MPa, sufijos, etiquetas de ejes, título, params
  internos inalterados).
- Fuera de alcance (spec): imperiales y t/m² (fase 2); el diálogo de
  ajuste a ensayos sigue en MPa (los datos de laboratorio se pegan en
  MPa, como en RocData); Convergence Settings (spec 013).
