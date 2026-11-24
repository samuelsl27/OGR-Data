# 025f — Fuentes pendientes de la ayuda de parámetros

La ayuda (`ogr_data/data/parameter_help.json`) se escribe solo con
documentos leídos y **citables**. Estado tras las decisiones de la
propietaria del 2026-11-24:

- **Rangos derivados** (por ejemplo λ de NorSand pasado de base 10 a
  logaritmo natural, límites de mb, s y a deducidos de las ecuaciones de
  Hoek et al. 2002): **se aceptan**, con la derivación dicha en la ayuda.
- **Γ de Cam-Clay** con presiones en lb/in² (Schofield & Wroth 1968,
  tabla 6.1): **se deja**, con la advertencia.
- **Manuales del programa de referencia**: **no se citan** (regla 9 de
  `AGENTS.md`). Las entradas que solo tenían esa fuente pasan a pendientes.

Resultado: **65 parámetros con ayuda** y fuente citable; **35 pendientes**.
La investigación completa, con las fuentes que ya no se pueden citar, se
guarda fuera del repositorio en `../Referencias/Ejemplos/ayuda_parametros_025f/`.

## 1. Pendientes: qué parámetros y qué fuente haría falta

| Parámetros | Por qué están pendientes | Qué los resolvería (fuente científica citable) |
|---|---|---|
| Softening-Hardening: tipo y tabla de endurecimiento del cono, propiedad de endurecimiento, ángulo de dilatancia, tipo de dilatancia, tipo de capa, endurecimiento y tabla de la capa, Lambda Kappa, tensión media inicial (10) | Solo los documenta el programa de referencia | Pietruszczak, S. (2010). *Fundamentals of Plasticity in Geomechanics*, CRC Press (origen declarado del modelo) |
| Power Curve: a, b, c, d, ondulación, sus residuales y la relación de dilatancia (11) | Solo los documenta el programa de referencia; ninguna fuente leída da el autor original de τ = a(σn + d)^b + c | El artículo original de la ley potencial de resistencia que se quiera adoptar; para la ondulación, Miller, S.M. (1988), *Proc. 39th Highway Geology Symposium*, 346-356 |
| Residuales de Hoek-Brown: mb y s residuales, GSI y mi residuales (4) | Solo el manual del programa de referencia los describe | Cai, M., Kaiser, P.K., Tasaka, Y., Minami, M. (2007). Determination of residual strength parameters of jointed rock masses using the GSI system. *IJRMMS* 44(2) |
| Parámetro de dilatancia mψ de Hoek-Brown (1) | Ídem | Alejano, L.R. & Alonso, E. (2005). Considerations of the dilatancy angle in rocks and rock masses. *IJRMMS* 42 |
| Tipo de material (Elastic/Plastic), «residual igual a pico», tracción residual, k residual de Drucker-Prager (4) | Conceptos de programa sin fuente científica leída | Un texto de plasticidad que describa el modelo elasto-frágil-plástico (Vermeer & de Borst 1984 trata la plasticidad no asociada; habría que localizar el apartado) |
| NorSand: condición de consolidación inicial, módulo volumétrico del fluido, G mínimo (3) | No los define ninguna fuente citable leída | Jefferies, M. & Been, K. (2015). *Soil Liquefaction: A Critical State Approach*, 2.ª ed., CRC Press |
| Barton-Bandis: resistencia residual y ángulo de dilatancia (2) | No los define ninguna fuente citable leída | Barton & Choubey (1977), *Rock Mechanics* 10; Barton & Bandis (1990) |

## 2. Documentos de pago o no públicos que mejorarían la ayuda ya escrita

| Documento | Para qué |
|---|---|
| Jefferies (1993), *Géotechnique* 43(1); Jefferies & Shuttle (2002), *Géotechnique* 52(9) | Originales de NorSand (hoy a través del artículo abierto de 2015) |
| Roscoe & Burland (1968), en *Engineering Plasticity*, CUP; Wood (1990), *Soil Behaviour and Critical State Soil Mechanics*, CUP | Cam-Clay modificado y tablas de λ, κ, M y N en kPa para más suelos |
| Kulhawy & Mayne (1990), EPRI EL-6800 (puede ser público) | Rangos de OCR y de parámetros de estado crítico |
| Hoek & Brown (1980, 1997); Brown (1981); Bieniawski (1989); Coulomb (1776); Mohr (1900); Zytynski et al. (1978) | Originales hoy citados a través de Hoek et al. (2002), Hoek (2023) y Drucker & Prager (1952) |

## 3. Rangos típicos que no da ninguna fuente leída

Sin rango hasta tener fuente: tracción de suelos y macizos, cohesión
residual distinta de 0, k de Drucker-Prager, OCR por tipo de suelo,
σ3max, profundidad del túnel y altura del talud, peso específico (solo un
valor típico), G de referencia y G operativo, Hy y ψ0 de NorSand.

## 4. Anomalías del programa encontradas al documentar

Pasan a la [spec 026](../026-anomalias-de-parametros/spec.md).
