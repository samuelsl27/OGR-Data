# Spec 011 — Proyectos multi-material

## Qué se construye

El modelo de proyecto real del programa de referencia (hoy OGR-Data guarda un material
por archivo, spec 007): un proyecto `.ogrdata` con **varios materiales**,
árbol de visibilidad (Add Material con plantillas roca/suelo, Duplicate,
borrar, renombrar, color/símbolo), selección que alimenta la barra
lateral y las gráficas, y persistencia de todo el conjunto.

## Motivación

Es la base sobre la que luego montan failure states, stress paths y
test simulations por material (specs 012-013). Sin él, cada spec
posterior tendría que improvisar el contenedor.

## Criterios de aceptación

- Proyecto con N materiales de criterios distintos; round-trip
  `.ogrdata` (formato v2 migrando v1: un material suelto = proyecto de
  un elemento).
- Árbol: añadir (rock/soil template), duplicar, borrar, renombrar.
- Cambiar de material en el árbol actualiza formulario y gráficas.
- Contrato de portapapeles (spec 005) copia el material seleccionado.

## Fuera de alcance

- Colecciones/estados por material (spec 012).
- Undo/redo (especificar aparte si se pide).
