# Plan 010 — Base de datos de materiales (equivalente RocProp)

Modelo: RocProp (capturas 36 y 37): panel de búsqueda (palabras clave,
`*`, "frases"), "Search Records for … Showing Results a - b of n" con 14
resultados por página, vista de registro y botones Edit / Delete / Copy
to Clipboard / Copy to New Record.

## Datos

- **Ningún dato de RocProp** (propietario). Registros **internos** de solo
  lectura generados desde las tablas con fuente del programa:
  - 42 rocas de la Tabla 3 de Hoek (mi ± dispersión, tipo/clase/grupo/
    textura; marca de "estimado") con su rango MR de *Practical Rock
    Engineering 2023*, fig. 13, cuando existe;
  - 7 grados de estimación de campo de σci (Tabla 2 de Hoek): valor y
    rango en el bloque Compression (test type "Field estimate").
  - No se inventan Information Quality, unidades de peso ni ubicaciones:
    quedan vacíos.
- **Registros del usuario** en `…/OpenGeoRock/OGR-Data/materials_db.json`
  (GenericDataLocation de Qt), formato `ogr-data-materials-db/1`.
  Referencia obligatoria (título y autor); Information Quality 1-10.

## Núcleo (`core/database.py`, sin Qt)

Esquema RocProp-compatible (registro, ubicación, referencia, bloques
Compression / Tensile / Hoek-Brown / Velocity; extensiones: rango de UCS,
mi ±, MR, tabla/figura de la fuente). Búsqueda AND, sin distinguir
mayúsculas: palabra completa, `*` dentro de palabra, frase exacta entre
comillas; sobre nombre, prefijo, fábrica, notas, ubicación y referencia.
Paginación de 14. `to_material_parameters` (σci del bloque Hoek-Brown o
UCS, y mi) y `clipboard_text` (tabulado).

## GUI

`gui/database_dialog.py`: búsqueda + filtro de origen (todos / internos /
míos), resultados paginados, vista HTML del registro; New / Copy to New /
Edit / Delete (solo los del usuario) con editor por pestañas que valida;
Copy to Clipboard; **Use as Material** → material GHB nuevo con σci y mi
del registro (GSI y D quedan por defecto: aviso en la barra de estado).
Menú Analysis → *Material Database…* (en RSData: Open RocProp).

## Pendiente

- Ampliar con **datos de ensayo reales de fuentes abiertas oficiales**
  (candidatas: USBR, USGS, informes públicos), cada registro con su
  referencia: tarea de investigación aparte.
- Favoritos, exportación a Excel e impresión de RocProp.
- Mapa de lat/long (fuera de alcance en la spec).
