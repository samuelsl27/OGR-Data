# Tareas 025c — Menús y convenciones de Windows

- [x] **T1** `gui/accelerators.py` (`assign`, `plain`) con sus tests — RF-4
  - Hecho cuando: test de letras únicas por menú con textos de ejemplo en EN y ES.
- [x] **T2** Los 8 menús, con clasificador, ajuste, base de datos y Delete — RF-1, RF-2, RF-3
  - Hecho cuando: tests de RF-1…3; tests existentes adaptados.
- [x] **T3** Atajos y aceleradores en la ventana; F5, F1 — RF-4, RF-9
  - Hecho cuando: test de RF-4 en los dos idiomas; F1 abre el diálogo.
- [x] **T4** Ruta del proyecto, Save / Save As, título de ventana — RF-5, RF-8, RF-10
  - Hecho cuando: tests de RF-5, RF-8, RF-10.
- [x] **T5** Proyectos recientes — RF-6
  - Hecho cuando: test de RF-6.
- [x] **T6** Supr en el árbol — RF-7
  - Hecho cuando: test de RF-7.
- [x] **T7** Textos en español, claves muertas fuera — todos
  - Hecho cuando: `test_i18n.py` en verde.
- [x] **T8** Validación final — todos
  - Hecho cuando: cada RF con su test, capturas de los menús en EN/ES, suite entera en verde.

## Validación (2026-11-24)

Suite entera: **245 tests, 0 fallos** (esta vez con código de salida 0).

| RF | Test (`tests/test_ux_025c.py`) | Resultado |
|---|---|---|
| RF-1 | `test_eight_menus_none_with_one_entry` | verde |
| RF-2 | `test_every_window_action_is_in_the_menu_bar` | verde |
| RF-3 | `test_eight_menus_none_with_one_entry` (nombres del programa de referencia en Tests y Report) | verde |
| RF-4 | `test_shortcuts_and_accelerators_in_both_languages`, `test_accelerators_are_unique_per_menu`, `test_word_initials_come_first` | verde |
| RF-5 | `test_save_writes_to_the_project_file_and_title_names_it` | verde |
| RF-6 | `test_recent_projects` | verde |
| RF-7 | `test_delete_key_in_the_tree_only` | verde |
| RF-8 | `test_save_writes_to_the_project_file_and_title_names_it` (también tras cambiar de idioma) | verde |
| RF-9 | `test_f1_lists_the_shortcuts` | verde |
| RF-10 | `test_save_writes_to_the_project_file_and_title_names_it` | verde |

Capturas de todos los menús en [`capturas/`](capturas/) (inglés y español).

Lista UX de la guía:

- [x] U3 8 menús, ninguno de una entrada.
- [x] U4 Atajos estándar, aceleradores Alt, Guardar como y recientes.
- [x] U5 Un reciente que ya no existe se dice en la barra de estado, sin modal.
- [x] U12 Supr en el árbol; F5 calcula.
- [x] U14 «Open…» / «Abrir…» en los dos idiomas y en todos los mensajes.

## Qué se encontró

- El cambio de idioma habría perdido la ruta del archivo, nueva en esta
  spec (la ventana nueva diría «Sin título» y Guardar pediría ruta):
  `adopt()` la pasa ahora, con test.
- Los textos con `&` rompen las comparaciones de los tests y la del
  diccionario de traducción: `accelerators.plain()` las quita, y
  `test_i18n` compara ya sin `&`.
- Claves de traducción que dejan de usarse y se quitan: «Load…», «Save…»,
  «Load project», «Load failed», «Calibrate», «Stress Paths».
- Las acciones del menú contextual de cada gráfica (guardar imagen, CSV,
  zoom) no van a la barra de menús: dependen de la gráfica pulsada (plan).
