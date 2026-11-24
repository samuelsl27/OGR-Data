# Plan 008 — Muestreadores y superposiciones

- `core/samplers.py` (sin Qt, MPa):
  - `sample(x, y, xq)`: coordenadas de la envolvente en un punto
    (interpolación con recorte al rango), para el stress sampler.
  - `hb_derivative(...)`: dσ1/dσ3 analítica de la familia Hoek-Brown
    (misma fórmula que `core/envelope.py`, Hoek 2002).
  - `instantaneous_mc(sig3, sig1, xq, slope=None)`: c y φ instantáneos
    desde d1 = dσ1/dσ3 (analítico si se pasa, si no derivada numérica):
    sinφ = (d1−1)/(d1+1); recta tangente σ1 = A + d1·σ3 con
    A = σ1* − d1·σ3*; c = A(1−sinφ)/(2cosφ). Construcción del programa de referencia antiguo (el manual del programa de referencia, que no se cita: regla 9).
  - `instantaneous_mc_shear(normal, shear, xq)`: tangente a la envolvente
    en espacio cortante: tanφ = dτ/dσn, c = τ* − σn*·tanφ (para
    Barton-Bandis / Power Curve, donde no hay espacio principal).
  - Rectas tangentes asociadas en ambos espacios (`mc_tangent_principal`,
    `mc_tangent_shear`).
  - `best_fit_mc(normal, shear)`: MC de mejor ajuste por mínimos
    cuadrados sobre la envolvente en rango (como el programa de referencia antiguo;
    el manual del programa de referencia, que no se cita: regla 9) para los criterios
    cortantes curvos.
  - `mogi_line(xmax)`: σ1 = 3,4·σ3 (el manual del programa de referencia, que no se cita: regla 9).
- Overlay MC en `refresh()`: GHB y HB clásico con la forma cerrada de
  Hoek 2002 (ya validada, spec 001); Power Curve y Barton-Bandis con el
  best-fit por mínimos cuadrados. Toggle "Overlay MC Envelope" en el
  menú Analysis (por defecto activado para GHB, comportamiento actual).
- GUI: menú Analysis con Stress Sampler e Instantaneous MC Sampler
  (checkables excluyentes; clic y arrastre continuo) y Overlay Mogi
  Line. Línea vertical punteada, tangente en ambas gráficas, punto de
  tangencia, resultados en la barra de estado. La derivada analítica se
  usa para HB/GHB; numérica en el resto.
- Temas: color "mogi" (verde) en `MPL_COLORS`.
- Tests sin Qt: tangente analítica vs numérica, tangencia en ambos
  espacios, Mogi frágil/dúctil por GSI, best-fit exacto sobre una recta
  MC, color del tema.
