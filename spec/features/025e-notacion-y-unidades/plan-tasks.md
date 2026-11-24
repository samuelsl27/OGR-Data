# Plan y tareas 025e — Notación, decimales y unidades

Aprobada al pedir la propietaria «continúa» (2026-11-24), con su criterio
de decimales: «dependiendo del parámetro, mira las capturas del programa de referencia;
hay parámetros que se muestran con 4–6 y se copian todos los decimales».

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| **Formato único** `core/numbers.format_number`: hasta 6 cifras significativas sin ceros de relleno; ángulos con 4 decimales; notación científica solo por debajo de 1e-4 (la *s* de un macizo muy malo) y por encima de 1e9; \|valor\| < 1e-12 se muestra 0 (ruido de un ajuste) | Decimales fijos por parámetro: una tabla que se desactualiza con cada criterio nuevo. Lo del programa de referencia (`100000`, `40.5662`, `0.000233284`) es justo esto | RF-2, RF-3 |
| La tabla de la spec queda así: adimensionales (mb, s, a, mi, D, GSI, ν), tensiones y módulos → 6 cifras significativas; ángulos → 4 decimales | — | RF-3 |
| `NumberSpinBox` (subclase de `QDoubleSpinBox`) en todos los campos: muestra con el formato y guarda 10 decimales; `setDecimals` ya no recorta | Cambiar `setDecimals` en cada sitio: seguiría rellenando con ceros | RF-2, RF-5 |
| `core/numbers.symbols`: σ₁, σ₃, σ₃max, σn, σci, σcm, σt, σc, φ, φb, φr, τ y «°» **solo al mostrar** (ejes, resultados, muestreador, etiquetas, informe); las claves de traducción, las columnas CSV y los ficheros siguen en ASCII | Cambiar las claves de traducción: el CSV y los ficheros cambiarían con la pantalla (spec 024) | RF-1 |
| `units.stress_text` usa el formato por defecto (los decimales fijos siguen disponibles) y el informe también (`report._number`) | — | RF-3 |
| Módulos: **siempre en la unidad elegida** (Erm = `3686231 kPa`), sin cambio automático a MPa/GPa | Cambiar de unidad solo: la columna de resultados mezclaría unidades; el número entero ya no sale en notación científica | RF-6 |
| El diálogo de ajuste trabaja en la unidad de la ventana (cabeceras, σci fijo, resultado); sin ventana, MPa como antes | — | RF-7 |
| Calibración y ajuste muestran c, φ, φb, JRC… en vez de `cohesion_mpa`, `friction_deg`, `phi_b` | — | RF-8 |
| **RF-9 no se aplica**: los nombres de criterio siguen los del programa de referencia («Mohr Coulomb», «Generalized Hoek Brown»), por la decisión de la propietaria en 025c de conservar los nombres del programa de referencia | Escribir «Mohr-Coulomb»: contradice esa decisión | RF-9 |

## Tareas

- [x] **T1** `core/numbers.py` (`format_number`, `symbols`) con tests contra las capturas del programa de referencia — RF-2, RF-3
- [x] **T2** `stress_text` e informe con el formato; «°» en el informe — RF-3
- [x] **T3** `NumberSpinBox` en todos los campos — RF-2, RF-5
- [x] **T4** Símbolos en ejes, resultados, muestreador, etiquetas e informe — RF-1
- [x] **T5** Ajuste en la unidad de la ventana — RF-7
- [x] **T6** Calibración y ajuste sin claves internas — RF-8
- [x] **T7** Tests existentes adaptados al formato nuevo (unidades, muestreador, informe, estimación, 025b)
- [x] **T8** Validación

## Validación (2026-11-24)

Suite entera: **258 tests, 0 fallos**, salida 0.

| RF | Test (`tests/test_ux_025e.py`) | Resultado |
|---|---|---|
| RF-1 | `test_symbols_on_screen_only`, `test_screen_uses_symbols_and_the_format` | verde |
| RF-2 | `test_fields_show_no_padding_and_keep_what_is_typed` | verde |
| RF-3 | `test_format_matches_the_reference_values`, `test_stress_text_uses_the_format` | verde |
| RF-4 | `test_copy_keeps_every_decimal` | verde |
| RF-5 | `test_fields_show_no_padding_and_keep_what_is_typed` | verde |
| RF-6 | `test_screen_uses_symbols_and_the_format` (Erm sin notación científica) | verde |
| RF-7 | `test_fit_dialog_works_in_the_window_unit` | verde |
| RF-8 | `test_calibration_result_shows_no_internal_keys`, `test_fit_dialog_works_in_the_window_unit` | verde |
| RF-9 | no aplica (decisión de 025c) | — |

Capturas de la ventana en [`capturas/`](capturas/) (inglés y español).

## Qué se encontró

- **El portapapeles perdía decimales**: los campos guardaban 6 decimales,
  así que una cohesión escrita `10.123456789` se copiaba a Slip2D como
  `10.123457`. Lo destapó el test de RF-4 antes del cambio; con 10
  decimales debajo se copia el valor escrito.
- Con `.6g`, el informe escribía Erm como `3.68623e+06 kPa` y una cohesión
  nula de un ajuste como `7.48901e-13 kPa`; ahora `3686231 kPa` y `0 kPa`.
- Los nombres de criterio del programa de referencia van sin guion: RF-9 chocaba con la
  decisión de 025c y no se aplica.
- El criterio de finalización pedía un test **estático** de que no queda
  `sigma1`/`deg` visible; no se escribió: los textos se convierten al
  mostrarse (las claves siguen en ASCII a propósito), así que un test sobre
  el código no lo vería. Se comprueba en la ventana (ejes, resultados,
  muestreador) con `test_screen_uses_symbols_and_the_format`.
- Pendiente fuera de esta spec: los encabezados de las tablas de puntos de
  los diálogos de estados y trayectorias siguen como el programa de referencia («Sigma3»,
  «Sigma1»), porque son también los nombres de columna que se importan y
  exportan; cambiarlos pide separar la cabecera visible del nombre de columna.
