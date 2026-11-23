# Plan 016 — Opciones de gráfica y exportación

Modelo: Graph Editor de RSData (captura `35_*`: lista de gráficas,
pestañas Title and Axis / Graph Display / Series Display, vista previa)
y menú contextual de gráfica (`34_*`). matplotlib cubre el render; esta
spec es la capa de UI y persistencia.

- `core/graph_options.py` (sin Qt): `SeriesStyle` (visible, color,
  grosor, estilo; valores vacíos/0 = defecto del tema), `PlotOptions`
  (título, rejilla, eje cuadrado, etiquetas dentro/fuera, rangos manuales
  o None=auto, estilos por serie) con `to_dict/from_dict` serializable
  para el `.ogrdata`.
- `core/export.py` (sin Qt): `write_series_csv(path, columns, unit)` —
  columnas "etiqueta (unidad)" por serie, filas recortadas/rellenadas
  con vacíos (formato listo para Excel, equivalente honesto del
  "Export to Excel" de RocData/RSData).
- `gui/plots.py`: cada canvas lleva `PlotOptions`; `apply_options()`
  aplica título/rejilla/aspecto/límites/estilos; el color por defecto
  sigue al tema salvo override del usuario; `zoom_extents()` vuelve a
  límites automáticos; `series_data()` expone las series para el CSV;
  `save_image(path)` (matplotlib savefig, PNG por defecto en el diálogo);
  `contextMenuEvent` con Copy / Save Image / Export CSV / Zoom Extents /
  Graph Editor, despachado por callback al MainWindow.
- `gui/graph_editor.py`: diálogo con selector de gráfica (principal /
  cortante) y controles por pestaña; los cambios se aplican al vuelo al
  canvas real; Cancel restaura el estado de apertura (snapshot).
- Persistencia: `.ogrdata` guarda `graph_options` (dict por canvas);
  `core/project.py` lo admite como clave opcional aditiva.
- Tests: `tests/test_graph_options.py` — round-trip de opciones, CSV,
  aplicación en canvas offscreen (propiedades de la figura: título,
  rejilla, límites, estilos de series), zoom extents, guardar imagen,
  editor (aplicar/cancelar) y persistencia en proyecto.
