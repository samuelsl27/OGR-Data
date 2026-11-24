# Tareas 025b — Ventana principal: resultados a la vista

En orden de dependencia. Tests primero; suite entera en verde al cerrar
cada tarea; una tarea cada vez.

- [x] **T1** `QSettings` aislado en los tests: `gui/settings.py` (`app_settings()`), la ventana y `__main__` lo usan, el runner lo apunta a una carpeta temporal — RF-4 (base)
  - Hecho cuando: un test comprueba que el fichero de ajustes de la suite está en la carpeta temporal y la suite no toca `HKCU\Software\OpenGeoRock\OGR-Data`.
  - Hecho el 2026-11-24: `tests/test_ux_025b.py` (3 tests); suite 227/0. Comprobado a mano: con `theme = dark` puesto en el registro, la suite entera lo deja en `dark` (sin aislar, `test_theme.py` lo escribía a `light` al terminar).
- [x] **T2** Acciones como atributos (`_new_act`, `_open_act`, `_save_act`, `_copy_*_act`, `_compute_act`) sin cambiar los menús — RF-7 (base)
  - Hecho cuando: los tests de menús existentes siguen en verde y las acciones se alcanzan por atributo.
- [x] **T3** `ResultsPanel` en un dock a la derecha, rellenado desde `_redraw`; `results_text()`; botón Copiar material — RF-1, RF-2, RF-3
  - Hecho cuando: tests de RF-1…3 en verde y los que leían `_outputs.text()` leen el panel.
- [x] **T4** RF-9: MC equivalente o mensaje para los criterios que no son GHB — RF-9
  - Hecho cuando: test de Mohr-Coulomb (mensaje) y Power Curve (c, φ = `overlay_mc`).
- [x] **T5** Muestreador en el panel y en la barra de estado — RF-8
  - Hecho cuando: test de RF-8 y `test_samplers.py` en verde.
- [x] **T6** *Project Settings* (título y unidad) y `set_project_title`; fuera `_title_edit` — RF-6
  - Hecho cuando: test del diálogo y del paso de deshacer; los 5 archivos de test migrados.
- [x] **T7** Barra de herramientas con las mismas acciones y el selector de unidad — RF-7
  - Hecho cuando: test de RF-7.
- [x] **T8** Barra lateral por secciones; fuera unidad, título, archivo y portapapeles — RF-5, RF-6
  - Hecho cuando: test de RF-5/RF-6; captura a 1366×768.
- [x] **T9** Estado del panel y de la barra en `QSettings` y a través del cambio de idioma; View > Results panel / Toolbar — RF-4
  - Hecho cuando: test de RF-4 (cerrar y abrir, cambio de idioma).
- [x] **T10** Textos en español y revisión de `test_i18n.py` — todos
  - Hecho cuando: `test_i18n.py` en verde.
- [x] **T11** Validación final — todos los RF
  - Hecho cuando: cada RF con su test, lista UX de la guía marcada con capturas EN/ES y claro/oscuro a 1366×768 y 1280×720, suite entera en verde.

## Validación (2026-11-24)

Suite entera: **236 tests, 0 fallos** (sale con 127 tras los totales: la
anomalía abierta de `AGENTS.md`, también en `ba1298d`).

| RF | Test (`tests/test_ux_025b.py`) | Resultado |
|---|---|---|
| RF-1 | `test_results_panel_is_in_view_on_the_right` | verde |
| RF-2 | `test_results_follow_the_parameters` | verde |
| RF-3 | `test_panel_button_copies_the_material` | verde |
| RF-4 | `test_panel_and_toolbar_state_is_remembered` (+ T1: `test_suite_settings_live_in_a_temporary_ini_file`, `test_no_settings_are_built_anywhere_else`) | verde |
| RF-5 | `test_sidebar_holds_only_the_material` | verde |
| RF-6 | `test_sidebar_holds_only_the_material`, `test_project_settings_set_title_and_unit` | verde |
| RF-7 | `test_toolbar_shares_the_menu_actions` | verde |
| RF-8 | `test_sampler_reads_in_panel_and_status_bar` (+ `test_samplers.py`) | verde |
| RF-9 | `test_other_criteria_show_derived_results_or_why_not` | verde |

Capturas en [`capturas/`](capturas/): inglés claro y español oscuro a
1366×768, inglés claro a 1280×720, español con Power Curve (RF-9).

Lista UX de la guía (las reglas que aplica la spec):

- [x] U1 Resultados a la vista sin desplazar a 1366×768 y 1280×720.
- [x] U2 Barra lateral por secciones; proyecto y programa fuera.
- [x] U10 Lo avanzado (rigidez) sigue en su sección; nada frecuente escondido.
- [x] U12 Copiar material, guardar y calcular en sitio fijo (barra y panel).
- [x] U16 *Copy material* sigue diciendo lo que copia (sin cambios aquí).
- [x] U17 El panel se rellena en el mismo `_redraw` que las gráficas.

## Qué se encontró

- **Los resultados solo existían para Hoek-Brown generalizado** en la
  ventana, mientras que el informe ya calculaba los derivados de Hoek-Brown
  clásico, Power Curve y Barton-Bandis (`report.computed_rows`). El panel
  usa esas mismas filas para los criterios que no son GHB (RF-9): una sola
  fuente para la ventana y el informe. GHB conserva su formato actual; el
  de `computed_rows` (`.6g`) da cosas como `7.48901e-13 kPa` para una
  cohesión nula: lo resuelve 025e.
- **Etiquetas pintadas unas sobre otras**: el panel rehacía sus `QLabel`
  en cada edición y los viejos, pendientes de `deleteLater`, se seguían
  pintando hasta volver al bucle de eventos. Ahora se reutilizan.
- **Los tests escribían en el registro del usuario** (T1, ver el plan).
- **Pendiente para 025f** (U13): con el tema oscuro, los iconos estándar
  de Qt deshabilitados (Rehacer sin nada que rehacer) casi no se ven.
- Las tareas T2–T9 se escribieron antes que sus tests (se pidió hacerlas
  seguidas); los tests se escribieron después y se comprobó que fallan con
  el código anterior porque usan atributos que no existían.
