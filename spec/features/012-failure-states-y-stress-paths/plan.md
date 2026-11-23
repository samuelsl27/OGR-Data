# Plan 012 — Estados de fallo y rutas de tensión

Modelo: diálogos *Define Failure States* y *Define Stress Paths* de RSData
(capturas `31_*`, `32_*`): lista a la izquierda (añadir, borrar, duplicar,
subir/bajar), editor a la derecha (nombre + color, ajustes del ensayo) y
tablas con cortar/copiar/pegar/insertar/borrar filas/importar/exportar.
Color por defecto de un estado o ruta nuevo en RSData: **#800000**
(muestreado de ambas capturas).

## Núcleo (`core/states.py`, sin Qt)

- `FailureState`: nombre, color, símbolo, Test Type, `peak` y `residual`
  (listas de `TestPoint(x, y, exclude)` en kPa).
- `StressPath`: nombre, color, Test Type, Seepage Condition (Drained/
  Undrained), Loading Direction (triaxial: Lateral/Axial), Strain Type
  (uniaxial: Lateral/Volumetric), Initial Effective Lateral Stress
  (defecto 100 kPa) y K0 (defecto 1) y pasos `PathStep(EpsilonZZ,
  tensión, deformación)` cuyas columnas siguen al diálogo de RSData
  (ver "Segunda iteración").
- Viven **por material** (`Material.failure_states/stress_paths`), como
  pide la spec; en RSData se definen globalmente y se "aplican" a
  materiales. Claves aditivas en el `.ogrdata` v2 (ficheros de la 011 sin
  ellas cargan con listas vacías). Duplicar un material los copia.
- Plantillas (spec 011): *Rock* trae un estado vacío "State 1" (RSData:
  "Material Model + Failure State Set"); *Soil* una ruta "Path 1"
  (Uniaxial, como la captura 32).
- `parse_rows`: parser único de tablas pegadas de Excel o leídas de
  CSV/texto (tabulador, punto y coma o coma decimal, coma, espacios;
  salta cabeceras y notas; columna opcional Exclude). El diálogo de
  ajuste (spec 006) pasa a usarlo, como pide la spec.
  `write_rows_csv` / `read_rows_csv`: exportación/importación; los
  CSV oficiales de ejemplo de RocData se leen tal cual.

## Dibujo (fuente: RocData 3.0 User's Guide, pp. 13 y 47-48)

"For triaxial test data, the lab or field data is plotted as points in
principal stress space, and as Mohr circles in direct shear space. For
direct shear data, test data is only plotted as points in direct shear
space."

- Triaxial: puntos (símbolo y color del estado) en σ1–σ3 y semicírculos
  de Mohr (centro (σ1+σ3)/2, radio (σ1−σ3)/2) en τ–σn.
- Direct shear: puntos solo en τ–σn.
- Convenciones OGR de estilo: pico relleno, residual hueco (sus
  círculos discontinuos); los puntos con *Exclude* se dibujan atenuados
  (su efecto sobre el ajuste es de la spec 014).
- Rutas: polilínea en σ1–σ3. Uniaxial → σ3 = 0 (lateral libre);
  triaxial convencional → tensión lateral constante = Initial Effective
  Lateral Stress mientras SigmaZZ (tensión axial) varía; σ1/σ3 = mayor/
  menor de axial y lateral (la extensión los intercambia). Biaxial,
  Simple Shear y General necesitan componentes que la tabla no tiene:
  se guardan pero no se dibujan (el diálogo lo indica).
- Se dibujan los datos de todos los materiales visibles (casilla del
  material) con casilla propia por estado/ruta en el árbol. Leyenda con
  "Material: Estado" si hay varios materiales. El export CSV de la
  gráfica (spec 016) añade columnas de puntos y rutas.

## GUI

- Árbol de la 011: hijos por material (estados y rutas, con casilla de
  visibilidad y color). Doble clic en un hijo abre su diálogo; menú
  contextual Editar/Borrar. En el material: *Define Failure States…* y
  *Define Stress Paths…*; menús de barra **Failure States** y **Stress
  Paths** (como RSData).
- Diálogos (`gui/states_dialog.py`) sobre copias: OK aplica, Cancel
  descarta. Columnas de tensión en la unidad de visualización (17);
  pegar/importar leen en esa unidad; almacenamiento en kPa. Una celda no
  numérica impide cambiar de elemento y aceptar (aviso "row N").
- Tema: indicadores de casilla también en tablas (la hoja de estilo
  ocultaba la casilla marcada de *Exclude*).

## Pendiente / fuera de esta spec (no inventar)

- **Pestaña Stress Path Graphs** de RSData (Axial Stress–Axial Strain,
  Volumetric Strain–Axial Strain, q–Deviatoric Strain, q–p): requiere
  las definiciones de deformación volumétrica y desviadora con fuente
  oficial, que no está en `Referencias/Bibliografia` (los manuales
  teóricos de RSData descargados pierden las ecuaciones en texto y no
  las definen). Se aborda con la simulación (spec 013) o al incorporar
  la fuente. Las rutas no se dibujan en τ–σn por la misma razón (falta
  convención con fuente, p. ej. s–t).
- Lista completa de Test Type del diálogo de estados de RSData: solo se
  observó "Triaxial Test"; "Direct Shear Test" viene del Use Lab Data de
  RocData. Strain Type: solo "Lateral" observado.
- Defectos de Initial Effective Lateral Stress (0) y K0 (1,0): elección
  OGR (los valores de RSData no se capturaron). K0 se guarda; no
  interviene en el dibujo.

## Tests

`tests/test_states.py`: parser (Excel, punto y coma con coma decimal,
CSV, espacios, cabeceras), CSV oficial de RocData, round-trip CSV,
geometría del círculo de Mohr, mapeo de rutas (uniaxial, triaxial,
extensión, no dibujables), defectos y validación, plantillas y round-trip
del proyecto con estados/rutas (y ficheros de la 011), y offscreen:
diálogo de estados (pegar en MPa → kPa, pestañas, tipos, celda inválida,
exportar/importar, copia hasta OK), árbol con hijos, capas en ambas
gráficas (pico/excluido/residual, círculos, punto de corte directo),
leyenda, visibilidad por estado y por material, diálogo de rutas (campos
de triaxial, nota de no dibujable), polilínea y columnas de export,
borrar desde el árbol, persistencia y reapertura.

## Segunda iteración (2026-11-23): fuentes encontradas y aplicadas

Fuentes guardadas: ayuda online oficial de RSData
(`Referencias/Ejemplos/RSData_analisis/ayuda_online/`, resumen en
`06_ayuda_online.md`) y `Referencias/Bibliografia/Ensayos/` (índice en
`00_INDICE.md`).

- **Correcciones con la ayuda oficial**: la "Loading Direction" de las
  rutas es **Lateral/Axial** (Compression/Extension era de los Tests); el
  uniaxial tiene **Strain Type Lateral/Volumetric**; defectos σ'h0 = 100
  kPa y K0 = 1 (figura oficial). Columnas: Uniaxial → EpsilonZZ, SigmaZZ,
  EpsilonXX|EpsilonV; Triaxial/Lateral → EpsilonZZ, SigmaXX, EpsilonV
  (figura oficial); Triaxial/Axial → EpsilonZZ, SigmaZZ, EpsilonV
  (provisional). Los tipos de estado de fallo oficiales son Triaxial,
  Simple Shear y General; Direct Shear se mantiene como extensión
  RocData (etiqueta "(RocData)"). Ficheros de la primera versión con
  Compression/Extension cargan como Lateral.
- **Pestaña Stress Path Graphs** (RSData: cuatro gráficas por defecto):
  Axial Stress–Axial Strain, Volumetric Strain–Axial Strain (RSData
  muestra Pore Water Pressure en no drenado; las tablas no traen presión
  de poro), q–Deviatoric Strain y q–p. Definiciones (Machaček 2023,
  "Triaxial test"): p' = (σa+2σr)/3, q = σa−σr, εv = εa+2εr,
  εq = 2(εa−εr)/3; con columna EpsilonV, εr = (εv−εa)/2. Ejes de tensión
  en la unidad de visualización; menú contextual copiar/guardar/CSV.
- **Rutas en τ–σn**: puntos de tensión en la cima de cada círculo de
  Mohr, (½(σ1+σ3), ½(σ1−σ3)) (UTM "Stress Paths and Strength Tests",
  p. 2; Machaček, representación tradicional σm–τ).
- **Interpretación provisional del triaxial** (a verificar, spec 021):
  Axial → varía SigmaZZ con σr = σ'h0; Lateral → varía SigmaXX con
  σa = σ'h0/K0 (K0 = σ'h/σ'v). Biaxial, Simple Shear y General no se
  dibujan. El diálogo lo indica.
- Verificación en la interfaz: prompt para Claude Desktop en
  `Data/Promps/2026_11_23_Prompt_Claude-Desktop_RSData-ORMAS.md`.

## Tercera iteración (2026-11-23): sustituida en parte por la spec 021

La verificación en la interfaz de RSData 1.009 (documento 07) corrigió
el modelo: sin pestañas Peak/Residual (una tabla por estado), tipos de
estado Triaxial / Direct Shear / General, rutas sin "General", Loading
Direction None/Axial/Lateral, columnas por combinación y semántica
numérica. Implementado en la **spec 021**; ver allí las decisiones donde
RSData se comporta de forma dudosa.
