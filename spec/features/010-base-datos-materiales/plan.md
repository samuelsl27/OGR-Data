# Plan 010 — Base de datos de materiales (equivalente a la base de datos de referencia)

Modelo: la base de datos de referencia (capturas 36 y 37): panel de búsqueda (palabras clave,
`*`, "frases"), "Search Records for … Showing Results a - b of n" con 14
resultados por página, vista de registro y botones Edit / Delete / Copy
to Clipboard / Copy to New Record; menú Favorites; exportación a Excel.

## Datos (150 registros internos, todos con fuente; nada de la base de datos de referencia)

1. **Tablas del programa** (49): 42 rocas de la Tabla 3 de Hoek (mi ±,
   con su MR de *Practical Rock Engineering 2023*, fig. 13) y los 7
   grados de estimación de campo de σci (Tabla 2 de Hoek).
2. **CANMET 1995** (77): Jackson, Gorski & Gyenge, *Geotechnical
   Properties of Rock*, CANMET – Natural Resources Canada (repositorio
   abierto OSTR de NRCan). Rocas de minas canadienses: densidad, σt, Qu,
   E50, ν, Vp, porosidad (Tabla 1) y constantes de Hoek-Brown intactas y
   residuales con su rango de σ3 (Tabla 2); referencia al informe MRL
   original (Tabla 3). Es el origen de los registros canadienses que se
   ven en la base de datos de referencia, tomado de la publicación oficial.
3. **MnDOT 2018** (24): Folta, Sharpe, Hu & Labuz, *Development of a Rock
   Strength Database*, Minnesota DOT MN/RC 2018-19 ("No restrictions"):
   21 sondeos del proyecto TH 53 (134 ensayos uniaxiales: medias + cada
   probeta) y 3 conjuntos triaxiales (Platteville Formation, Glenwood
   Shale, sedimentos cretácicos de SP804-81) con cada (σ3, σ1).

Transcripción: los dos informes tienen tablas no fiables como texto (OCR
ruidoso / columnas desplazadas). Se transcribieron valor a valor desde
imágenes de las páginas, con verificación doble y controles cruzados
(CANMET: Tablas 1 y 2 independientes cruzadas en σt y Qu; MnDOT: tablas
SI contra las de unidades US, área y densidad recalculadas, E contra las
gráficas). Las incoherencias encontradas son **de las fuentes** (vistas
en las imágenes) y se conservan tal cual, anotadas en el registro.
Procedencia completa en `ogr_data/data/db_sources/README.md`; los PDF
originales en `Referencias/Bibliografia/Bases_de_datos/`.

No se inventa nada: la litología de los testigos TH 53 y la ubicación de
los proyectos triaxiales no constan en el informe y quedan como "not
stated"; no se derivan latitudes/longitudes (el informe no da el sistema
de coordenadas). La probeta 120 de MnDOT (incoherente en el propio
informe) queda fuera de las medias y entra como excluida.

## Núcleo

- `core/database.py`: esquema compatible con la base de datos de referencia (+ densidad, porosidad,
  constantes residuales, rango de confinamiento, nº de probetas,
  `specimens`); búsqueda AND con `*` y frases; paginación de 14;
  validación (fuente obligatoria); registros del usuario y **favoritos**
  en JSON (`…/OpenGeoRock/OGR-Data/materials_db.json`); `export_csv`;
  `to_material_parameters`; `specimen_points`.
- `core/db_sources.py`: importadores CANMET y MnDOT desde los CSV
  empaquetados (peso unitario = densidad × 9,81/1000).

## GUI

Analysis → *Material Database…*: búsqueda + filtro (todos / internos /
míos / favoritos), resultados paginados con ★, vista del registro con la
tabla de probetas; botones ☆ Favourite, Copy to New / Edit / Delete (solo
los del usuario), Copy to Clipboard, **Print / PDF**, **Use as Failure
State** (las probetas (σ3, σ1) pasan a un estado de fallo del material
actual, las marcadas como dudosas como excluidas) y **Use as Material**
(material GHB nuevo con σci y mi); *Export Results to Excel (CSV)*.

## Fuentes descartadas o pendientes

- BGS (Open Government Licence), p. ej. Sidmouth Mudstone: descarga por
  la aplicación del NGDC con aceptación de licencia (manual).
- DTIC AD0646610, USACE EM 1110-2-1906, FHWA: rechazan descargas
  automáticas (403); no se fuerza.
