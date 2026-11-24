# Spec 008 — Muestreadores y superposiciones en las gráficas

## Qué se construye

Las herramientas de análisis gráfico del menú Analysis del programa de referencia y del programa de referencia antiguo (herramientas "Stress Sampler" e
"Instantaneous Mohr-Coulomb Sampler"):

1. **Stress Sampler**: clic (o arrastre) sobre cualquiera de las dos
   gráficas; muestra las coordenadas (σ3 o σn en el eje X) y los valores
   de la envolvente en ese punto; línea vertical punteada de marca.
2. **Instantaneous MC Sampler**: tangente a la envolvente curva en el
   punto clicado; muestra c y φ instantáneos y las coordenadas; la
   tangente se dibuja en ambas gráficas.
3. **Overlay MC Envelope**: superpone la recta MC equivalente (o la
   tangente) en las gráficas.
4. **Línea de Mogi**: σ1/σ3 = 3,4 (umbral frágil/ductil, verde, en la
   gráfica principal).

## Criterios de aceptación

- Sobre datos GHB conocidos, el instantaneous MC sampler reproduce c y φ
  de la tangente analítica (dσ1/dσ3 en el punto).
- La línea de Mogi corta la envolvente como esperado para GSI alto/bajo.
- Funciona en ambas gráficas y con arrastre continuo.
- Tests del cálculo sin Qt (la tangente ya sale de `tangent_shear`).

## Referencias

- El manual del programa de referencia antiguo (no se cita: regla 9) y las capturas de `05_profundizacion.md`.
- ORMAS no tiene muestreadores (diferencial a favor de OGR-Data).
