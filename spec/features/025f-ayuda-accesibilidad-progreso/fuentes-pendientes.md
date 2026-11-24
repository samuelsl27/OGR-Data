# 025f — Fuentes pendientes y lo que necesito de la propietaria

La ayuda de los parámetros (`ogr_data/data/parameter_help.json`) se
escribió el 2026-11-24 solo con documentos leídos: 98 entradas con
definición (EN/ES), fuente y localizador (página, tabla o ecuación), y
rango típico **solo** cuando una fuente lo da. Lo que no se pudo apoyar en
una fuente fiable está aquí, ordenado por lo que más falta.

Documentos descargados para esto (fuentes públicas, ya en
`../Referencias/Bibliografia/` y en su `00_INDICE.md`): Hoek & Diederichs
(2006), Drucker & Prager (1952), Schofield & Wroth (1968), Jefferies,
Shuttle & Been (2015), Vermeer & de Borst (1984), FHWA GEC 5 (2002) y el
cap. 20 del manual teórico de RS2.

## 1. Sin ninguna fuente: dos parámetros sin ayuda

| Parámetro | Qué falta | Qué lo resolvería |
|---|---|---|
| Softening-Hardening · **Initial Mean Stress** | Ningún documento lo define (ni el manual teórico, ni la ayuda de RS2, ni la API de RS3, que solo da su nombre). Podría ser la presión inicial de la capa (*cap*), pero nadie lo dice. | La página de ayuda de RSData/RS2 de *Define Material Properties → Strength → Softening Hardening*, o una captura de la ayuda dentro de RSData. |
| Barton-Bandis · **Residual Strength** | Ningún documento lo define; el manual de RS2 dice que el residual de Barton-Bandis es sin cohesión con φr, lo que no explica un campo aparte. | La ayuda de RSData del modelo Barton-Bandis (no está en el índice público de manuales teóricos) o una captura de RSData con su texto de ayuda. |

## 2. Documentos de pago o no públicos (citados hoy de segunda mano)

Si puede conseguir alguno, se sustituye la cita secundaria por la original.

| Prioridad | Documento | Para qué |
|---|---|---|
| Alta | Jefferies, M. & Been, K. (2015). *Soil Liquefaction: A Critical State Approach*, 2.ª ed., CRC Press | NorSand completo: rangos de Hy, ψ0, G_ref; definición de OCR, Cap Softening, Fluid Bulk Modulus tal como los usa el modelo |
| Alta | Manual teórico de NorSand de Rocscience (RSData/RS2) | No está en la documentación pública; confirmaría el significado exacto de cada campo de RSData |
| Alta | Cai, M. et al. (2007). Determination of residual strength parameters of jointed rock masses using the GSI system. *IJRMMS* 44(2) | Valores residuales de GSI, mi, mb, s (hoy sin rango) |
| Media | Roscoe, K.H. & Burland, J.B. (1968). On the generalised stress-strain behaviour of 'wet' clay. En *Engineering Plasticity*, CUP | Original de Cam-Clay modificado (hoy solo el manual de Rocscience) |
| Media | Wood, D.M. (1990). *Soil Behaviour and Critical State Soil Mechanics*, CUP | Tablas de λ, κ, M y N en kPa para más suelos (hoy solo las cinco arcillas de Schofield & Wroth) |
| Media | Pietruszczak, S. (2010). *Fundamentals of Plasticity in Geomechanics*, CRC | Original del modelo Softening-Hardening |
| Media | Barton & Choubey (1977), *Rock Mechanics* 10; Barton & Bandis (1982, 1990) | Originales de JRC, JCS y φr (hoy vía Hoek 2023 y FHWA 1989, que los reproducen) |
| Media | Jefferies (1993), *Géotechnique* 43(1); Jefferies & Shuttle (2002), *Géotechnique* 52(9) | Originales de NorSand (hoy vía el artículo abierto de 2015) |
| Baja | Kulhawy & Mayne (1990). *Manual on Estimating Soil Properties for Foundation Design*, EPRI EL-6800 | Rangos de OCR y parámetros de estado crítico; puede ser público, no se intentó |
| Baja | Zytynski et al. (1978), *IJNAMG* 2 | Origen de la elección ν constante / G constante de Cam-Clay |
| Baja | Hoek & Brown (1980, 1997); Brown (1981); Bieniawski (1989); Coulomb (1776); Mohr (1900) | Originales hoy citados a través de Hoek et al. (2002) y Hoek (2023) |
| Baja | Miller, S.M. (1988), *Proc. 39th Highway Geology Symp.* | Original de la ondulación (*waviness*) de Power Curve |
| — | Autor original del criterio Power Curve | Ninguna fuente leída lo nombra; RocData solo dice «en algunos textos» |

## 3. Rangos típicos que no da ninguna fuente leída

Se muestran sin rango hasta tener fuente: tracción de suelos y macizos,
cohesión residual distinta de 0, k de Drucker-Prager, todos los de Power
Curve, OCR por tipo de suelo, σ3max, profundidad del túnel y altura del
talud, el peso específico (solo hay un valor típico, 0,027 MN/m³),
G_ref, G mínimo, el G operativo (solo el de pequeña deformación), A y la
dilatancia de Softening-Hardening, Lambda Kappa, Hy, ψ0 y el módulo del
fluido.

## 4. Decisiones que le pido

1. **Rangos derivados por cálculo, no publicados tal cual.** Hoy se
   muestran con la derivación dicha en la ayuda:
   - NorSand λ: la fuente da 0,03–0,15 en base 10; se muestra además
     ~0,013–0,065 en logaritmo natural (factor 2,3 del propio artículo).
   - mb, s y a de Hoek-Brown: límites deducidos de las ecs. 3–5 de Hoek
     et al. (2002).
   - q de Drucker-Prager ≤ 0,866: deducido de Drucker & Prager (1952).
   ¿Se aceptan así, o solo rangos literales?
2. **Γ (volumen específico) de Cam-Clay**: la única tabla (Schofield &
   Wroth, tabla 6.1) usa la presión en lb/in²; la ayuda lo dice. ¿Se deja
   así o se quita el rango hasta tener una tabla en kPa?
3. **Citas de manuales de Rocscience.** Los parámetros propios del
   programa (Softening-Hardening, Power Curve, opciones residuales,
   mψ de Hoek-Brown) solo tienen como fuente los manuales de Rocscience,
   y se citan así. ¿Le parece bien que la ayuda nombre esos manuales?

## 5. Anomalías encontradas en el programa (se reportan, no se han tocado)

Regla 6 de `AGENTS.md`: se muestran con la evidencia y se corrigen con su
spec si lo decide.

| Dónde | Qué se vio | Evidencia |
|---|---|---|
| NorSand · N (valor por defecto) | 0,05 (el de RSData, capturado en la spec 002), por debajo del rango publicado 0,2–0,5; el tutorial de RSData usa 0,5 | Jefferies, Shuttle & Been (2015), tabla 2; tutorial NorSand de RSData |
| Barton-Bandis · JCS (valor por defecto) | 1e7 kPa = 10 000 MPa (el de RSData, capturado en la spec 002), muy por encima de cualquier roca | Hoek (2023) tabla de resistencias; FHWA 1989 |
| Power Curve · c y ondulación | `core/criteria_envelopes.py` los ignora «hasta verificar su significado»; el manual de RS2 (ec. 20.3) ya lo da: τ = a(σn + d)^b + c + σn·tan θw | `Bibliografia/Rocas/Rocscience_RS2_Theory_20_Slide-Isotropic-Models.pdf` |
| Softening-Hardening · Cone Dilation Type (por defecto) | OGR-Data usa «Mohr-Coulomb»; el `.rsdata` exportado de RSData guarda `ConeIsCompactDilation=true` para el material por defecto | `Ejemplos/RSData_analisis/exportes/verificacion_rutas_estados.rsdata` |
| Softening-Hardening · Lambda Kappa | No está claro si es (λ − κ) o (λ − κ)/v: la ec. 11.10 del manual no lleva el volumen específico, la 8.8 de Cam-Clay sí | Manual teórico de Rocscience, caps. 8 y 11 |
| Mohr-Coulomb / Hoek-Brown · Material Type | El registro solo ofrece «Plastic»; RS2 y RSData ofrecen Elastic y Plastic | Ayuda de RS2 *Strength Properties*; captura de RSData |
| Hoek-Brown generalizado · Define by | El registro solo ofrece «GSI»; RSData tiene más opciones que ningún documento leído describe | `RSData_analisis/01_modelos_material.md` |
