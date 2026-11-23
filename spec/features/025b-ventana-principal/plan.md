# Plan 025b — Ventana principal: resultados a la vista

Sin código. Cada apartado dice qué RF cubre.

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| Panel nuevo `ResultsPanel` en `gui/results_panel.py`, dentro de un `QDockWidget` a la derecha (`objectName` fijo para guardar su estado) | Seguir con el `QLabel` monoespaciado `_outputs`: no se puede alinear en columnas ni añadir el botón y el muestreador | RF-1, RF-3 |
| El panel recibe filas `(etiqueta, valor)` ya formateadas y un título (material, criterio); la ventana las calcula en `_redraw`, como hoy | Que el panel calcule: duplicaría la lógica de `_redraw` y del núcleo | RF-1, RF-2 |
| `results_text()` en el panel devuelve el mismo texto que hoy da `_outputs.text()` (filas `etiqueta = valor`) | Cambiar los 3 tests que leen `_outputs.text()` a otra forma: el texto plano sirve también para copiar y para el informe | RF-1 |
| RF-9 con `material_results.overlay_mc` llamado siempre para el panel (no solo con *Overlay MC* activo) | Mostrar el MC equivalente solo con la superposición: el número dependería de una casilla de dibujo (regla 7) | RF-9 |
| El muestreador escribe su lectura en la barra de estado (como hoy, los tests la leen) y en una sección «Sampler» del panel, oculta sin muestreador | Solo en el panel: rompe los atajos de lectura actuales | RF-8 |
| Barra de herramientas `QToolBar` con iconos estándar de Qt (`QStyle.StandardPixmap`) y texto al lado; usa las **mismas** `QAction` del menú | Botones propios: dos objetos por acción que se desincronizan (habilitado, atajos) | RF-7 |
| Acciones de menú que hoy se crean con `addAction(texto, slot)` y se necesitan en la barra pasan a atributos `QAction` (`_new_act`, `_open_act`, `_save_act`, `_copy_material_act`, `_copy_data_act`, `_copy_plot_act`, `_compute_act`) | Buscar acciones por texto: falla en español | RF-7 |
| Selector de unidad: un `QComboBox` en la barra y otro en *Project Settings*, los dos llaman a `_set_stress_unit` | Uno solo: el diálogo no podría cambiarla | RF-6, RF-7 |
| *Project Settings* (`gui/project_settings_dialog.py`): título y unidad; al aceptar, la ventana aplica el título con un paso de deshacer y la unidad como hoy | Mantener `_title_edit` como campo oculto: estado fantasma | RF-6 |
| `_title_edit` desaparece; el título vive en `self._project.title` y se cambia con `set_project_title(texto)` (punto de deshacer) | Dejar el `QLineEdit` fuera de la vista: dos fuentes de verdad | RF-6 |
| Barra lateral: `QGroupBox` por sección («Material», «Stress range», «Parameters», «Stiffness»); el nombre del material con etiqueta en un `QFormLayout` | Pestañas como RSData: esconden el rango de tensiones mientras se editan parámetros | RF-5 |
| Clasificador y ajuste quedan como botones en la sección «Material» (herramientas de estimación del material) y además en el menú (025c los ordenará) | Quitarlos de la barra lateral ahora: 025c aún no ha dado su sitio en los menús | RF-5 |
| Estado del panel y de la barra: `saveState()` en `QSettings` (clave `window_state`) al cerrar y `restoreState()` al abrir; el cambio de idioma lo pasa en `adopt()` | Guardar solo «visible sí/no»: se pierde flotante/ancho | RF-4 |
| Los tests usan un `QSettings` aislado: el runner fija `QSettings.setPath` a una carpeta temporal y la ventana crea sus ajustes con el formato por defecto (`QSettings.defaultFormat()` + `IniFormat` en tests) | Seguir escribiendo en el registro del usuario: los tests ya le cambian tema y unidad (anomalía, ver abajo), y esta spec añadiría el estado de la ventana | RF-4 |

## Capas y archivos

- `ogr_data/gui/results_panel.py` — nuevo: `ResultsPanel` (título, filas, mensaje, sección del muestreador, botón Copiar material).
- `ogr_data/gui/project_settings_dialog.py` — nuevo: título y unidad.
- `ogr_data/gui/settings.py` — nuevo: `app_settings()` única fuente de `QSettings` (formato por defecto, organización y aplicación).
- `ogr_data/gui/main_window.py` — barra lateral por secciones, dock, barra de herramientas, acciones como atributos, `_redraw` rellena el panel, `_sample_at` escribe en los dos sitios, título sin `QLineEdit`, `adopt` y `closeEvent` con el estado.
- `ogr_data/__main__.py` — usa `app_settings()`.
- `ogr_data/gui/i18n/es_main.py` — textos nuevos.
- `tests/_runner.py` — `QSettings` en carpeta temporal antes de cargar tests.
- Núcleo, API y MCP: sin cambios.

## Modelo de datos

Ninguno: `.ogrdata` ya guarda `title` y `stress_unit`. Clave nueva de
`QSettings`: `window_state` (bytes de `saveState`).

## Validación numérica

No hay fórmulas nuevas. RF-9 usa `overlay_mc`, ya validado (spec 008,
Hoek 2002 / RocData 2004); el test compara el valor del panel con la
llamada directa al núcleo.

## Estrategia de tests (`tests/test_ux_025b.py`, offscreen)

- RF-1: a 1366×768, el panel es visible y su `geometry()` cae dentro de la ventana, sin barra de desplazamiento; con GHB tiene las 9 filas.
- RF-2: cambiar GSI cambia mb en el panel sin otra acción.
- RF-3: el botón del panel deja en el portapapeles lo mismo que *Copy material*.
- RF-4: ocultar el panel, cerrar, abrir otra ventana: sigue oculto; `toggleViewAction` en View.
- RF-5/RF-6: títulos de las secciones en orden; no hay en la barra lateral ni unidad, ni título, ni botones de archivo/portapapeles.
- RF-7: la barra tiene las acciones pedidas y son las mismas `QAction` que las del menú.
- RF-8: con el muestreador, un clic escribe lo mismo en la barra de estado y en el panel; sin muestreador la sección está oculta.
- RF-9: Mohr-Coulomb muestra el mensaje; Power Curve muestra c y φ iguales a `overlay_mc`.
- *Project Settings*: cambiar el título es un paso de deshacer y cambia el título de la ventana.
- Idioma y tema: el panel en español y en oscuro (captura revisada a mano).
- Tests existentes que usan `_title_edit` de la ventana (5 archivos: history, i18n, materials, report, units) pasan a `set_project_title`/`_project.title`.

## Riesgos

- Ancho: el dock quita ~230 px a las gráficas; a 1280×720 se comprueba que las dos gráficas siguen legibles (captura).
- `restoreState` con un estado de otra versión: Qt lo ignora si no casa; se comprueba que no rompe.
- Cambiar el `QSettings` del runner puede destapar tests que dependían del estado del usuario: se verán en la primera corrida.

## Anomalía encontrada al planificar (corregida en T1)

Los tests escriben en el `QSettings` real del usuario
(`HKCU\Software\OpenGeoRock\OGR-Data`): pasar la suite cambia su tema,
unidad e idioma guardados (de ahí los `# QSettings may persist a previous
run` de `test_units.py` y `test_materials.py`). Incumple la regla 5. La
tarea T1 lo corrige porque esta spec añade estado guardado.
