# Plan, tareas y validación 026 — Anomalías de los parámetros

Aprobada por la propietaria el 2026-11-24 («sí, las apruebo»).

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| N = 0,43 (arena de Fraser River) y JCS = 100 MPa (= σci por defecto) en el registro; los proyectos guardados conservan sus valores | Cambiar también los proyectos abiertos: alteraría resultados ya entregados | RF-1, RF-2 |
| `Field.used` (falso mientras nada lo lea) y el formulario lo deshabilita con su motivo; el valor se sigue guardando y copiando | Quitar los campos: rompería ficheros y el contrato del portapapeles (spec 005) | RF-3, RF-10 |
| Power Curve τ = a(σn + d)^b + c + σn·tan i en kPa; formato de proyecto v3 y conversión de *a* al abrir v1/v2 y al importar `.roc` (a_kPa = a_MPa·1000^(1−b)); los ajustes y la calibración, que trabajan en MPa, convierten *a* al rellenar el formulario | Dejar *a* en MPa: sería el único campo del registro en otra unidad | RF-4, RF-5 |
| Compactación-dilatancia por defecto en Softening-Hardening | — | RF-6 |
| Lambda Kappa: se corrige el texto del modelo (`core/simulation.py`) y la ayuda (Λ = (λ − κ)/v, Wood 1990); **la etiqueta se mantiene** «Lambda Kappa» porque la ayuda del campo ya dice qué introducir | Cambiar la etiqueta: rompía la paridad del nombre con el programa de referencia sin ganar nada sobre el tooltip | RF-7 |
| `ElasticModel` para «Elastic» en Mohr-Coulomb y Hoek-Brown | — | RF-8 |
| **RF-9 se aplaza**: la opción «mb, s, a» de *Define by* abre un camino de cálculo nuevo (sin GSI no hay Erm de Hoek-Diederichs, y el núcleo, el informe, el portapapeles y la simulación calculan mb, s, a desde GSI). Hasta su spec, *Define by* queda como campo no usado (deshabilitado con su motivo) | Hacerlo dentro de esta spec: tocaba ocho módulos y dejaba Erm sin definir | RF-9 |

## Tareas

- [x] **T1** Tests (`tests/test_spec_026.py`) — todos
- [x] **T2** Valores por defecto (N, JCS, tipo de dilatancia) — RF-1, RF-2, RF-6
- [x] **T3** `Field.used`, campos no usados deshabilitados, test de lectura — RF-3, RF-10
- [x] **T4** Power Curve con c e i, en kPa; conversión de *a* (formato v3, `.roc`, ajuste, calibración) — RF-4, RF-5
- [x] **T5** Texto de Lambda Kappa — RF-7
- [x] **T6** Material elástico — RF-8
- [x] **T7** Tests existentes adaptados (fórmula de Power Curve en kPa, calibración, formato v3, captura de JCS, fixture de Softening-Hardening con el potencial explícito)
- [x] **T8** Validación

## Validación (2026-11-24)

Suite entera: **273 tests, 0 fallos**, salida 0.

| RF | Test (`tests/test_spec_026.py`) | Resultado |
|---|---|---|
| RF-1, RF-2, RF-6 | `test_defaults_inside_published_ranges` | verde |
| RF-3 | `test_unused_fields_are_disabled_with_their_reason` | verde |
| RF-4 | `test_power_curve_in_kpa_with_c_and_waviness` | verde (fórmula); **falta** el contraste con valores del programa de referencia: no se tienen |
| RF-5 | `test_power_curve_a_is_converted_from_old_files_and_fits`, `test_calibration.py`, `test_criteria.py` | verde |
| RF-7 | texto del modelo y ayuda | hecho; etiqueta sin cambiar (ver decisiones) |
| RF-8 | `test_elastic_material_never_yields` | verde |
| RF-9 | — | **aplazado** (ver decisiones) |
| RF-10 | `test_every_field_is_used_or_marked_unused` | verde |

## Qué se encontró

- Campos que siguen sin usar, ya deshabilitados con su motivo: los
  residuales y la relación de dilatancia de Power Curve (no hay cálculo
  residual de criterios en el plano σn–τ), *Cap Softening*, módulo del
  fluido y condición de consolidación inicial de NorSand, dilatancia y
  resistencia residual de Barton-Bandis, *Tensile Cutoff Type* y *Define
  by* de Hoek-Brown generalizado.
- La migración de proyectos lee `residual_a` y `residual_b`: el test de
  RF-10 cuenta solo las lecturas de los cálculos (excluye el registro y los
  lectores de ficheros).
