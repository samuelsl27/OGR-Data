# Plan 011 — Proyectos multi-material

Modelo: panel *Visibility* de RSData (captura `03_*`: árbol de materiales
con ojo y papelera, botones *Add Material* con desplegable *Add Rock
Template / Add Soil Template* y *Duplicate Material*; panel *Properties*
con el nombre) y menú contextual sobre un material
(`RSData_analisis/03_interfaz_y_menus.md`). Se mantiene la sencillez del
viejo RocData: la barra lateral sigue siendo el formulario, ahora del
material seleccionado.

## Núcleo (`core/project.py`, sin Qt)

- `Material`: nombre, criterio, parámetros (kPa/grados del registro),
  `sig3max_mpa`, `Application` (modo custom/tunnel/slope + peso unitario
  + profundidad de la spec 009, que pasan a ser **por material** como el
  *Failure Range* de RSData), color, símbolo, visible. Los parámetros que
  falten se completan con los defectos del criterio.
- `Project`: lista de materiales (≥1), índice seleccionado, título,
  unidad de visualización y opciones de gráfica. Operaciones: `add`
  (plantilla), `append` (importación), `duplicate`, `remove`, `rename`,
  nombres únicos ("Rock", "Rock 2"…; duplicado "X - Copy") y paleta de
  colores para los añadidos.
- Formato **`ogr-data-project/2`**: `{title, stress_unit, graph_options,
  selected, materials: [...]}`. Un `.ogrdata` v1 (spec 007: un material
  suelto en la raíz) se carga como proyecto de un material, con sus
  título/unidad/opciones de gráfica.
- `criteria_envelopes.envelopes(key, params, sig3max)`: envolvente de un
  material en ambos espacios (principal + tangente de Mohr; solo
  cortante; o ninguna), para dibujar los demás materiales.

## Plantillas (decisión OGR, no dato de RSData)

RSData documenta las plantillas solo como "Material Model + Failure State
Set" (roca) y "Material Model + Test, Stress Path" (suelo); no consta qué
criterio usa cada una. OGR Data elige: **Rock → Generalized Hoek-Brown**,
**Soil → Mohr-Coulomb**, ambos con los defectos del registro (capturados
de RSData). *Add Material* a secas = criterio por defecto del programa
(el primero del registro, Mohr-Coulomb). La parte de estados de fallo y
rutas de las plantillas llega con la spec 012.

## GUI

- Grupo **Materials** arriba de la barra lateral: `QTreeWidget` (casilla
  = visibilidad, muestra de color, nombre editable con doble clic/F2) +
  *Add Material* (con desplegable Rock/Soil), *Duplicate*, *Delete*
  (deshabilitado con un solo material; pide confirmación). Árbol y no
  lista para colgar en la 012 los estados y rutas de cada material.
- Menú contextual: añadir (3 variantes), duplicar, renombrar, color…,
  color automático, símbolo (para los puntos de la 012), copiar material,
  borrar. Menú **Materials** en la barra con las mismas acciones; File
  gana *New Project*.
- Sincronización: el formulario edita el material seleccionado; cada
  `refresh` lo vuelca al proyecto (`_store_current`) salvo durante la
  carga de otro material (`_loading`). Al cambiar de selección se carga
  criterio, parámetros (ahora también casillas y combos — antes
  `_apply_project` solo restauraba los numéricos), σ3max y aplicación.
  El campo de nombre renombra en vivo el material (nombre único).
- Gráficas: el material seleccionado se dibuja con su color (o el del
  tema si es "automático"; un color fijado en el Graph Editor manda);
  los demás visibles, con su color y debajo del seleccionado; leyenda de
  nombres cuando hay más de uno. Un material oculto se sigue editando
  pero no se dibuja ni se muestrea.
- Portapapeles (spec 005): *Copy material* copia el seleccionado.
- Import `.roc`: añade el material importado al proyecto (antes
  sustituía el único material).
- Export CSV (spec 016): añade columnas por cada material visible no
  seleccionado, etiquetadas con su nombre.

## Correcciones incluidas (detectadas al verificar la ventana)

- **Ejes en unidades de visualización (spec 017)**: las gráficas dibujaban
  MPa con etiquetas "(kPa)". Ahora los datos siguen en MPa internos y un
  formateador de marcas muestra la unidad elegida; el Graph Editor edita
  los rangos en la unidad de visualización y los guarda en MPa.
- **Graph Editor**: abrirlo y tocar cualquier control congelaba el color
  por defecto de cada serie como color de usuario; ahora solo se guarda
  el color elegido explícitamente.
- Tema: indicadores de casilla en vistas de árbol/lista (la hoja de
  estilo los ocultaba con el estilo windows11) y color de texto en vistas
  del tema oscuro. La barra lateral abre a su ancho completo.

## Alternativas descartadas

- Varias ventanas/pestañas (una por material): rompe la comparación de
  envolventes en la misma gráfica, que es el valor del multi-material.
- Mantener `save_project(name, criterion, …)` de la v1: la API pasa a
  `save_project(path, Project)` / `load_project(path) -> Project`; los
  tests de 007/016/017 se adaptan.

## Tests

`tests/test_materials.py`: plantillas y nombres únicos, duplicar (copia
independiente)/borrar/renombrar, round-trip v2 con 4 criterios (incluido
uno sin envolvente), migración v1, errores de validación, helper de
envolventes, y offscreen: árbol/selección conservando cada material
(incluidas casillas y modo túnel), dibujo de otros materiales, leyenda y
visibilidad, duplicar/renombrar/borrar desde la GUI, copiar el material
seleccionado, guardar/abrir proyecto e importar `.roc`, *New Project*.
