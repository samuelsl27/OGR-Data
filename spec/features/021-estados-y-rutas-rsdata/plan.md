# Plan 021 — Estados y rutas fieles a RSData

- `core/states.py`
  - `FailureState`: `points` (TestPoint x, y, exclude) para Triaxial y
    Direct Shear; `tensors` (6 componentes) para General.
    `principal_points()` (excluidos fuera; General → autovalores del
    tensor simétrico 3×3) y `shear_points()` (Direct Shear).
    `failure_states_from_dicts()` migra `peak`/`residual` de la 012.
  - `StressPath`: `steps` como filas genéricas cuyas columnas da
    `columns()` según tipo/seepage/dirección/strain type; `stress_columns()`
    para unidades; `drawable` = uniaxial o triaxial/Axial;
    `invariants()` con radial 0 (uniaxial) o σ'h0 (triaxial), εr desde
    EpsilonXX o EpsilonV, y en no drenado tensiones efectivas con u y
    εv = 0; q = |σa − σr|.
- `gui/states_dialog.py`: `PointTable.reconfigure()` (cambia columnas
  conservando valores por posición); diálogo de estados con una tabla
  que se reconfigura por tipo; diálogo de rutas que muestra/oculta filas
  del formulario (`QFormLayout.setRowVisible`) y reconfigura columnas por
  combinación, con nota de lo no dibujado.
- `gui/main_window.py`: dibujo sin pico/residual; excluidos fuera; estado
  General como puntos principales + círculos de Mohr.
- Tests (`tests/test_states.py`) con los números del documento 07.
