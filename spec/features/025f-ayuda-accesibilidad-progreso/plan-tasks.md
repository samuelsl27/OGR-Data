# Plan y tareas 025f — Ayuda contextual, accesibilidad y progreso

Aprobada el 2026-11-24 con la condición de la propietaria: **todo
documentado y de fuentes fiables; lo que no se pueda conseguir, en un
listado** → [`fuentes-pendientes.md`](fuentes-pendientes.md).

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| La ayuda vive en datos (`ogr_data/data/parameter_help.json`) con su lista de fuentes, y el núcleo la lee (`core/parameter_help.py`); la interfaz solo la muestra | Textos en el código de la ventana: no se pueden revisar ni citar | RF-1 |
| Cada entrada: definición EN/ES con palabras propias, rango **solo** si una fuente lo da, fuentes y localizador (página, tabla, ecuación); lo que no tiene fuente va a `pending` con lo que falta | Rellenar con «valores habituales» sin fuente: lo prohíbe AGENTS.md | RF-1 |
| Investigación en cuatro grupos (MC/DP/rigidez, Hoek-Brown, Cam-Clay/Softening-Hardening, NorSand/Power Curve/Barton-Bandis) sobre la biblioteca de la suite y fuentes públicas descargadas a `../Referencias/Bibliografia` | — | RF-1 |
| Fuente original científica cuando se pudo leer; los manuales de Rocscience solo para conceptos propios del programa, citados como tales | Citar el manual para todo: no es la fuente del concepto | RF-1 |
| Tooltip = nombre, definición, unidad (la de pantalla), rango típico y fuentes cortas; en la etiqueta y en el campo, y en los campos del rango de tensiones | — | RF-1 |
| *Status tips* de una frase para las 46 acciones de los menús, por su texto inglés (`gui/status_tips.py`, `es_tips.py`) | — | RF-2 |
| Etiqueta → campo con `setBuddy` (el campo, no la fila con su «Elegir…»); nombre accesible a lo que no tiene texto | — | RF-3 |
| Orden de tabulación explícito de la barra lateral (`_apply_tab_order`), rehecho al cambiar de criterio | El orden de creación: saltaba (rango antes que materiales) | RF-4 |
| Test de contraste WCAG con los colores de las hojas; iconos de la barra de herramientas legibles en oscuro (los de un color se tiñen con el color de texto; los deshabilitados, con el gris del tema) | — | RF-5 |
| Medido (2026-11-24): una simulación tarda hasta ~0,5 s (NorSand), una calibración < 5 ms. Progreso y Cancelar en *Compute* con 2 o más simulaciones; el diálogo solo aparece si pasa de 1 s | Hilos: el cálculo es corto y el núcleo no está pensado para ello | RF-6 |
| Clasificador sin botón *Classify* (ya se actualizaba solo) | — | RF-7 |
| Tooltip de cada «Elegir…» con la tabla que abre y su fuente (las de `ogr_data/data`) | — | RF-8 |

## Tareas

- [x] **T1** Tests (`tests/test_ux_025f.py`) — todos
- [x] **T2** Investigación de fuentes (4 grupos) y fusión en `parameter_help.json` — RF-1
- [x] **T3** `core/parameter_help.py`, `gui/parameter_tooltip.py`, tooltips en formulario, rigidez y rango — RF-1
- [x] **T4** *Status tips* — RF-2
- [x] **T5** *Buddies* y nombres accesibles — RF-3
- [x] **T6** Orden de tabulación — RF-4
- [x] **T7** Contraste e iconos del tema oscuro — RF-5
- [x] **T8** Progreso y Cancelar en *Compute* — RF-6
- [x] **T9** Clasificador sin *Classify*; tooltips de «Elegir…» — RF-7, RF-8
- [x] **T10** Textos en español; `fuentes-pendientes.md`; índice de la bibliografía
- [x] **T11** Validación

## Validación (2026-11-24)

| RF | Test (`tests/test_ux_025f.py`) | Resultado |
|---|---|---|
| RF-1 | `test_every_parameter_has_sourced_help_or_is_pending`, `test_tooltips_show_definition_unit_range_and_source` | verde: 65 entradas con fuente citable y 35 pendientes, tras la regla 9 (ver abajo) |
| RF-2 | `test_every_menu_action_has_a_status_tip` (EN y ES) | verde |
| RF-3 | `test_inputs_have_labels_or_names` (barra lateral con 4 criterios y 7 diálogos) | verde |
| RF-4 | `test_tab_goes_down_the_sidebar` | verde |
| RF-5 | `test_text_contrast_reaches_wcag_aa` | verde (el menor, 5,97:1: título de grupo en el tema claro) |
| RF-6 | `test_compute_shows_progress_and_can_be_cancelled` | verde |
| RF-7, RF-8 | `test_classifier_is_live_and_pick_buttons_say_what_they_open` | verde |

## Qué se encontró

- **Siete anomalías del programa** al documentar (valores por defecto de
  RSData fuera de rango, Power Curve que ignora c y la ondulación, opciones
  que faltan…): se reportan en `fuentes-pendientes.md` §5, sin tocarlas.
- Al cerrar el programa, una ventana podía recibir `closeEvent` con su menú
  Editar ya destruido por Qt (`RuntimeError: QMenu already deleted` en
  `accelerators.assign`): se comprueba con `shiboken6.isValid`. Podría estar
  relacionado con la salida 127 abierta en `AGENTS.md`, pero no la arregla:
  la suite entera sigue saliendo a veces con 127 (266 tests, 0 fallos).
- El botón «Cancelar» del progreso usa el texto de Qt (su catálogo lo
  traduce); con una clave propia, el test de la spec 024 lo marcaba como
  inglés sin traducir en todos los diálogos.

## Decisiones de la propietaria tras la validación (2026-11-24)

- Rangos derivados por cálculo: **se aceptan**, con la derivación dicha.
- Γ de Cam-Clay en lb/in²: **se deja**, con la advertencia.
- **Regla 9 de `AGENTS.md`**: no se cita al fabricante del programa de
  referencia. Las 33 entradas que solo tenían sus manuales como fuente
  pasaron a pendientes (98 → 65 con ayuda); las citas de los libros de
  Hoek ya no nombran a quien los aloja. Test nuevo:
  `test_help_and_status_tips_name_no_vendor`. La investigación completa se
  guarda fuera del repositorio (`../Referencias/Ejemplos/ayuda_parametros_025f/`).
- Las anomalías encontradas pasan a la spec 026; las menciones antiguas
  al fabricante en el resto del repositorio, a la spec 027.
