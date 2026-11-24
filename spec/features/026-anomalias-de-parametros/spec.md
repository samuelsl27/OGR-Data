# Spec 026 — Anomalías de los parámetros de material

> Estado: **borrador listo para aprobar** (2026-11-24). Las dudas se resolvieron con las fuentes aportadas por la
> propietaria o por deducción, como ella indicó («el resto dedúcelo con lógica»).

## Contexto y objetivo

Al documentar cada parámetro con fuentes (spec 025f) aparecieron valores
por defecto fuera de los rangos publicados, campos cuyo significado no
estaba claro y, al comprobarlo en el código, **13 campos del formulario
que ningún cálculo lee**: se pueden editar y no cambian nada, lo que
incumple la regla 7 de `AGENTS.md` («ningún ajuste puede no hacer nada»)
y la U9 de la guía de UX. Esta spec los corrige o, mientras falte una
fuente citable para implementarlos, hace que la interfaz lo diga.

Evidencias: la ayuda con fuentes (`ogr_data/data/parameter_help.json`),
`spec/features/025f-ayuda-accesibilidad-progreso/fuentes-pendientes.md`,
y las capturas y exportaciones privadas del programa de referencia en
`../Referencias/`.

## Hallazgos

| Id | Dónde | Qué pasa | Evidencia |
|---|---|---|---|
| A1 | NorSand · N | Valor por defecto 0,05; el rango publicado para arenas es 0,2–0,5 | Jefferies, Shuttle & Been (2015), tabla 2, p. 78 |
| A2 | Barton-Bandis · JCS | Valor por defecto 1e7 kPa (10 000 MPa), por encima de cualquier roca; JCS es la resistencia a compresión de los labios de la junta, igual a la de la roca intacta con labios sanos | Hoek (2023), cap. «Shear strength of discontinuities», ecs. 4–7 |
| A3 | Power Curve · c, ondulación y sus residuales; relación de dilatancia | El cálculo los ignora (`core/criteria_envelopes.py`); son editables | Código; ninguna fuente citable leída da la ecuación completa |
| A4 | Power Curve · a | La envolvente se calcula con σn en MPa y el formulario está en kPa: con b ≠ 1 el mismo *a* da otra curva según la unidad interna | Código (`criteria_envelopes.shear_curve`) |
| A5 | Softening-Hardening · tipo de dilatancia del cono | Por defecto «Mohr-Coulomb»; el material por defecto del programa de referencia exportado guarda compactación-dilatancia | Exportación privada en `../Referencias/` |
| A6 | Softening-Hardening · Lambda Kappa | No está claro si es (λ − κ) o (λ − κ)/v; cambia el endurecimiento de la capa | Ecuaciones de la capa del modelo; sin fuente citable |
| A7 | Mohr-Coulomb y Hoek-Brown · tipo de material | Solo ofrece «Plastic» y nada lo lee; el programa de referencia ofrece también «Elastic» | Capturas privadas |
| A8 | Hoek-Brown generalizado · Define by | Solo ofrece «GSI» y nada lo lee; el programa de referencia tiene más opciones que ningún documento leído describe | Capturas privadas |
| A9 | Campos que nada lee (13) | `c`, `waviness`, `residual_c`, `residual_waviness`, `dilation_ratio` (Power Curve); `cap_softening`, `fluid_bulk_modulus`, `initial_consolidation_condition` (NorSand); `residual_dilation`, `residual_strength` (Barton-Bandis); `tensile_cutoff_type`, `define_by` (Hoek-Brown generalizado); `material_type` (Mohr-Coulomb, Hoek-Brown) | Búsqueda en `ogr_data/core` (2026-11-24) |

## Historias de usuario

- H1: Como geotécnico quiero que los valores por defecto sean razonables
  y tengan fuente, para no arrastrar un dato imposible a Slip2D.
- H2: Como usuario quiero que todo campo que edito cambie el resultado, o
  que el programa me diga que no se usa.

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA propondrá como N de NorSand por defecto 0,43, el
  de la arena de Fraser River (Jefferies, Shuttle & Been 2015, tabla 2,
  p. 78), dentro del rango publicado 0,2–0,5. *(A1)*
- **RF-2**: EL SISTEMA propondrá como JCS por defecto la resistencia a
  compresión simple por defecto de la roca intacta del programa
  (100 MPa): con labios sanos JCS es la resistencia de la roca intacta
  (Barton & Choubey 1977, pp. 6 y 8), y es también el valor de su ejemplo
  resuelto (p. 7). *(A2)*
- **RF-3**: MIENTRAS un campo no intervenga en ningún cálculo, EL SISTEMA
  lo mostrará deshabilitado con un tooltip que diga que OGR Data todavía
  no lo usa (el valor se sigue guardando y copiando tal cual, para no
  romper el contrato del portapapeles de la spec 005). *(A3, A9)*
- **RF-4**: EL SISTEMA calculará la Power Curve como
  τ = a(σn + d)^b + c + σn·tan i, con i la ondulación, y habilitará c, i y
  sus residuales. La parte a(σn + d)^b es la envolvente potencial de
  Hoek y Brown (FHWA 1989, ec. 30, p. 5.25: a = A·σc^(1−B), b = B,
  d = −T·σc); c e i se **deducen** (c, término de tipo cohesión que vale
  la resistencia en σn = −d; i, ángulo de Patton que suma rozamiento,
  Hoek 2023 ec. 3) y se comprueban contra valores del programa de
  referencia (comparar está permitido; citarlo, no). *(A3)*
- **RF-5**: EL SISTEMA interpretará *a* de la Power Curve con las
  tensiones en kPa, como c, d y el resto del registro (hoy el cálculo usa
  σn en MPa, `core/criteria_envelopes.py` y `core/calibration.py`); como
  a = A·σc^(1−B) depende de la unidad, el ajuste y la calibración que
  rellenan *a* lo harán también en kPa. Los proyectos guardados con b ≠ 1
  se convierten al abrirlos (a_kPa = a_MPa·1000^(1−b)). *(A4)*
- **RF-6**: EL SISTEMA usará compactación-dilatancia como tipo de
  dilatancia del cono por defecto, como el material por defecto exportado
  del programa de referencia. *(A5)*
- **RF-7**: EL SISTEMA dirá en la etiqueta y en la ayuda que Lambda Kappa
  es Λ = (λ − κ)/v, que es lo que el cálculo ya usa
  (pc·exp(Δεv^p/Λ), `core/simulation.py`), según la regla de
  endurecimiento de Cam-Clay (Wood 1990, ec. 4.21, p. 94); el cálculo no
  cambia. *(A6)*
- **RF-8**: EL SISTEMA ofrecerá «Elastic» y «Plastic» como tipo de
  material; CUANDO el material sea elástico, las simulaciones de ensayo
  no plastificarán y la envolvente seguirá dibujándose. *(A7)*
- **RF-9**: EL SISTEMA ofrecerá en «Define by» «GSI» (mb, s y a se
  calculan con GSI, mi y D, Hoek et al. 2002, ecs. 3–5) y «mb, s, a»
  (se introducen directamente, como en el Hoek-Brown clásico); la segunda
  opción se deduce de la forma del criterio. *(A8)*
- **RF-10**: EL SISTEMA tendrá un test que falle si un campo del registro
  no lo lee ningún cálculo y no está marcado como «no usado». *(A9)*

## Requisitos no funcionales

- Proyectos `.ogrdata` antiguos: los valores guardados se respetan; solo
  cambian los valores por defecto de materiales nuevos.
- Ninguna referencia al programa de referencia en código, interfaz,
  tests ni documentos del repositorio (regla 9).
- Validación numérica contra fuente publicada o contra el programa de
  referencia (regla 1), nunca contra lo que el código da hoy.

## UX

U7 (lo deshabilitado dice por qué), U9 (valores por defecto con fuente;
ningún ajuste que no mueva el número), U11.

## Casos límite

- Proyecto guardado con un campo que ahora sale deshabilitado: el valor se
  conserva en el fichero.
- Material elástico calibrado o simulado: los resultados no muestran
  plastificación.

## Fuera de alcance

- Las fuentes de la ayuda (siguen en `fuentes-pendientes.md`).
- Retirar las menciones antiguas al programa de referencia (spec 027).

## Criterios de finalización

Cada RF con su test; RF-4, RF-5, RF-7 y RF-9 validados contra su
referencia cuando llegue; suite en verde.

## Dudas abiertas

Ninguna: resueltas el 2026-11-24 con Jefferies, Shuttle & Been (2015),
Barton & Choubey (1977), FHWA (1989), Wood (1990) y Hoek et al. (2002), y
por deducción donde no hay fuente (RF-4 c e i, RF-9 segunda opción).
Pendiente solo la aprobación para implementarla.
