# Tareas 028 — Hoek-Brown generalizado definido por mb, s y a

En orden de dependencia. Cada tarea ≤ 30 min, tests primero, y se marca
`[x]` al terminarla con la suite en verde. Una tarea cada vez.

## Contratos (antes del código)

- [ ] **T1** Notas de formato en las specs 007/011 (`.ogrdata`: claves
  nuevas del GHB, ficheros viejos en «GSI») y 005 (portapapeles: el
  receptor usa las mb, s, a de `computed`) — RF-9, RF-10
  - Hecho cuando: las tres specs tienen su nota con la fecha y la cita de
    la spec 028, y `test_spec_027` sigue en verde.

## Núcleo (sin Qt)

- [ ] **T2** Fuente única de mb, s y a, solo con el modo «GSI»: función
  del núcleo que da (mb, s, a) de pico y residual desde los parámetros;
  `material_results`, `criteria_envelopes`, `report` y `simulation` la
  llaman — RF-5, RF-7, RF-9
  - Hecho cuando: un test nuevo comprueba que los cinco caminos dan las
    mismas mb, s y a para el ejemplo de Hoek et al. (2002) § 7, y la suite
    actual pasa sin tocar ningún test (sin cambio de comportamiento).
- [ ] **T3** Límites de mb, s y a con su motivo — RF-8
  - Hecho cuando: `test_limits_*` en verde: dentro y fuera de cada límite,
    con a(GSI=0) = 1/2 + (1 − e^(−20/3))/6 exacto, y un mensaje por fallo.
- [ ] **T4** Campos nuevos en el registro (`mb`, `s`, `a`, `erm`,
  `*_residual`), «Define by» con «GSI» y «mb, s, a», `used=True`, y los
  campos activos por modo con el motivo de los inactivos — RF-1, RF-2,
  RF-3, RF-10
  - Hecho cuando: `test_fields_by_mode` en verde, y un `.ogrdata` guardado
    antes de esta spec abre en «GSI» con los mismos resultados.
- [ ] **T5** Modo «mb, s, a» en la fuente única y en `compute()` (con Erm
  dado o ausente); `ghb_computed` sin `erm_mpa` si no hay Erm — RF-5,
  RF-6, RF-7
  - Hecho cuando: en verde los tests de soluciones cerradas (ecs. 6, 7 y
    17, a ≠ 0,5, 1e-9), de Jaeger/FHWA 1989 (σ3 ≥ 0,35 MPa, 10 %), de
    coincidencia con el camino por GSI (§ 7, 1e-9) y de residuales directos.
- [ ] **T6** GSI equivalente: despeje de las ecs. 3–5 con sus motivos de
  rechazo, también para los residuales — RF-6b, RF-6c
  - Hecho cuando: § 7 (GSI 45, mi 10, D 0) y un caso con D = 0,7 vuelven a
    sus valores (1e-9); a = 0,5 con s < 1, s = 0, D fuera de 0–1 y GSI < 1
    se rechazan con motivo.
- [ ] **T7** Mismos números en todas las salidas en modo «mb, s, a»:
  informe, portapapeles, simulación (pico y residual), σ3max por
  aplicación — RF-9
  - Hecho cuando: `test_same_numbers_everywhere` en verde, con Erm dado y
    sin dar.

## API y MCP

- [ ] **T8** API: `material_set`/`material_add` validan los límites;
  `material_get` dice el modo y los campos activos; operación
  `material_equivalent_gsi` y su herramienta MCP — RF-6b, RF-8, RF-9
  - Hecho cuando: los tests de la API en verde (límite incumplido →
    `InvalidArgument` con el motivo; la operación nueva devuelve GSI, mi y
    D y pasa a «GSI»), y la herramienta aparece en el servidor MCP.

## Ventana

- [ ] **T9** Formulario por modo: habilitar y deshabilitar con el motivo en
  el tooltip; en «GSI», mb, s y a muestran los calculados sin pisar los
  manuales — RF-2, RF-3
  - Hecho cuando: test offscreen en EN y ES: en cada modo, los campos
    habilitados y sus valores son los del núcleo.
- [ ] **T10** Cambio de modo: RF-4 la primera vez (la envolvente no se
  mueve), RF-11 después (ida y vuelta conserva los manuales); un paso de
  deshacer cada cambio — RF-4, RF-11
  - Hecho cuando: test offscreen en verde con la envolvente comparada
    punto a punto y Ctrl+Z devolviendo el estado anterior.
- [ ] **T11** Erm a mano: «sin dar» en el campo, «sin calcular» con su
  motivo en los resultados, botón «Erm» de la rigidez deshabilitado sin
  Erm — RF-6
  - Hecho cuando: test offscreen en verde, más el de la regla 7 (mb, s, a
    y Erm mueven el número en «mb, s, a» y no en «GSI»).
- [ ] **T12** Botón «Deducir GSI equivalente» junto a «Define by» y en el
  menú Materiales; mensaje junto al botón si no se puede; un paso de
  deshacer — RF-6b, RF-6c
  - Hecho cuando: test offscreen en verde (deduce, pasa a «GSI», la
    envolvente no cambia, Ctrl+Z lo deshace; caso rechazado con mensaje), y
    el test de la regla 3 (acción en un menú) sigue en verde.
- [ ] **T13** Límites en la ventana: mensaje junto al campo tras editarlo,
  sin envolvente ni resultados — RF-8
  - Hecho cuando: test offscreen en verde en EN y ES.

## Textos y ayuda

- [ ] **T14** Ayuda de cada campo nuevo (definición, unidad, fuente: Hoek
  et al. 2002) y textos en español de T9–T13 — RF-1, RF-2, RF-6
  - Hecho cuando: `test_i18n` y los tests de ayuda de la spec 025f en
    verde con los campos nuevos.

## Cierre

- [ ] **T15** Validación final — todos los RF
  - Hecho cuando: cada RF tiene su test en verde (tabla RF → test →
    resultado), la lista UX de la spec está marcada, capturas en EN/ES y
    claro/oscuro de los dos modos, la suite entera pasa y el roadmap marca
    la 028 como hecha.

## Cobertura

RF-1 (T4, T14) · RF-2 (T4, T9) · RF-3 (T4, T9) · RF-4 (T10) · RF-5 (T2,
T5) · RF-6 (T5, T11) · RF-6b (T6, T8, T12) · RF-6c (T6, T12) · RF-7 (T2,
T5) · RF-8 (T3, T8, T13) · RF-9 (T1, T2, T7, T8) · RF-10 (T1, T4) · RF-11
(T10). Ningún RF queda sin tarea.
