# Plan 006 — Ajuste a datos de ensayo

## Núcleo (`core/fitting.py`)

- `FitResult(parameters, residuals, method, criterion_key, data_kind)`.
- `fit(criterion_key, data_kind, x, y, method, fixed=None) -> FitResult`
  despachando:
  - `hb_intact` triaxial: lineal y = (σ1−σ3)² = mi·σci·σ3 + σci²
    (Hoek ch.11); LM/Simplex sobre el modelo directo.
  - `mohr_coulomb` triaxial: σ1 = k σ3 + n → φ = asin((k−1)/(k+1)),
    c = n/(2√k); directo: τ = c + σn tanφ.
  - `generalized_hoek_brown` triaxial: σ1 = σ3 + σci(mb σ3/σci + s)^a,
    σci y D fijos; LM/Simplex.
  - `barton_bandis` directo: τ = σn tan(φb + JRC log10(JCS/σn)); φb fijo.
  - `power_curve` directo: τ = a(σ+d)^b.
- Residuos: suma de cuadrados verticales.

Métodos: "linear" (solo donde existe cerrada), "levenberg_marquardt"
(scipy least_squares, method="lm"), "simplex" (Nelder-Mead sobre la SSR).

## GUI (`gui/fit_dialog.py`)

Diálogo: criterio + tipo de datos (filtrados por compatibilidad), método,
tabla editable de puntos con pegado desde Excel (portapapeles tabulado),
botón Fit → parámetros y residuals, botón "Apply" que rellena el
formulario del criterio activo de la ventana principal.

## Riesgos

- Convergencia de LM/Simplex a mínimos locales con datos reales ruidosos:
  mitigado con valores iniciales por defecto razonables y multiples
  semillas solo si los tests lo exigen (no por ahora).
