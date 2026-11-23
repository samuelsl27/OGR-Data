# Plan 014 — Calibración

Diálogo *Calibration* de RSData (captura 33; opciones verificadas en
`RSData_analisis/07_estados_y_rutas_verificado.md` §4) sobre el ajuste de
la spec 006, los materiales de la 011 y los estados de la 012/021.

## Núcleo (`core/calibration.py`, sin Qt)

- `collect_points(states)`: puntos no excluidos de los estados elegidos;
  Triaxial y General → (σ3, σ1) (General por autovalores), Direct Shear
  → (σn, τ); mezclar triaxial y corte directo es un error.
- Strength type (combo de RSData): **Mohr Coulomb** (triaxial o corte
  directo), **Generalized Hoek Brown** (triaxial), **Power Curve** y
  **Barton Bandis** (corte directo; φb fijo).
- Failure Data Type: **Lab Data** (GHB = roca intacta: ajusta σci y mi;
  material con GSI = 100, D = 0 → mb = mi, s = 1, a = 0,5) y **Rock Mass
  Data** (solo GHB, σci y D fijos como el "Use Rock Mass Data" de
  RocData). RocData ajusta ahí mb, s, a; el formulario GHB de OGR se
  define por GSI/mi/D (el modo "mb, s, a" de RSData no está), así que se
  ajustan **GSI y mi** con el mismo modelo GHB 2002.
- Algorithm: **Linear Regression** (formas cerradas de la 006: MC y HB
  intacto; con error relativo solo MC), **Levenberg-Marquardt** (por
  defecto, como RocData) y **Simplex** (Nelder-Mead, RocData). RSData
  ofrece además "None" (sin significado claro): no se replica.
- Error Summation: **Vertical** (residuos en σ1 o τ, manual de RocData).
  Error Type: **Absolute** / **Relative** (residuo / valor observado).
- Límites físicos (c ≥ 0, 0 < φ < 90°, resistencias > 0, 1 ≤ GSI ≤ 100,
  0 ≤ JRC ≤ 20): si la solución LM libre los viola se rehace con un
  solver acotado (trust-region) y el resultado lo dice.
- Resultado: criterio y parámetros del registro (kPa) para un **material
  nuevo**; nº de puntos, suma de cuadrados y RMS.

## Contraste con RSData (caso de verificación, 4 puntos)

- Con el punto (300; 1500) excluido: c = 10,4788 kPa, φ = 34,9894° con
  los tres algoritmos = RSData ✓.
- Con los 4 puntos: el óptimo libre es c = −6,97 kPa (no físico). OGR da
  el óptimo acotado c = 0, φ = 40,0902°; RSData muestra c = 0,000233,
  φ = 40,5662°, que ninguna formulación probada reproduce (principal o
  cortante, absoluta o relativa, acotada o no): probablemente un punto
  de parada de su LM. Se documenta, no se imita.
- Linear Regression con los 4 puntos: no hay recta MC válida (ordenada
  negativa) → OGR da un error claro. Explica (hipótesis) por qué en
  RSData esa calibración dejó el modelo igual al de partida.

## GUI

- `gui/calibration_dialog.py`: Material Model (origen) · New Model
  Settings (nombre único "Calibrated Material", Strength type con GHB por
  defecto como RSData) · Curve Fit Analysis · Failure States (lista con
  casillas de todos los estados del proyecto; marcados los del material
  actual) · Failure Data Type con σci/D (macizo) y φb (Barton-Bandis)
  visibles solo cuando aplican. Vista previa en vivo; OK deshabilitado si
  el ajuste no es válido (mensaje en rojo).
- Menú **Calibrate → Calibrate…** (como RSData). OK añade el material y
  lo selecciona; el material de origen no cambia.

## Pendiente

- **Prediction Interval** (casilla + %): semántica en RSData no
  verificada.
- Material calibrado de solo lectura (RSData): en OGR es editable.
- GHB "Define by mb, s, a" para guardar el ajuste de macizo de RocData.
