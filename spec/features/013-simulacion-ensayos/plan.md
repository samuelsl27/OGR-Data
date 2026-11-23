# Plan 013 — Simulación de ensayos (fase 13a)

Referencias: captura `20_define_test_simulations.png` (diálogo de RSData:
Name, Symbol, Test Type, Seepage Condition, Loading Direction, Maximum
Strain 0,1, Number of Steps 100, Cyclic Loading Cycles), captura `12_*`
(pestaña Stiffness: Linear Isotropic, ν = 0,3, E = 20 000 kPa) y
`07_estados_y_rutas_verificado.md` §8: en RSData 1.009 **Compute no añade
curvas simuladas a las rutas de laboratorio**; dónde muestra RSData la
simulación de un ensayo no está verificado. OGR Data las dibuja en las
Stress Path Graphs (decisión propia, anotada).

## Núcleo (`core/simulation.py`, sin Qt)

- `TestSimulation`: campos de RSData + **Confining Stress** (kPa, por
  defecto 100 como σ'h0 de las rutas; RSData no documenta ese campo).
  Tipos: los cinco de RSData; se simulan Uniaxial, Triaxial y Biaxial;
  Simple Shear y General se guardan pero quedan para 13b (ejes
  principales que giran / carga general).
- Rigidez: elástica lineal isótropa (`Material.stiffness`, formato
  `.ogrdata` v2 con claves nuevas opcionales).
- Resistencia: MC, HB (a = 0,5) y GHB, perfectamente plásticos; con *Set
  Residual to Peak* desactivado, elasto-frágil-plástico (caída a la
  residual en el primer paso plástico, convención RS2).
- Formulación en tensiones principales (compresión positiva, ejes fijos):
  seis superficies f_ij = σi − S(σj) que forman la pirámide (aristas y
  vértice exactos); potencial plástico MC con ψ (ángulo de dilatancia),
  HB con el *Dilation Parameter* como mb del potencial (0 = sin cambio de
  volumen plástico; = mb asociado), GHB sin dilatancia (RSData no tiene
  ese campo para GHB). Return mapping Euler implícito con conjunto activo
  (Newton sobre σ y Δλ; exacto en una iteración para MC) y retorno al
  vértice si hay más de dos superficies activas.
- Control mixto: deformación axial impuesta; las condiciones laterales
  se resuelven por Newton sobre modos laterales simétricos (en la arista
  triaxial el reparto entre ε2 y ε3 está indeterminado). Subdivisión del
  paso si no converge.
  - Uniaxial: σ'lat = 0. Triaxial drenado: σ'lat = σc. No drenado:
    εv = 0 (εr = −εa/2), u = σc − σ'r con presión de célula constante.
  - Biaxial (deformación plana): ε2 = 0; σ'3 = σc (drenado) o ε3 = −ε1
    y u = σc − σ'3 (no drenado).
  - Tension: deformaciones axiales negativas (extensión).
  - Cíclico básico: 0 → máx → 0 por ciclo, Number of Steps por
    semiciclo (sin modelos cíclicos ni animación: 13c).
- Resultados: ε (3), σ' (3), u; p', q (sin signo, como RSData), εv,
  εq = √(2/3 e:e) con el signo de εa − εr.

## Verificación (tests contra soluciones cerradas)

- **Criterio de aceptación 13a**: triaxial CD sobre MC (c = 10,5 kPa,
  φ = 35°, σc = 100 kPa): meseta q_f = (Nφ − 1)σc + 2c√Nφ = 309,358 kPa
  (error < 1e-6, criterio 1 %).
- Uniaxial a compresión (2c√Nφ) y a tracción (−2c/√Nφ); extensión
  triaxial σa = (σc − σcm)/Nφ; CU con p' constante y
  q_f = 3[(Nφ − 1)σc + σcm]/(2 + Nφ); biaxial σ'1 = Nφσ'3 + σcm con σ2
  intermedia; pendiente de dilatancia dεv/dεa = 1 − Nψ; caída frágil a la
  residual; GHB q_f = σci(mb σ3/σci + s)^a para tres confinamientos.
- La comparación con los tutoriales de RSData (NorSand, MCC) queda para
  13b, cuando existan esos modelos.

## GUI

- Menús en el orden de RSData: **Tests** (Define Test Simulations…) tras
  Failure States y **Compute** tras Calibrate. Compute vuelve a calcular
  todo y lista lo que no se puede simular.
- Diálogo `TestSimulationsDialog` (misma base que estados y rutas);
  Confining Stress solo en triaxial/biaxial; nota para tipos de 13b.
- Árbol: los ensayos cuelgan del material (visibilidad, editar, borrar).
- Barra lateral: grupo **Stiffness** (ν, E en la unidad de visualización)
  con botón **Erm** (E = módulo del macizo de GHB, como RSData rellena E).
- Dibujo: las cuatro Stress Path Graphs (líneas continuas sin marcador;
  las rutas de laboratorio siguen con puntos) y la ruta σ'3–σ'1 a trazos
  en la gráfica de tensiones principales. Caché por entradas (modelo,
  rigidez, ensayo): editar un parámetro recalcula al instante.
- Plantilla de suelo: «Material Model + Test, Stress Path» → trae ahora
  también el ensayo Test 1.
- Informe (spec 015): Defined Test Simulations con configuración, rigidez
  y resumen calculado.

## Fase 13b (hecha)

Fuentes: manuales de teoría RS2/RSData en `Referencias/Bibliografia/Suelos/`
(Drucker-Prager, Cam-Clay y Modified Cam-Clay, Softening-Hardening) y
`Rocas/` (Mohr-Coulomb, Hoek-Brown/GHB); ecuaciones leídas de las páginas
renderizadas (el texto extraído pierde los símbolos).

- **Motor en tensores 3×3** (deformaciones ingenieriles en el orden
  a, x, y, a-x, x-y, a-y): retorno espectral para los modelos isótropos
  (la tensión de prueba conserva sus ejes principales con elasticidad
  isótropa), válido con ejes que giran. Superficies como objetos (cara de
  la pirámide, cono DP, corte a tracción) en un mismo conjunto activo de
  hasta tres superficies, con búsqueda exhaustiva de respaldo antes del
  vértice; las iteraciones de Hoek-Brown se mantienen por encima de su
  vértice a tracción. Newton del control mixto amortiguado (búsqueda
  lineal); el paso de rotura frágil se resuelve en la rama residual si la
  prueba supera el pico.
- **Corte a tracción** (ecs. 4.3, 0.7, 0.8 y 11.11 de los manuales,
  asociado) en MC, DP y Softening-Hardening con su Tensile Strength
  (pico/residual). Lectura literal: **T = 0 = sin tracción** (sentido RS2).
  Cambia el ensayo de tracción uniaxial de MC por defecto de 13a (antes
  llegaba a −2c/√Nφ). HB y GHB conservan su resistencia a tracción propia
  (no tienen campo en RSData).
- **Drucker-Prager** (ecs. 4.1-4.2): √J2 = k + qφ p, potencial
  √J2 − qψ p (qψ = Dilation Parameter), frágil con k y q residuales.
  Ejemplo del manual (Fig. 4.2: qφ = 0,5, k = 3 kPa, p0 = 100 kPa):
  q_f = 129,05 kPa, igual que la figura. **Corregido de paso** el signo de
  qφ en la envolvente de la spec 002 (`criteria_envelopes.py` daba q
  decreciente con p).
- **Cam-Clay y Modified Cam-Clay** (§8): superficies q + M p ln(p/pc) y
  q² + M² p (p − pc), flujo asociado, pc_{n+1} = pc_n exp(v Δεv^p/(λ−κ)),
  K = v p/κ integrado exactamente en el paso, ν de la pestaña Stiffness
  (el manual pide G o ν; E no se usa), inicio isótropo p0 = confinamiento,
  pc0 = OCR·p0, v0 sobre la línea de hinchamiento que pasa por pc0 en la
  virgen v = N − λ ln p (N = Specific Volume at Unit Pressure, kPa).
  Retorno implícito en (p, q, pc, Δλ); el pico de la curva de Cam-Clay
  original (q = 0, p = pc) es una esquina: retorno al vértice.
  Verificación: integración independiente de las ecuaciones de velocidad
  con 200 000 pasos — error < 0,5 % con 1000 pasos y < 1 % con los 100 de
  RSData. **Comparación con el manual** (Fig. 8.5, Tabla 8.1, leída de la
  gráfica): RSData da q ≈ 385-390 kPa y εv ≈ 0,051 (analítica) / 0,055
  (RS2) a εa = 0,2; OGR da q = 374,6 kPa (−3 %) y εv = 0,062. La
  diferencia no se explica con v constante (probado: q = 377,7); las dos
  curvas del propio manual también difieren entre sí. Se documenta, no se
  ajusta. OCR 2 y OCR 5 reproducen el comportamiento de las Figs. 8.7-8.8
  (elástico hasta la superficie; lado seco con pico y ablandamiento hacia
  la CSL); no drenado termina en q = M p'.
- **Softening-Hardening** (§11.1), mecanismo desviador: superficie de
  Mohr-Coulomb con φ movilizado, tan φ = tan φf εq^p/(εq^p + A) (ec. 11.4,
  Cone Hardening «Hyperbolic»), cohesión movilizada que mantiene el
  vértice en c/tan φf (ec. 11.3), endurecimiento implícito (raíz acotada,
  Brent). Cone Dilation «Mohr-Coulomb»: ψ = ψf φ/φf (ecs. 11.5-11.6);
  «Compaction-Dilation» (ec. 11.7): dilatancia d = M_ψ − η con M_ψ de
  compresión triaxial y η al inicio del paso, convertida al flujo de las
  caras de la pirámide. Ejemplo del manual (Fig. 11.4, arena de Hostun
  suelta): q ≈ 774 kPa a εa = 0,15 (figura ≈ 760) y εv que sube a ≈ 0,012
  y luego baja (figura ≈ 0,0105). Opciones de los combos con los nombres
  del manual (RSData no los mostró en las capturas); los archivos con
  «default» se leen como la primera opción.
- **Simple Shear**: γ impuesta, sin deformación lateral, σ'v = confinamiento
  (drenado) o εv = 0 y u = σc − σ'v (no drenado), inicio isótropo.
  Verificación: τ/σ'v → sin φ cos ψ/(1 − sin φ sin ψ) (Davis 1968) y
  τ = G γ en el tramo elástico.
- Rendimiento: 100 pasos en 0,02-0,6 s según el modelo (MCC el más lento).

## Pendiente

- NorSand: sin manual de teoría público (spec 002).
- General Test: RSData no documenta sus entradas.
- Softening-Hardening: casquete (vertical y elíptico) y endurecimiento
  tabular; Cam-Clay con G constante (el manual lo permite).
- **13c**: modelos cíclicos y pestaña Animation.
