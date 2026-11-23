# Plan y tareas 025a — Errores visibles

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| Etiqueta del registro (`tr(CRITERIA[key].label)`) con la clave en `itemData` | Un diccionario propio en el diálogo: una segunda lista de nombres que se desincroniza | RF-1 |
| Paleta oscura de la aplicación además de la hoja (la de OGR-Slip2D v0.1.316, D301) | Una regla QSS para `QScrollArea`: arregla este panel y deja el siguiente igual; la hoja solo pinta lo que nombra | RF-2 |
| Etiquetas largas con `setWordWrap`, carta con ancho mínimo y divisor no colapsable | Fijar el ancho del diálogo: el texto de fuente cambia con el idioma | RF-3 |
| `calibration.has_points(state)` en el núcleo; la ventana lo pregunta | Comprobar los puntos en el diálogo: la regla de qué punto cuenta (excluidos, tipo de ensayo) ya vive en el núcleo (regla «una regla, un sitio») | RF-4, RF-5 |
| El botón cierra la calibración y la ventana abre *Define Failure States* | Abrir un diálogo modal desde otro: dos modales apilados y la lista de estados de la calibración sin refrescar | RF-4 |

## Tareas

- [x] **T1** Tests de los cuatro bugs (`tests/test_ux_025a.py`), en rojo — RF-1…5
  - Hecho cuando: los cuatro fallan sin el arreglo (B2 comprobado con `git stash`).
- [x] **T2** Ajuste: nombres de criterio — RF-1 (`gui/fit_dialog.py`)
- [x] **T3** Tema oscuro: paleta — RF-2 (`gui/themes.py`)
- [x] **T4** Clasificador: etiquetas partidas y carta con ancho — RF-3 (`gui/soil_classifier.py`)
- [x] **T5** Calibración: `has_points`, aviso, botón y textos en español — RF-4, RF-5 (`core/calibration.py`, `gui/calibration_dialog.py`, `gui/main_window.py`, `gui/i18n/es_dialogs.py`)
- [x] **T6** Validación: suite entera en verde.

## Qué se encontró

- La suite entera termina a veces con código 127 (un `abort()` al cerrar
  el intérprete) después de `Passed: 224  Failed: 0`. Se bisecó cambio a
  cambio en un *worktree*: también lo hace `ba1298d` sin tocar, así que no
  es de esta spec. Queda como anomalía abierta en `AGENTS.md`.
- La anchura del diálogo del clasificador no se puede comprobar offscreen:
  la fuente de respaldo de Qt es más ancha que Segoe UI (1462 px frente a
  1198 px con las fuentes de Windows). El test comprueba la carta, no el
  diálogo.
