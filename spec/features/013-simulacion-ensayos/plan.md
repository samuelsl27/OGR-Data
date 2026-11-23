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

## Fases siguientes

- **13b**: Drucker-Prager, Cam-Clay/MCC, Softening-Hardening y NorSand
  como modelos constitutivos; Simple Shear y General; cortes a tracción.
- **13c**: modelos cíclicos y pestaña Animation.
