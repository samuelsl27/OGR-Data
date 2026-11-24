# Plan 025c — Menús y convenciones de Windows

Sin código. Cada apartado dice qué RF cubre.

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| Los 8 menús de la spec, construidos en `_create_menus` con las acciones como atributos (025b) | Mantener los 11 de RSData: cinco con una sola entrada (U3) | RF-1, RF-3 |
| Las acciones de la barra lateral (clasificador, ajuste) y del menú contextual del árbol (color, símbolo, borrar) tienen entrada en la barra de menús; las del menú contextual de una gráfica (guardar imagen, CSV, zoom) **no**: actúan sobre la gráfica pulsada | Llevar también las de gráfica al menú: habría que elegir a qué gráfica se aplican | RF-2 |
| Aceleradores (`&`) asignados por código (`gui/accelerators.py`) al terminar de construir los menús: primera letra libre de cada palabra, si no cualquier letra libre, sin repetir dentro de un menú; se vuelven a asignar cuando cambia un texto (Deshacer «…», Recientes) | Escribir `&` en cada clave de traducción: duplica el diccionario, y el español necesita otras letras que nadie comprobaría | RF-4 |
| Atajos estándar de Qt (`QKeySequence.StandardKey`) para Nuevo, Abrir, Guardar, Guardar como, Deshacer; F5 Compute, F1 atajos | Escribir las teclas a mano: Qt ya da la de cada plataforma | RF-4 |
| La ventana guarda la ruta del proyecto (`_file_path`): Save escribe en ella o hace Save As si no hay; abrir, guardar y Save As la fijan; Nuevo la borra; Import .roc no la toca (añade un material) | Pedir siempre la ruta (lo de hoy): rompe Ctrl+S | RF-5 |
| Recientes en `app_settings()` (clave `recent_projects`, lista de 8, el último primero); un reciente que ya no existe se quita y se dice en la barra de estado | Un aviso modal: interrumpe por algo que no tiene remedio (U5, U15) | RF-6 |
| Edit > Delete con Supr, atajo de contexto del árbol (`WidgetShortcut`): fuera del árbol Supr sigue borrando texto en los campos | Atajo de ventana: robaría Supr a los campos numéricos | RF-7 |
| Título: «nombre.ogrdata[*] (título del proyecto) - OGR Data», o «Untitled» / «Sin título»; la convención de Windows es documento primero | Solo el título del proyecto (lo de hoy): dos proyectos con el mismo título no se distinguen | RF-8 |
| F1 abre un diálogo **no modal** con la tabla de atajos, generada desde las acciones de los menús | Una tabla escrita a mano: se desactualiza | RF-9 |
| «Open…» en inglés; mensajes y títulos de diálogo «Open project», «Open failed» | — | RF-10 |
| View > Stress unit ▸ con kPa/MPa (acciones exclusivas ligadas a `_set_stress_unit`) | — | spec, tabla de menús |

## Capas y archivos

- `ogr_data/gui/accelerators.py` — nuevo: `assign(menu)` y `plain(text)`.
- `ogr_data/gui/shortcuts_dialog.py` — nuevo: tabla de atajos.
- `ogr_data/gui/main_window.py` — menús, ruta del proyecto, Save/Save As, recientes, Supr, título, F1.
- `ogr_data/gui/i18n/es_main.py` — textos nuevos; fuera los muertos («Load…», «Save…», títulos de menús que desaparecen).
- Tests que comparan textos de menú (`test_theme`, `test_calibration`, `test_database`, `test_report`, `test_history`, `test_i18n`, `test_units`, `test_ux_025b`) pasan a comparar sin `&`.
- Núcleo, API, MCP, formatos: sin cambios.

## Estrategia de tests (`tests/test_ux_025c.py`, offscreen)

- RF-1: número de menús ≤ 9 y cada uno con ≥ 2 entradas.
- RF-2: los botones de la barra lateral y las entradas del menú contextual del árbol tienen una acción de la barra con el mismo texto.
- RF-3: lista de nombres de RSData presentes (Define Failure States…, Compute, Calibrate…, Report Generator…, …).
- RF-4: atajos de las acciones; aceleradores sin repetir en cada menú, en inglés y en español.
- RF-5/RF-6: guardar en carpeta temporal, Save sin diálogo la segunda vez, recientes en orden, reciente borrado → quitado y mensaje.
- RF-7: Supr con el árbol enfocado borra; con un campo enfocado, no.
- RF-8: título con «Untitled», con nombre de archivo y con título del proyecto.
- RF-9: F1 abre el diálogo (no modal) y lista Ctrl+S.
- RF-10: «Open…» en File.

## Riesgos

- Tests existentes que comparan textos de menú: se adaptan con `plain()`.
- Diálogos de archivo en tests: se prueban las funciones con ruta (`save_project_to`, `open_project_file`), no el diálogo.
