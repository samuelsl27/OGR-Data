# Spec 026 — Anomalías de los parámetros de material

> Estado: **borrador** (2026-11-24), pendiente de clarificación y aprobación.

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

- **RF-1**: EL SISTEMA propondrá como N de NorSand por defecto un valor
  dentro del rango publicado, el de una calibración citada
  [NECESITA ACLARACIÓN: ¿el de la arena de Fraser River de Jefferies,
  Shuttle & Been (2015), o el centro del rango, 0,35?]. *(A1)*
- **RF-2**: EL SISTEMA propondrá como JCS por defecto la resistencia a
  compresión simple por defecto de la roca intacta del programa
  (100 MPa), por ser la de labios sanos. *(A2)*
- **RF-3**: MIENTRAS un campo no intervenga en ningún cálculo, EL SISTEMA
  lo mostrará deshabilitado con un tooltip que diga que OGR Data todavía
  no lo usa (el valor se sigue guardando y copiando tal cual, para no
  romper el contrato del portapapeles de la spec 005). *(A3, A9)*
- **RF-4**: CUANDO haya una fuente citable de la Power Curve completa,
  EL SISTEMA calculará la envolvente con c y la ondulación y habilitará
  esos campos [NECESITA ACLARACIÓN: fuente; ver `fuentes-pendientes.md`]. *(A3)*
- **RF-5**: EL SISTEMA interpretará *a* de la Power Curve con las
  tensiones en kPa, como el resto del formulario y del registro, y lo
  comprobará contra un valor del programa de referencia con b ≠ 1
  [NECESITA ACLARACIÓN: una captura con a, b, d y una tensión de prueba]. *(A4)*
- **RF-6**: EL SISTEMA usará compactación-dilatancia como tipo de
  dilatancia del cono por defecto, como el material por defecto exportado
  del programa de referencia. *(A5)*
- **RF-7**: EL SISTEMA interpretará Lambda Kappa de una sola forma,
  comprobada contra una simulación del programa de referencia
  [NECESITA ACLARACIÓN: una simulación con capa y Lambda Kappa ≠ 0
  exportada del programa de referencia]. *(A6)*
- **RF-8**: EL SISTEMA ofrecerá «Elastic» y «Plastic» como tipo de
  material; CUANDO el material sea elástico, las simulaciones de ensayo
  no plastificarán y la envolvente seguirá dibujándose. *(A7)*
- **RF-9**: EL SISTEMA ofrecerá en «Define by» las opciones que tenga el
  programa de referencia, cada una con su efecto
  [NECESITA ACLARACIÓN: captura del desplegable y de los campos de cada
  opción]. *(A8)*
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

- [NECESITA ACLARACIÓN: valor por defecto de N (RF-1)]
- [NECESITA ACLARACIÓN: fuente citable de la Power Curve completa (RF-4)]
- [NECESITA ACLARACIÓN: captura del programa de referencia para *a* con b ≠ 1 (RF-5)]
- [NECESITA ACLARACIÓN: simulación exportada con Lambda Kappa ≠ 0 (RF-7)]
- [NECESITA ACLARACIÓN: opciones de «Define by» (RF-9)]
