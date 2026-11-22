# Spec 002 — Los diez criterios de fallo de RSData

## Qué se construye

Registro de los **diez criterios** observados en RSData con sus parámetros y
valores por defecto exactos (del análisis en
`../../../Referencias/Ejemplos/RSData_analisis/01_modelos_material.md`), y
cálculo de envolventes:

| Criterio | Espacio de la envolvente |
|---|---|
| Mohr-Coulomb | principal + cortante-normal (lineal) |
| Hoek-Brown (clásico, a=0,5) | principal + cortante-normal |
| Drucker-Prager | principal + cortante-normal (lineal; tensión de corte como campo) |
| Generalized Hoek-Brown | principal + cortante-normal (spec 001) + MC equivalente |
| Power Curve | cortante-normal (τ = a·(σ+d)^b) |
| Barton-Bandis | cortante-normal (τ = σn·tan(φr + JRC·log10(JCS/σn))) |
| Cam-Clay | línea de estado crítico q = M·p' (principal y p'-q) |
| Modified Cam-Clay | idem |
| Softening-Hardening | superficie de fallo MC en compresión triaxial (q = M(p' − c/tanφ)) |
| NorSand | parámetros definidos; envolvente pendiente (sin documentación oficial localizada) |

La interfaz pasa a ser guiada por el registro: selector de criterio, formulario
dinámico de parámetros, gráficas que se adaptan al espacio del criterio.

## Decisiones documentadas

- **Drucker-Prager**: superficie Fs = √J2 + (q_φ/3)·I1 − k_φ = 0 del manual
  oficial RSData (descargado en `../../../Referencias/Bibliografia/Suelos/`).
  En triaxial: q = √3·(k_φ − q_φ·p').
- **Cam-Clay / MCC**: manuales oficiales RSData (línea de estado crítico,
  superficies de fluencia F = q + Mp·ln(−p/pc), F = q² + M²p(p+pc)). La
  spec 002 dibuja solo la **CSL**; las superficies de fluencia completas
  requieren el estado de consolidación (pc) y quedan para una fase con
  simulación de ensayos.
- **Softening-Hardening**: en fallo se reduce a Mohr-Coulomb; se usa
  M = 6·sinφ/(3−sinφ) (compresión triaxial) según el manual oficial.
- **Power Curve**: fórmula del manual de RocData 2004 (τ = a·(σ+d)^b). Los
  campos c y Waviness del diálogo de RSData se conservan en el registro con
  valor por defecto 0 y sin efecto hasta verificar su semántica exacta.
- **NorSand**: parámetros del diálogo de RSData; sin envolvente (Rocscience
  no publica manual teórico de NorSand en la página de manuales).

## Criterios de aceptación

1. Los diez criterios existen con los valores por defecto capturados de
   RSData (tests).
2. MC, DP, CC/MCC y SH dan envolventes lineales en espacio principal cuya
   construcción tangente reproduce la recta τ = c + σn·tanφ (MC) con
   exactitud de tolerancia.
3. HB clásico: σ1(0) = σci·√s.
4. Barton-Bandis reproduce la fórmula punto a punto; Power Curve reproduce
   τ = a·(σ+d)^b.
5. La GUI lista los diez criterios y actualiza formulario y gráficas al
   cambiar.
