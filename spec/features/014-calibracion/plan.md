# Plan 014 — Calibración

Diálogo *Calibration* del programa de referencia (captura 33; opciones verificadas en
el documento `07_estados_y_rutas_verificado.md` del análisis privado del programa de referencia §4) sobre el ajuste de
la spec 006, los materiales de la 011 y los estados de la 012/021.

## Núcleo (`core/calibration.py`, sin Qt)

- `collect_points(states)`: puntos no excluidos de los estados elegidos;
  Triaxial y General → (σ3, σ1) (General por autovalores), Direct Shear
  → (σn, τ); mezclar triaxial y corte directo es un error.
- Strength type (combo del programa de referencia): **Mohr Coulomb** (triaxial o corte
  directo), **Generalized Hoek Brown** (triaxial), **Power Curve** y
  **Barton Bandis** (corte directo; φb fijo).
- Failure Data Type: **Lab Data** (GHB = roca intacta: ajusta σci y mi;
  material con GSI = 100, D = 0 → mb = mi, s = 1, a = 0,5) y **Rock Mass
  Data** (solo GHB, σci y D fijos como el "Use Rock Mass Data" del programa de referencia antiguo). El programa de referencia antiguo ajusta ahí mb, s, a; el formulario GHB de OGR se
  define por GSI/mi/D (el modo "mb, s, a" del programa de referencia no está), así que se
  ajustan **GSI y mi** con el mismo modelo GHB 2002.
- Algorithm: **Linear Regression** (formas cerradas de la 006: MC y HB
  intacto; con error relativo solo MC), **Levenberg-Marquardt** (por
  defecto, como el programa de referencia antiguo) y **Simplex** (Nelder-Mead, el programa de referencia antiguo). El programa de referencia actual
  ofrece además "None" (sin significado claro): no se replica.
- Error Summation: **Vertical** (residuos en σ1 o τ, como el programa de referencia antiguo).
  Error Type: **Absolute** / **Relative** (residuo / valor observado).
- Límites físicos (c ≥ 0, 0 < φ < 90°, resistencias > 0, 1 ≤ GSI ≤ 100,
  0 ≤ JRC ≤ 20): si la solución LM libre los viola se rehace con un
  solver acotado (trust-region) y el resultado lo dice.
- Resultado: criterio y parámetros del registro (kPa) para un **material
  nuevo**; nº de puntos, suma de cuadrados y RMS.

## Contraste con el programa de referencia (caso de verificación, 4 puntos)

- Con el punto (300; 1500) excluido: c = 10,4788 kPa, φ = 34,9894° con
  los tres algoritmos = el programa de referencia ✓.
- Con los 4 puntos: el óptimo libre es c = −6,97 kPa (no físico). OGR da
  el óptimo acotado c = 0, φ = 40,0902°; el programa de referencia muestra c = 0,000233,
  φ = 40,5662°, que ninguna formulación probada reproduce (principal o
  cortante, absoluta o relativa, acotada o no): probablemente un punto
  de parada de su LM. Se documenta, no se imita.
- Linear Regression con los 4 puntos: no hay recta MC válida (ordenada
  negativa) → OGR da un error claro. Explica (hipótesis) por qué en el programa de referencia esa calibración dejó el modelo igual al de partida.

## GUI

- `gui/calibration_dialog.py`: Material Model (origen) · New Model
  Settings (nombre único "Calibrated Material", Strength type con GHB por
  defecto como el programa de referencia) · Curve Fit Analysis · Failure States (lista con
  casillas de todos los estados del proyecto; marcados los del material
  actual) · Failure Data Type con σci/D (macizo) y φb (Barton-Bandis)
  visibles solo cuando aplican. Vista previa en vivo; OK deshabilitado si
  el ajuste no es válido (mensaje en rojo).
- Menú **Calibrate → Calibrate…** (como el programa de referencia). OK añade el material y
  lo selecciona; el material de origen no cambia.

## Pendiente

- **Prediction Interval** (casilla + %): semántica en el programa de referencia no
  verificada.
- Material calibrado de solo lectura (el programa de referencia): en OGR es editable.
- GHB "Define by mb, s, a" para guardar el ajuste de macizo del programa de referencia antiguo.
