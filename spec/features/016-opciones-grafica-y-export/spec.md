# Spec 016 — Opciones de gráfica y exportación

## Qué se construye

El **Graph Editor** (captura `35_*`) y el menú contextual de gráfica de
RSData (captura `34_*`), sobre nuestros canvas matplotlib:

- **Title and Axis**: título visible/editable, posición de etiquetas de
  ejes (Inside/Outside), rango de ejes manual o automático, eje cuadrado.
- **Graph Display**: rejilla, grosores/colores de ejes y fondo.
- **Series Display**: visibilidad, color, grosor y estilo por serie
  (envolvente, MC equivalente, puntos de estado, rutas de tensión).
- **Contextual**: Copy Graph as Image (ya), **Save Graph as Image**
  (PNG/JPG/BMP), **Export Graph to Excel** (CSV con los puntos de las
  series abierto en Excel, equivalente honesto del "Export to Excel" de
  RocData/RSData sin depender de Excel instalado).
- Zoom extents (escala a los límites naturales de la envolvente, como el
  "Zoom Extents" de RocData).

## Criterios de aceptación

- Guardar imagen con el diálogo de archivo (PNG por defecto).
- Export Excel: CSV con columnas por serie (σ3, σ1, σn, τ, MC…) listo
  para abrir en Excel.
- Editor de serie: cambiar color/grosor se refleja al vuelo.
- Tests sin Qt del render con opciones aplicadas (comparación de
  propiedades del objeto figura).

## Nota

matplotlib cubre todo esto nativamente; la spec es principalmente la capa
de UI y persistencia de las opciones en el proyecto.
