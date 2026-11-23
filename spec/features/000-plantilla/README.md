# Plantilla de feature (SDD)

Metodología: [hello-sdd](https://github.com/mouredev/hello-sdd), adaptada
a la suite. Flujo completo y puertas de aprobación en
[`AGENTS.md`](../../../AGENTS.md) («Flujo SDD»).

Para cada feature, copiar esta carpeta a `../NNN-nombre-en-kebab-case/`
con el siguiente número libre de tres cifras, y rellenar:

| Archivo | Fase | Qué contiene | Qué **no** contiene |
|---|---|---|---|
| [`spec.md`](spec.md) | Especificación (+ clarificación) | Qué y por qué: historias, requisitos RF-n en EARS, casos límite, fuera de alcance, UX, criterios de finalización, dudas | Stack, archivos, algoritmos, firmas |
| [`plan.md`](plan.md) | Planificación | Cómo: decisiones con la alternativa descartada, capas y archivos, modelo de datos, validación numérica, estrategia de tests; cada parte con los RF que cubre | Código |
| [`tasks.md`](tasks.md) | Tareas | Lista ordenada de tareas pequeñas (≤ 30 min), cada una con sus RF y su «Hecho cuando» | Tareas sin criterio verificable |

Cada fase termina con la aprobación explícita de la propietaria antes de
pasar a la siguiente. Una feature pequeña puede juntar plan y tareas en
`plan-tasks.md` (como la 020) si la propietaria lo acepta.

Las specs 001–024 son anteriores a esta plantilla y no se reescriben: se
leen como están.
