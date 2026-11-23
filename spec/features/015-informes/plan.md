# Plan 015 — Generador de informes

Referencia: captura `41_report_generator.png` y
`05_profundizacion.md` (Report Generator de RSData 1.009). Del diseñador
de RSData (ribbon, mapa del documento, marca de agua, cabeceras) se toma
solo el **modelo de contenido**: secciones con visibilidad por casillas.

## Núcleo (`core/report.py`, sin Qt)

- `SECTIONS`: índice de RSData en su orden (Cover Page, Table of
  Contents, Title, Project Summary, Project Settings, Samples, Defined
  Material Models, Defined Failure States, Defined Test Simulations,
  Defined Stress Paths) más **Graph Views** (las vistas añadidas con Add
  View To Report) tras Project Settings. `default_visibility()` = todas.
- `ReportView`: instantánea de una vista — título, material, criterio,
  unidad, filas de parámetros y de resultados ya formateadas, imágenes
  PNG con su pie, lectura del muestreador y fecha. Es una copia: editar
  el material después no cambia la vista (como una captura de RSData).
- `ReportViews`: lista ordenada con `add`, `remove`, `move` (arriba/abajo,
  devuelve el índice nuevo) y `rename`.
- `parameter_rows(material, unit)`: campos del registro con su etiqueta;
  tensiones de kPa a la unidad de visualización.
- `computed_rows(material, unit)`: GHB → mb, s, a, σt, σc, σcm, c, φ y
  Erm (mismo `compute` que la ventana); HB → σcm y MC equivalente (Hoek
  2002, a = 0,5); Power Curve y Barton-Bandis → MC de mejor ajuste en el
  rango (RocData 2004 p. 10). El resto no tiene resultados derivados.
- `build_html(project, views, visibility, title, generated)`: documento
  HTML5 autocontenido — CSS en línea, imágenes en `data:image/png;base64`,
  sin recursos externos; índice con anclas; saltos de página para
  imprimir (`@media print`). **Las secciones vacías se omiten** también
  del índice: Samples sin lecturas, Graph Views sin vistas, estados o
  rutas sin definir, materiales sin ensayos simulados. Desde la spec 013,
  Defined Test Simulations lista la configuración de cada ensayo, la
  rigidez del material y un resumen calculado (q pico y estado final).
- `write_report(path, html)`.

Interpretación de **Samples** (RSData no documenta su contenido): las
lecturas del muestreador (spec 008) activas al añadir cada vista.

## GUI

- Menú Analysis (nombres de RSData): **Report Generator…**, **Add View
  To Report**, **Manage Report View…**.
- Add View To Report: pestaña activa — Strength Graphs (σ1-σ3 y τ-σn)
  o Stress Path Graphs (las cuatro) — del material seleccionado, con sus
  parámetros y resultados. Las gráficas se capturan con el tema claro
  aunque la ventana use otro (el informe es para imprimir) y se restaura.
- `gui/report_dialog.py`:
  - `ManageReportViewsDialog`: lista, Up/Down/Remove, renombrar con doble
    clic.
  - `ReportGeneratorDialog`: título (por defecto el del proyecto o
    «Untitled Project»), casillas Section Visibility, número de vistas con
    acceso a Manage, **Generate…** (guarda `.html`) y abrir en el
    navegador para guardar/imprimir (PDF desde el navegador).
- Las vistas viven en la sesión: no se guardan en `.ogrdata` (PNG en
  base64 inflaría el proyecto); New/Load project las vacía.

## Fuera de v1

Plantillas corporativas, cabecera/pie, marca de agua, PDF nativo,
persistencia de vistas en el proyecto.
