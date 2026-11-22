# Spec 015 — Generador de informes

## Qué se construye

El **Report Generator** de RSData (Analysis: Report Generator / Add View
To Report / Manage Report View): componer un informe con las vistas de
las gráficas actuales y generarlo.

## Alcance v1

- "Add View To Report": captura la(s) gráfica(s) activas con su título
  y los parámetros del material en una lista ordenada.
- "Manage Report View": reordenar/quitar vistas.
- "Generate": documento HTML autocontenido (imágenes embebidas en base64
  + tabla de parámetros + fecha + título del proyecto). PDF queda fuera
  v1 (dependencia extra; HTML se imprime a PDF desde el navegador).

## Criterios de aceptación

- Informe con dos materiales: secciones con gráfica, parámetros y
  resultados calculados; HTML válido y autocontenido.
- Round-trip: añadir/quitar/reordenar antes de generar.

## Fuera de alcance

- Plantillas corporativas, encabezados personalizados, PDF nativo.
