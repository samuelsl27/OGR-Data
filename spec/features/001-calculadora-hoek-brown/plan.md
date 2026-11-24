# Plan 001 — Calculadora Hoek-Brown

## Decisiones

- **Fórmulas**: Hoek-Brown 2002 tal cual el artículo (mb, s, a; sigt, sigc,
  sigcm). Validación numérica contra ORMAS V2.0 (ver spec.md).
- **MC equivalente**: ajuste por mínimos cuadrados de σ1 = k·σ3 + n sobre N
  puntos en [0, σ3max]; φ = asin((k−1)/(k+1)), c = n/(2√k). Equivalente al
  "best-fit MC envelope over a stress range" del programa de referencia antiguo. Se verifica contra
  ORMAS; si ORMAS usa la forma cerrada de la Ref. 1 §4, se adopta esa para
  coincidencia exacta.
- **Envolvente τ–σn**: construcción tangente a los círculos de Mohr por
  puntos: sinφi = (dσ1/dσ3 − 1)/(dσ1/dσ3 + 1) con dσ1/dσ3 analítico de
  GHB; σn = centro − R·sinφi, τ = R·cosφi.
- **Unidades internas**: MPa (como ORMAS); la UI muestra MPa con cambio a
  kPa previsto (spec posterior).
- **UI**: PySide6; barra lateral con QDoubleSpinBox/QComboBox; dos canvas
  matplotlib (`FigureCanvasQTAgg`) en un splitter; recálculo por señales.

## Estructura

```
ogr_data/
  core/
    hoek_brown.py    # dataclass HbInput, HbResult, compute(), equivalent_mc(), rock_mass_modulus()
    envelope.py      # puntos de envolvente σ1–σ3 y τ–σn
  gui/
    main_window.py   # ventana principal
    plots.py         # widgets matplotlib
tests/
  test_hoek_brown.py # validación ORMAS
  test_envelope.py
  _runner.py         # runner propio (sin pytest, sin ogr-core)
```

## Riesgos

- Diferencias de redondeo con ORMAS → tolerancias explícitas en tests y
  nota en la spec.
- matplotlib lento al arrastre → recalcular envolvente con 200 puntos
  (igual que el programa de referencia, Failure Range por defecto).

## Correcciones (2026-11-23)

Al analizar el código de ORMAS (`Referencias/Ejemplos/ORMAS_analisis/`):

- **MC equivalente**: la cohesión se calcula con la eq. 13 de Hoek 2002
  (σ3n = σ3max/σci). La forma "anclada en σcm" usada hasta entonces solo
  es válida para σ3max = σci/4 —el caso por defecto de ORMAS con el que
  se validó—, y fallaba en cualquier otro rango (túnel, talud, Custom
  distinto). Tests: Custom, Túnel y Talud de ORMAS (c y φ) y la
  identidad σcm = 2c cosφ/(1−sinφ) solo en σci/4.
- **Módulo "Simplified Hoek & Diederichs (2006)"**: 100000·(1−D/2)/
  (1+e^((75+25D−GSI)/11)) (Practical Rock Engineering 2023, eq. 20); se
  usaba por error la forma generalizada (0,02 y 60+15D).
- **Módulo Hoek 2002 (eq. 11)**: devuelve MPa (antes GPa sin convertir) y
  para σci > 100 MPa el término √(σci/100) vale 1 (hoja de cálculo de la
  masa de roca de Practical Rock Engineering 2023).
