# Spec 010 — Base de datos de propiedades de materiales (equivalente a la base de datos de referencia)

## Qué se construye

El equivalente OGR de la **base de datos de referencia** (analizado: búsqueda por palabras
clave con comodines; registro con Rock Name, Unit Weight, Fabric, Notes,
Location (región/país/localidad/lat/long/profundidad), Reference (tipo,
título, autor, editorial, año, páginas, volumen, ISBN, edición) y datos
de ensayo por pestañas: Compression (test type, diámetro/longitud de
testigo, confinamiento, ángulo a foliación, σc, E50, ν, Information
Quality 1–10), Tensile, Hoek-Brown, Velocity; navegación por páginas;
"Copy to Clipboard").

## Decisión clave: datos propios, no los de la base de datos de referencia

La base de datos de referencia es contenido propietario del fabricante del programa de referencia: **no se
copiará ni rastreará**. OGR-Data construye su propia base de datos
versionada en JSON a partir de bibliografía oficial (Hoek ch.11 ya
extraída en spec 003; candidatos a ampliar: tablas de Practical Rock
Engineering, fuentes USGS/USBR/NRCS). Cada registro lleva cita de fuente.

## Alcance v1

- Esquema de registro compatible con la base de datos de referencia (mismo modelo de datos).
- Semillas: las tablas de Hoek ya digitalizadas (sigci por grado R0–R6,
  mi por roca) convertidas en registros con referencia.
- GUI: diálogo de búsqueda (comodines `*`, frases entre comillas), lista
  de resultados con paginación, vista de registro, botón "Usar como
  material" (rellena el criterio GHB: sigci, mi, GSI manual).
- Edición de registros propios (añadir/editar/borrar) con referencia
  obligatoria.

## Criterios de aceptación

- Búsqueda con comodines y frases exactas sobre los registros semilla.
- "Usar como material" rellena sigci/mi correctamente.
- Un registro sin fuente no se guarda.

## Fuera de alcance

- Importación de la base de datos de referencia (propietaria).
- Coordenadas geográficas en mapa (la lat/long del esquema se guarda,
  no se visualiza).
