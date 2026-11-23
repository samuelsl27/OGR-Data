# Plan 023 — Deshacer y rehacer

## Decisión principal: instantáneas comparadas, no comandos

Slip2D envuelve cada escritura en un comando (`SnapshotCommand`). Aquí el
formulario es el estado vivo del material seleccionado y `refresh()` lo
vuelca al proyecto en cada cambio (`_store_current`), así que hay un
punto por el que pasan TODAS las ediciones. En vez de tocar los ~40
manejadores, la ventana compara el proyecto con el último estado
registrado al final de `refresh()` (y en los pocos sitios que editan sin
redibujar: título, editor de gráficas, símbolo) y, si difiere, registra
un paso. El texto del paso se deduce comparando los dos estados
(`describe`): «Change GSI», «Add Material 'Rock'», «Edit Failure
States»... Ventajas: cubre ya las acciones futuras, no puede olvidarse un
manejador, y el núcleo no conoce Qt. Descartado: un `QUndoStack` con un
comando por acción (más código, y cada acción nueva tendría que acordarse).

## Núcleo: `core/history.py` (sin Qt)

- `snapshot(project) -> dict`: `copy.deepcopy(project.to_dict())` (el
  `to_dict` comparte las listas de las tablas con el material).
- `comparable(state)`: sin `selected`, `stress_unit` ni `format` (no son
  ediciones: selección y preferencia), con los reales redondeados a 10
  cifras significativas (el formulario devuelve los valores pasados por
  la unidad de visualización).
- `describe(before, after) -> (texto, clave)`: la clave identifica la
  edición (`("param", i, "gsi")`) para agrupar las seguidas.
- `History(estado, limit=100)`: `record` (paso nuevo, o fusión con el
  último si la clave coincide y el grupo sigue abierto), `rebase`
  (absorber sin paso), `close_group`, `undo`/`redo` (devuelven el estado a
  restaurar), `undo_text`/`redo_text`, `mark_saved`/`modified`.
- Ida y vuelta `Project.from_dict(snapshot)` = identidad: test.

## Ventana

- `self._history`; `_checkpoint()` al final de `refresh()` y al empezar
  `_load_material` (registra la acción que cambia de material: añadir,
  duplicar, borrar, importar...); después de cargar un material se
  absorbe el estado (sin paso) para no registrar el redondeo del
  formulario. También tras el título (al terminar de editarlo), el editor
  de gráficas y el símbolo.
- Cerrar grupo: `editingFinished` de los campos numéricos del formulario,
  de σ3max, de la aplicación y de la rigidez, y de nombre y título.
- `_restore(state)`: `Project.from_dict`, conserva la unidad de
  visualización, título, opciones de gráfica, material seleccionado del
  estado, árbol y gráficas; sin registrar pasos; luego `rebase`.
- Edit > Undo / Redo (`QKeySequence.Undo`; Redo con Ctrl+Y y
  Ctrl+Shift+Z), texto con la acción y habilitados según el historial.
- Cambiar de unidad de visualización: `rebase` (no es una edición).
- Cambios sin guardar: `setWindowModified` + `[*]` en el título; `New
  Project`, `Load…`, `Exit` / cerrar preguntan Guardar / Descartar /
  Cancelar (`_confirm_discard`, con un gancho `ask_unsaved` para los
  tests); `_save_project` devuelve si guardó y marca el punto guardado.
  Nuevo y cargar empiezan un historial nuevo.

## API (spec 019)

- `call()` registra cada operación que edita (`mutates`) en el historial
  del proyecto (mismo `History`), con el nombre de la operación.
- Operación `project_history(action = list | undo | redo, steps)` y su
  herramienta MCP.

## Tests

- `tests/test_history.py`: núcleo (identidad del ida y vuelta, describe,
  fusión, rama de rehacer, límite, modificado) y ventana offscreen (un
  test por tipo de paso: campo, criterio, σ3max/aplicación, añadir /
  duplicar / renombrar / borrar, color / visibilidad, estados de fallo,
  ajuste, selector, título; menú y atajos; asterisco y preguntas;
  rendimiento de la instantánea).
- `tests/test_api.py`: `project_history`.
