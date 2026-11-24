# 025f — Fuentes de la ayuda de parámetros: estado final

La ayuda (`ogr_data/data/parameter_help.json`) está **completa**: todos los
parámetros del registro y de la rigidez (101 entradas: un mismo campo puede
significar cosas distintas según el criterio) tienen definición en inglés y
español, fuente y localizador (página, tabla o ecuación). Decisiones de la
propietaria (2026-11-24):

- Rangos derivados por cálculo: **se aceptan**, con la derivación dicha.
- Γ de Cam-Clay con presiones en lb/in²: **se deja**, con la advertencia
  (además, Wood 1990 confirma el valor de la arcilla de Weald en kPa).
- **Regla 9 de `AGENTS.md`**: no se cita al fabricante del programa de
  referencia.
- **Lo que ninguna fuente cubre se deduce con lógica** (de las ecuaciones
  del modelo, de la definición de la magnitud o del propio programa) y se
  marca: la ayuda dice «Deducido por OGR Data (sin fuente publicada)» y el
  localizador explica la deducción.

## Resultado

| | Entradas |
|---|---|
| Con fuente publicada | 59 |
| Con fuente y una parte deducida | 39 |
| Solo deducidas (G mínimo de NorSand; c y b residual de Power Curve) | 3 |
| Pendientes | 0 |
| Con rango típico | 85 |

Fuentes nuevas aportadas por la propietaria y ya archivadas en
`../Referencias/Bibliografia/` (con su `00_INDICE.md`): Cai et al. (2007),
Barton & Choubey (1977), Jefferies & Shuttle (2002), Jefferies & Been
(2.ª ed., extracto), Kulhawy & Mayne (1990, EPRI EL-6800), Wood (1990) y
Davis & Selvadurai (2002). La investigación completa (dos rondas) queda
fuera del repositorio en `../Referencias/Ejemplos/ayuda_parametros_025f/`.

## Lo que todavía mejoraría la ayuda (no bloquea nada)

| Documento | Qué aportaría |
|---|---|
| Jefferies & Been, *Soil Liquefaction*, 2.ª ed., **capítulo 3 completo** (el extracto acaba en la p. 47) | Rango general de Hy y N de NorSand (hoy solo calibraciones de Fraser River y Brasted) |
| Pietruszczak (2010), *Fundamentals of Plasticity in Geomechanics* | Original de la ley hiperbólica del cono de Softening-Hardening y valores de A |
| Alejano & Alonso (2005), *IJRMMS* 42 | Valores típicos de mψ (dilatancia de Hoek-Brown) |
| Miller (1988), *Proc. 39th Highway Geology Symposium*; Patton (1966), *Proc. 1st ISRM Congress* | Cómo se combina la ondulación con una ley potencial y su rango |
| Un manual de caracterización con OCR por tipo de suelo (p. ej. FHWA-NHI-16-072) | Rangos de OCR por tipo de suelo (hoy: base de 96 arcillas, 1–40) |
| Ensayos de tracción en suelos cementados o compactados | Tracción de suelos (hoy: 0 sin cementación) |

Un significado sigue deducido a medias: el campo «Residual Strength» de
Barton-Bandis. Se sabe qué es la resistencia residual de una junta
(τr = σn·tan φr, Barton & Choubey 1977), pero no qué número guarda ese
campo; OGR Data no lo usa todavía (spec 026).

## Anomalías del programa encontradas al documentar

Pasan a la [spec 026](../026-anomalias-de-parametros/spec.md).
