# Plan 009 — Rango de tensión por aplicación (σ3max túnel/talud)

## Fórmulas (extraídas del paper, §6, eqs. 18-19)

Del PDF `Hoek_CarranzaTorres_Corkum_2002_Hoek-Brown_2002_edition.pdf`:

- **Túneles (eq. 18):** σ'3max = 0,47 · σcm · (σcm / (γ·H))^(−0,94)
- **Taludes (eq. 19):** σ'3max = 0,72 · σcm · (σcm / (γ·H))^(−0,91)

donde σcm es la resistencia global de la masa de roca (eq. 17 del paper,
ya implementada y validada en spec 001), γ el peso unitario (MN/m³) y H
la profundidad (túnel) o altura (talud) en m; γ·H queda en MPa. Marinos &
Hoek 2000 §2.2 confirma el rango 0 < σ3 < σv con σv = profundidad × peso
unitario (se cumple: túnel 0,664 < 1,3 = σv).

## Validación contra ORMAS V2.0 (casos de `RSData_analisis/05_profundizacion.md`)

Material ORMAS por defecto: sigci=30 MPa, GSI=50, mi=10, D=0 → σcm=5,2300 MPa.

- **Túnel** (γ=0,026, H=50 → γH=1,3 MPa): la eq. 18 da **σ3max=0,6643 MPa**
  vs 0,6642 anotado de ORMAS (Δ<0,02 %). Con ese σ3max, la forma cerrada
  del ajuste MC da φ=50,00° (anotado: 49,98°) ✓.
- **Talud** (mismos γ=0,026, H=50; los datos exactos no se anotaron): la
  eq. 19 da **σ3max=1,0610 MPa**, y con él la forma cerrada da
  **φ=46,50°**, exactamente el valor anotado de ORMAS ✓ (γH=1,3 es el
  único que reproduce el φ anotado con el material por defecto).

**Pendiente (no inventar):** los valores de cohesión anotados para
túnel/talud (c=0,3669 / 0,4608) NO son reproducibles: la forma cerrada
(validada en spec 001 contra el caso Custom de ORMAS) daría c≈0,95 / 1,04,
y un ajuste numérico por mínimos cuadrados tampoco los reproduce. El φ sí
cuadra en ambos casos. Conclusión: implementar las eqs. 18-19 tal cual;
el c anotado se deja como discrepancia documentada para consultar al
propietario (posible transcripción o convención no documentada de ORMAS).

## Implementación

- `core/application.py`: `sig3max_tunnel(sigcm_mpa, unit_weight, depth)` y
  `sig3max_slope(sigcm_mpa, unit_weight, height)` con las constantes del
  paper (0,47/−0,94 y 0,72/−0,91) y validación de entrada (>0). Solo
  cálculo, sin Qt.
- `tests/test_application.py`: caso túnel ORMAS (0,5 %), caso talud vía φ
  de la forma cerrada (46,50°), γH en MPa, errores de entrada.
- GUI: combo **Application: Custom | Tunnel | Slope** junto al σ3max.
  Custom = spin manual (comportamiento actual). Tunnel/Slope = peso
  unitario (MN/m³) + profundidad/altura (m); el σ3max se calcula solo
  desde σcm (GHB o HB clásico; para otros criterios el selector vuelve a
  Custom, como ORMAS que solo es GHB) y el ajuste MC se recalcula por el
  pipeline existente. El spin σ3max queda deshabilitado mostrando el valor
  calculado. "General" = σci/4 queda fuera de alcance (spec).
