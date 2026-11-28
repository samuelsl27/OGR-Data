# Plan 028 — Hoek-Brown generalizado definido por mb, s y a

Sin código. Cada apartado dice qué RF cubre. Aprobado el 2026-11-28.

## Situación de partida

Hoy cinco sitios calculan mb, s y a desde GSI, mi y D, cada uno por su
cuenta: `core/material_results.py` (`hb_terms`, `ghb_computed`,
`rock_mass_strength_mpa`), `core/criteria_envelopes.py`, `core/report.py`,
`core/simulation.py` (pico y residual) y, a través de `mr`, la ventana.
`HbInput` exige GSI y `compute()` deriva siempre las constantes de él.
«Define by» es un `enum` con una sola opción y `used=False` (spec 026).

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| **Una sola fuente de mb, s y a**: una función del núcleo devuelve (mb, s, a) de pico y residual a partir de los parámetros del material, según «Define by». Los cinco sitios de arriba la llaman. | Guardar siempre mb, s y a calculados en los parámetros y sincronizarlos: dos verdades que acaban diciendo cosas distintas (regla de capas de `AGENTS.md`) | RF-5, RF-7, RF-9 |
| `compute()` acepta las constantes ya resueltas, y un Erm dado o ausente; las fórmulas de σt, σc, σcm y el MC equivalente no cambian (ya reciben mb, s, a) | Un `HbInput` paralelo sin GSI: duplica validación y llamadas | RF-5, RF-6 |
| **Límites en el núcleo**: una función comprueba mb > 0, 0 ≤ s ≤ 1 y 0,5 ≤ a ≤ a(GSI=0) y devuelve el motivo de cada fallo. La ventana lo muestra junto al campo, la API lo devuelve como `InvalidArgument`, y el cálculo no se hace | Validar solo en los spin boxes (rango): la API y el portapapeles se lo saltarían | RF-8 |
| **Qué campos manda cada modo** lo dice el núcleo (campos activos de «GSI» y de «mb, s, a», con el motivo de los inactivos); la ventana lo pregunta para habilitar y poner el tooltip | Decidirlo en `main_window.py`: la API no lo sabría | RF-2, RF-3 |
| Campos nuevos en el registro del GHB: `mb`, `s`, `a`, `erm` (kPa) y `mb_residual`, `s_residual`, `a_residual`; «Define by» con las opciones «GSI» y «mb, s, a», y `used=True` | Un diálogo aparte para mb, s, a: esconde lo frecuente (U10) | RF-1, RF-2, RF-6, RF-7 |
| **Erm a mano**: el campo `erm` con 0 = «no dado» (se muestra «sin dar» con `specialValueText`). En modo «mb, s, a», Erm es ese valor o «sin calcular» con su motivo; el botón «Erm» de la rigidez se deshabilita sin él | Un interruptor «dar Erm» más el campo: dos controles para una cosa | RF-6 |
| **Deducir GSI equivalente**: una función del núcleo despeja GSI de a (ec. 5), D de s y GSI (ec. 4) y mi de mb, GSI y D (ec. 3); devuelve el motivo si no se puede (a = 0,5, s = 0, D fuera de 0–1, GSI < 1). Hace lo mismo con los residuales si no son iguales al pico. El botón va junto a «Define by» y en el menú Materiales | Ajustar GSI, mi y D por mínimos cuadrados: innecesario, el despeje es exacto | RF-6b, RF-6c |
| **Valores manuales en GSI**: los spin boxes de mb, s y a muestran deshabilitados los valores calculados; los manuales siguen en los parámetros del material, y la lectura de la ventana no los pisa | Mostrar los manuales deshabilitados: contradice RF-3 | RF-3, RF-11 |
| Cambio de modo, deducción y edición pasan por el historial de deshacer (spec 023) como un solo paso cada uno | Confirmar con un diálogo: U5 lo prohíbe | RF-6b, RF-11 |

## Duda resuelta (regla 6)

RF-4 y RF-11 chocaban la segunda vez que se pasa a «mb, s, a». Resuelto
con la propietaria el 2026-11-28: **RF-4 solo la primera vez**, cuando el
material no tiene valores manuales (mb = 0 por defecto, que no es válido);
después manda RF-11. La spec lo recoge.

## Capas y archivos

- `ogr_data/core/hoek_brown.py`: constantes desde parámetros según el modo,
  límites, GSI equivalente y `compute()` con constantes y Erm opcional
  (RF-5, RF-6, RF-6b, RF-6c, RF-8).
- `ogr_data/core/models.py`: los campos nuevos, «Define by» con dos
  opciones, y los campos activos por modo (RF-1, RF-2, RF-3, RF-7).
- `ogr_data/core/material_results.py`, `criteria_envelopes.py`,
  `report.py`, `simulation.py`: pasan a la fuente única (RF-5, RF-7, RF-9).
  `ghb_computed` deja fuera `erm_mpa` cuando no hay Erm.
- `ogr_data/api/ops/materials.py` y `_common.py`: `material_set`/`add`
  validan los límites; `material_get` dice el modo y los campos activos;
  operación nueva `material_equivalent_gsi` (RF-6b, RF-8, RF-9).
- `ogr_data/mcp_server/`: la herramienta de la operación nueva.
- `ogr_data/gui/main_window.py`: habilitar por modo, mostrar los
  calculados en «GSI», RF-4/RF-11 al cambiar de modo, el botón y su menú,
  el mensaje junto al campo (RF-2, RF-3, RF-4, RF-6b, RF-8, RF-11).
- `ogr_data/gui/stiffness_panel.py`: el botón «Erm» sin Erm (RF-6).
- `ogr_data/gui/parameter_tooltip.py` y `core/parameter_help.py`: ayuda de
  mb, s, a, Erm y residuales con su fuente (Hoek et al. 2002) (spec 025f).
- `ogr_data/gui/i18n/es_registry.py`, `es_main.py`: textos nuevos
  («mb, s, a», «Deducir GSI equivalente», motivos, «sin dar», etiquetas).

## Modelo de datos

- `.ogrdata`: solo claves nuevas en `parameters` del material
  (`define_by: "mb, s, a"`, `mb`, `s`, `a`, `erm`, `*_residual`). Un fichero
  viejo no las trae y toma los valores por defecto (`define_by = "GSI"`):
  abre igual (RF-10). Antes del código, una nota en las specs 007/011.
- Portapapeles (spec 005): el contrato no cambia de forma. `parameters`
  lleva las claves nuevas; `computed` sigue llevando mb, s y a, que son
  válidos en los dos modos. Se añade a la spec 005 que un receptor debe
  usar las mb, s y a de `computed`, porque con «mb, s, a» los GSI, mi y D
  de `parameters` no describen el material. Hoy ni OGR Slip2D ni OGR FEM2D
  leen este formato (comprobado en sus fuentes), así que nada se rompe.
- Sin tablas nuevas en `ogr_data/data/`.

## Validación numérica

| Qué | Referencia externa | Tolerancia |
|---|---|---|
| Envolvente con m y s directos (a = 0,5) | Ensayos de Jaeger, FHWA (1989) p. 5.27: σci = 265,5 MPa, m = 0,277, s = 0,0002; 6 ensayos con σ3 ≥ 0,35 MPa | 10 % sobre el σ1 medido (máx. del ajuste publicado: 9,7 %); el ensayo a σ3 = 0 se excluye y se dice |
| σc, σt, σcm con a ≠ 0,5 | Soluciones cerradas, ecs. 6, 7 y 17 de Hoek et al. (2002), escritas en el test | 1e-9 relativo |
| c y φ equivalentes | Ecs. 12 y 13 de Hoek et al. (2002) con las mb, s, a del ejemplo del § 7 | Coincidencia con el camino por GSI (ya validado con ORMAS), 1e-9 |
| GSI equivalente | Inversión exacta de las ecs. 3–5: el ejemplo del § 7 (GSI 45, mi 10, D 0) y un caso con D = 0,7 vuelven a sus valores | 1e-9 |
| Límites | a(GSI=0) = 1/2 + (1 − e^(−20/3))/6 | exacto |

## Estrategia de tests

- **Núcleo y API, sin Qt** (`tests/test_spec_028.py`): los casos de la
  tabla; RF-8 dentro y fuera de cada límite; RF-6c (a = 0,5 con s < 1,
  s = 0, D fuera de rango, GSI < 1); RF-9, los mismos números en
  `computed`, el informe, el portapapeles, la simulación (pico y residual)
  y `material_compute` de la API; RF-10, un `.ogrdata` de la versión
  actual abre en «GSI» con los mismos resultados; Erm ausente fuera de
  `computed`.
- **Ventana (offscreen)**: RF-2 y RF-3, qué campos están habilitados y con
  qué valores en cada modo; RF-4 la envolvente no se mueve al cambiar;
  RF-11 ida y vuelta conserva los manuales; RF-6b el botón y su menú, y
  Ctrl+Z lo deshace; RF-8 el mensaje junto al campo y nada calculado.
- **Regla 7**: un test que demuestra que mb, s, a y Erm mueven el número
  en «mb, s, a», y que no lo mueven en «GSI» (donde están deshabilitados).
- **Idioma y tema**: `test_i18n` cubre los textos; el test de ventana corre
  en EN y ES.

## UX

- **U2**: los campos del modo inactivo, deshabilitados y con su motivo en el tooltip.
- **U5**: cambiar de modo y deducir se deshacen; sin diálogos.
- **U7**: el límite incumplido se dice junto al campo, tras editarlo.
- **U9**: al pasar a «mb, s, a» la primera vez, los valores son los que ya se veían.
- **U11**: ayuda de cada campo nuevo con definición, unidad y fuente.
- **Regla 3**: «Deducir GSI equivalente» también en el menú Materiales.

## Riesgos

- **a cerca de 0,5**: el GSI deducido es muy sensible (a varía poco por
  encima de GSI ≈ 70). Se acepta: el despeje es exacto y devuelve las
  mismas mb, s y a. La ayuda del botón lo dice.
- **Calibración y ajuste** (specs 006 y 014) siguen produciendo materiales por
  GSI (fuera de alcance); un test lo fija.
- **Tamaño**: toca seis módulos del núcleo. Las tareas empiezan por la
  fuente única, sin cambio de comportamiento (la suite actual debe seguir
  en verde) y luego añaden el modo nuevo.
