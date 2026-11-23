# Plan 022 — Estimación sin ensayos

## Fuentes (todas en `Referencias/Bibliografia`)

- **Hoek, Carter & Diederichs (2013)**, *Quantification of the GSI
  chart*, ARMA 13-672 (`General/2013-Quantification-of-the-GSI-Chart.pdf`,
  aportado por el propietario): ecs. 1-6, fig. 5, tablas 1-3. Copyright
  ARMA: uso personal; **las ilustraciones no se copian** → la carta se
  redibuja vectorialmente desde la ec. 1 (es lineal: A = 1,5·JCond89 de
  45 a 0, B = RQD/2 de 0 a 40, GSI = A + B).
- *Practical Rock Engineering 2023*: fig. 9 (D, texto), fig. 13 (tabla
  MR, imagen renderizada p. 110 y transcrita), ecs. 20-22 (Erm, ya en el
  núcleo desde la corrección de la 009).
- Hoek ch. 11 Tablas 2-3 (σci y mi, spec 003) y Hoek & Marinos 2000
  (carta GSI de la 003).

## Implementación

- `core/gsi.py` (sin Qt): ecs. 1-6, JCond89 desde las 5 valoraciones de
  la tabla 1, `chart_gsi(A, B)`, `chart_row(B)`. Sin truncar.
  - Diferencias con RSData documentadas en el JSON: RSData usa 1,95 para
    JCond76 (sustitución exacta 1,5×1,3; el paper publica 2) y una forma
    logarítmica para Jr/Ja que no está en el paper. OGR sigue el paper.
  - Ec. 4: el signo menos del exponente se pierde en el PDF; se usa
    e^(−0,1λ) (con +, RQD > 100).
- Datos con fuente: `gsi_quantified.json`, `modulus_ratio.json` (41
  rocas; valor = punto medio del rango, o el único/abierto impreso),
  `disturbance_factor.json` (8 casos túnel/talud).
- Registro GHB: campo **Ei** (kPa, defecto 12 000 MPa = ORMAS; pick MR)
  y **Erm method** (3 métodos, etiquetas de ORMAS); pick en **D**. El
  núcleo recibe Ei y método (`_ghb_input`, `_modulus_method`).
- GUI `gui/estimation.py`:
  - `GsiDialog`: pestañas *Chart 2000* (selector de la 003), *Quantified
    chart 2013* (clic → GSI, JCond89, RQD y banda de estructura) y
    *Calculator 2013* (RQD directo / λ / Jv 2005 / Jv 1982; JCond89
    directo con presets de la tabla 1, desde valoraciones, JCond76 con
    presets de la tabla 2, Jr/Ja de la tabla 3).
  - `FilteredTableDialog`: búsqueda + filtros por columna; mi con Rock
    Type / Texture, D con Application, MR con Rock Type / Texture.
  - `ModulusRatioDialog`: MR de la tabla (editable) y Ei = MR·σci con el
    σci del formulario, en la unidad de visualización.
- `MainWindow.pick_value` / `_pick`: un clic, y conversión kPa → unidad
  de visualización (corrige un fallo previo: el pick de σci escribía kPa
  en el campo aunque la unidad fuera MPa).
- σci: valores de RSData/ORMAS (35 y 0,6 MPa) — hecho en la revisión
  anterior.

## Pendiente (no implementado, con motivo)

- **Carta de flysch 2000 (Marinos & Hoek) y Heterogeneous 2013**: no son
  lineales; harían falta isolíneas digitalizadas. ORMAS tiene las suyas
  en su código, pero son su trabajo (no se copian); digitalizarlas desde
  la fuente (PDF de Marinos & Hoek en Bibliografia) es una tarea aparte.
- **Clic sobre la carta 2000** con isolíneas (método de ORMAS): la carta
  cuantificada 2013 cubre el uso con fuente oficial; la 2000 queda con el
  selector estructura × superficie de la 003.
