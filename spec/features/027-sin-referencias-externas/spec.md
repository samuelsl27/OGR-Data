# Spec 027 — Retirar las referencias al fabricante del programa de referencia

> Estado: **hecha** (2026-11-24; validación en `plan-tasks.md`).

## Contexto y objetivo

Regla 9 de `AGENTS.md` (propietaria, 2026-11-24): ni Rocscience ni sus
productos se nombran ni se citan en el repositorio. La regla llega después
de 24 specs que los nombraban al describir qué se reproducía. Lo que se
escribió en la sesión de la regla ya la cumple (ayuda de parámetros,
*status tips*, módulos y tests nuevos de la serie 025); el resto queda por
limpiar.

## Inventario (2026-11-24)

| Zona | Alcance |
|---|---|
| Código y comentarios (`ogr_data/core`, `gui`, `api`, `mcp_server`) | 166 líneas en 33 archivos (las que más: `core/simulation.py`, `core/states.py`, `core/roc_import.py`, `gui/main_window.py`, `core/database.py`, `core/models.py`, `core/calibration.py`) |
| Textos de la interfaz | 6 claves con su español (notas de los diálogos de ensayos; «Import RocData file») |
| API y servidor MCP | descripciones de operaciones y la guía para agentes |
| Datos que se distribuyen | 4 menciones en `ogr_data/data` (fuentes de tablas alojadas por el fabricante) |
| Tests | 55 líneas en 14 archivos (nombres, comentarios, rutas a capturas) |
| Documentación del repositorio | `README.md`, `spec/constitution/*.md` y 59 documentos de `spec/` |

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA no nombrará al fabricante ni a sus productos en el
  código, los comentarios, los textos de la interfaz, la ayuda, los datos
  distribuidos, la API, el servidor MCP ni los tests.
- **RF-2**: EL SISTEMA tendrá un test que recorra el repositorio y falle
  ante cualquiera de esos nombres fuera de la propia regla 9 de `AGENTS.md`.
- **RF-3**: DONDE haga falta decir que un comportamiento reproduce el del
  programa de referencia, EL SISTEMA dirá «el programa de referencia».
- **RF-4**: EL SISTEMA citará las fórmulas por su fuente científica; donde
  hoy la única cita es un manual del fabricante, el comentario dirá que
  falta fuente citable y la ayuda lo listará como pendiente.
- **RF-5**: CUANDO se importe un archivo `.roc`, EL SISTEMA lo llamará por
  su extensión, sin el nombre del programa que lo crea
  [NECESITA ACLARACIÓN: ¿se mantiene la importación de `.roc`?].

## Requisitos no funcionales

- Ningún cálculo cambia: la spec es de textos, nombres y comentarios.
- La documentación privada de `../Referencias/` queda fuera.

## Fuera de alcance

- La historia de git (sus commits nombran al fabricante; reescribirla
  obligaría a forzar el push).

## Dudas abiertas

Resueltas al aprobarla (2026-11-24), con el alcance que ya fija la regla 9
de `AGENTS.md`:

- La regla alcanza **también a los documentos de `spec/`** («la
  documentación del repositorio»).
- La importación de `.roc` **se mantiene**, nombrada por su extensión. La
  etiqueta con que empieza un `.roc` se sigue comparando en el importador:
  es un dato del formato y la línea va marcada `rule 9: file-format tag`.
- La **historia de git no se reescribe** (obligaría a forzar el push).
- Las rutas a la carpeta privada `../Referencias/` se escriben sin nombres
  de carpeta que lleven el nombre de un producto; los tests localizan los
  ejemplos `.roc` buscándolos, no por su ruta.
