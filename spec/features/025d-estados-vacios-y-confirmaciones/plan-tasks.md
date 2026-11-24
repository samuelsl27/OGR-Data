# Plan y tareas 025d — Estados vacíos y confirmaciones

Aprobada al pedir la propietaria «continúa» (2026-11-24). Duda de la spec
resuelta con la opción de la guía (U6, GoodUI «Designing for zero data»):
el estado vacío **lleva botones que ejecutan** la acción, además de decir
dónde está en el menú.

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| Barra de aviso sobre las *Stress Path Graphs* con dos botones (Define Stress Paths…, Define Test Simulations…), visible mientras no haya nada que dibujar; cada gráfica vacía lo dice en el centro | Solo el texto en las gráficas: cuatro veces el mismo aviso y ningún botón | RF-1 |
| El panel de animación muestra qué necesita (simulación calculada, Ensayos > Calcular F5) | — | RF-2 |
| Los diálogos de estados, trayectorias y simulaciones muestran un texto por tipo en lugar del editor deshabilitado; «Add» en vez de «+»; Delete, Duplicate, Up y Down deshabilitados sin elementos | Dejar el editor gris: no dice qué hacer | RF-3 |
| Borrar material, estado, trayectoria o simulación sin pregunta, con aviso «Deshacer (Ctrl+Z) lo recupera» en la barra de estado | Mantener la pregunta: incoherente con los estados (que no la tenían) y con el deshacer | RF-4 |
| Delete Material (menú y botón) deshabilitado con el motivo («un proyecto conserva al menos un material»); *Export Graph to Excel* deshabilitado con motivo si la gráfica no tiene datos | Avisar después del clic | RF-5 |
| Se pregunta solo lo irreversible (ver inventario) | — | RF-6 |

## Inventario de `QMessageBox` (23 al empezar)

| Dónde | Qué | Decisión |
|---|---|---|
| `main_window` borrar material | pregunta | **quitada** (RF-4) |
| `main_window` exportar gráfica vacía | información | **a la barra de estado**; la entrada del menú ya está deshabilitada (RF-5) |
| `main_window` Erm sin GHB | información | queda: el botón Erm ya estaba deshabilitado con su motivo fuera de GHB; solo se llega por código |
| `main_window` cambios sin guardar | pregunta | queda (irreversible, RF-6) |
| `main_window` Compute con simulaciones fallidas | información | queda: es el detalle de un resultado, no una confirmación (candidata a panel en 025f) |
| `main_window` About | about | queda |
| `main_window` abrir / guardar / importar / base de datos / Pick fallidos (5) | aviso | quedan: errores de E/S con su texto |
| `database_dialog` borrar registro de usuario | pregunta | queda: la base de datos no está en el historial de deshacer (irreversible, RF-6) |
| `database_dialog` errores de registro, uso como material o estado (4) | aviso | quedan (errores) |
| `report_dialog`, `states_dialog` (2), `table_field` (2) | aviso | quedan (errores de datos o de E/S) |

## Tareas

- [x] **T1** Tests (`tests/test_ux_025d.py`) — todos
- [x] **T2** Barra de aviso y texto en gráficas vacías — RF-1
- [x] **T3** Aviso del panel de animación — RF-2
- [x] **T4** Estado vacío de los diálogos, «Add», botones deshabilitados — RF-3
- [x] **T5** Borrar sin pregunta con aviso de deshacer — RF-4, RF-6
- [x] **T6** Acciones deshabilitadas con motivo — RF-5
- [x] **T7** Textos en español; claves muertas fuera («Delete material», «Delete material '{0}'?», «Export»)
- [x] **T8** Validación

## Validación (2026-11-24)

Suite entera: **250 tests, 0 fallos** en dos corridas (una sale con 0 y otra con 127 tras los totales: la anomalía abierta de `AGENTS.md`).

| RF | Test (`tests/test_ux_025d.py`) | Resultado |
|---|---|---|
| RF-1 | `test_empty_path_graphs_say_what_is_missing` | verde |
| RF-2 | `test_animation_panel_says_what_it_needs` | verde |
| RF-3 | `test_empty_item_dialogs_show_the_first_step` | verde |
| RF-4 | `test_delete_asks_nothing_and_says_how_to_undo` | verde |
| RF-5 | `test_unavailable_actions_are_disabled_with_a_reason` | verde |
| RF-6 | inventario de arriba + `test_delete_asks_nothing_and_says_how_to_undo` | verde |

Capturas en [`capturas/`](capturas/): gráficas de trayectorias vacías y
diálogo de estados vacío, en inglés y español.

Lista UX: U5 (deshacer en vez de preguntar), U6 (estados vacíos con el
siguiente paso), U7 (motivo junto a lo deshabilitado), U15 y U16 (aviso de
lo borrado) marcadas.

## Qué se encontró

- Borrar un estado o una trayectoria nunca preguntaba y borrar un material
  sí: la misma acción con dos comportamientos. Ahora ninguno pregunta.
- Las gráficas vacías siguen mostrando la escala por defecto de Matplotlib
  (±0,04) detrás del texto; se deja así para no inventar ejes.
