# Spec 025b — Ventana principal: resultados a la vista

> Estado: **aprobada** (2026-11-24): opción B, lecturas del muestreador
> en el panel y en la barra de estado, título en *Project Settings*.
> RF-9 añadido después de aprobar (ver «Cambios tras la aprobación»).

## Contexto y objetivo

Hallazgos F1 y F2 de la [revisión](../025-revision-ux/revision.md): a
1366×768 los parámetros calculados empiezan unos 1000 px más abajo en una
barra lateral que solo muestra 719 px, y esa barra mezcla el material, el
proyecto, el programa y acciones de archivo que repiten el menú. Causa
(los parámetros) y efecto (los resultados) quedan en pantallas
distintas, y la acción que justifica el programa —copiar el material a
Slip2D— está a media columna.

## Opciones exploradas

Prototipos sobre la ventana real (GHB, 1366×768; capturas offscreen, el
tipo de letra no es el de Windows). En B–E la barra lateral pierde
unidades, título, copiar y archivo, que pasan a una barra de herramientas.

| | Opción | Captura | A favor | En contra |
|---|---|---|---|---|
| A | Actual: resultados al final de la barra lateral | [A](opciones/opcion_a.png) | Nada que cambiar | Resultados fuera de la vista (U1) |
| **B** | **Panel acoplable a la derecha** | [B](opciones/opcion_b.png) | Entrada a la izquierda, gráficas en medio, salida a la derecha: se lee como el flujo de trabajo. Fijo mientras se desplazan los parámetros. Hueco debajo para el muestreador y la comparación entre materiales. Patrón de RSData (panel derecho plegable) y de las apps tipo CAD | Las gráficas pierden ~230 px de ancho (se recuperan cerrándolo o flotándolo) |
| C | Franja bajo las gráficas | [C](opciones/opcion_c.png) | Gráficas a todo lo ancho; todos los valores en dos filas | Las gráficas pierden ~100 px de alto; la franja no admite más contenido; lejos de los parámetros |
| D | Arriba de la barra lateral | [D](opciones/opcion_d.png) | Cerca de los parámetros; sin perder sitio para las gráficas | Empuja los parámetros aún más abajo: se cambia GSI sin ver los resultados otra vez |
| E | Espejo: parámetros a la derecha, resultados a la izquierda | [E](opciones/opcion_e.png) | Propiedades a la derecha como un inspector | Rompe el hábito de RocData/RSData (materiales a la izquierda) y separa el árbol de sus parámetros |

**Recomendación: B.** Es la única que mantiene a la vista, a la vez,
los parámetros que se tocan, las gráficas y los resultados (U1, U2), y
deja un sitio natural para lo que hoy va a la barra de estado.

## Usuarios / actores

Geotécnico que ajusta parámetros y copia el material a Slip2D/FEM2D.

## Historias de usuario

- H1: Como geotécnico quiero ver los parámetros calculados mientras cambio
  GSI o mi, para entender su efecto sin desplazarme.
- H2: Como usuario diario quiero copiar el material y guardar sin buscar
  los botones.

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA mostrará los parámetros calculados del material
  activo en un panel acoplable a la derecha, visible sin desplazar a
  1366×768.
- **RF-2**: CUANDO cambie un parámetro, el material activo o el criterio,
  EL SISTEMA actualizará el panel de resultados a la vez que las gráficas.
- **RF-3**: EL SISTEMA ofrecerá en el panel de resultados el botón
  «Copiar material» (portapapeles de la spec 005).
- **RF-4**: EL SISTEMA permitirá cerrar, flotar y volver a mostrar el
  panel (View > Results) y recordará su estado entre sesiones.
- **RF-5**: EL SISTEMA agrupará la barra lateral en secciones con título,
  en este orden: materiales; material (nombre con etiqueta, criterio,
  herramientas de estimación); rango de tensiones; parámetros; rigidez.
- **RF-6**: EL SISTEMA no mostrará en la barra lateral la unidad de
  tensión, el título del proyecto ni las acciones de archivo y
  portapapeles; seguirán en sus menús y en la barra de herramientas.
- **RF-7**: EL SISTEMA tendrá una barra de herramientas con Nuevo, Abrir,
  Guardar, Deshacer, Rehacer, Copiar material, Copiar datos, Copiar
  gráfica, Calcular y el selector de unidad de tensión.
- **RF-8**: MIENTRAS un muestreador (de tensiones o MC instantáneo) esté
  activo, EL SISTEMA mostrará sus lecturas en el panel de resultados
  además de en la barra de estado.
- **RF-9**: SI el criterio del material no es Hoek-Brown generalizado,
  ENTONCES EL SISTEMA mostrará en el panel la cohesión y el ángulo de
  rozamiento Mohr-Coulomb equivalentes en el rango de σ3 cuando el núcleo
  los calcule para ese criterio, y si no, una frase que diga que ese
  criterio no tiene parámetros derivados.

## Requisitos no funcionales

- Redibujar tras editar sigue por debajo de 400 ms.
- Textos nuevos con `tr()` y español; cambio de idioma (spec 024)
  conserva la posición del panel.
- El título del proyecto y la unidad de tensión se editan en
  File > Project Settings…, como en RSData *Project Settings*; la unidad
  también en la barra de herramientas. El título sigue deshaciéndose
  (spec 023).

## UX

U1, U2, U10, U12, U16, U17. Lista de comprobación de la guía al validar.

## Casos límite

- 1280×720 y 1920×1080 con escalado 150 %.
- Criterios con muchos campos (NorSand, Softening-Hardening).
- Material sin resultados calculables (parámetros fuera de rango): el
  panel dice por qué, no se queda vacío.
- Panel cerrado: Copiar material sigue en la barra y en Edit.

## Fuera de alcance

- Reordenar los menús (025c), formato de los números (025e).
- Iconos propios: se usan los estándar de Qt.

## Criterios de finalización

- Cada RF con su test y la suite entera en verde.
- Capturas a 1366×768 en EN/ES y claro/oscuro con los resultados a la vista.

## Dudas abiertas

Ninguna: resueltas por la propietaria el 2026-11-24 («sí a todo»).

## Cambios tras la aprobación

- **RF-9** (2026-11-24, aprobado por la propietaria el mismo día): al preparar el plan se vio que
  hoy el bloque *Computed* solo tiene contenido con Hoek-Brown
  generalizado; con los otros nueve criterios queda vacío. Un panel vacío
  incumple U6. El núcleo ya calcula el MC equivalente
  (`material_results.overlay_mc`) para la familia Hoek-Brown, Power Curve
  y Barton-Bandis.
