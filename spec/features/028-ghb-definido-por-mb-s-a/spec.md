# Spec 028 — Hoek-Brown generalizado definido por mb, s y a

> Estado: **borrador** (2026-11-24). La propietaria pidió escribirla y no
> implementarla todavía.

## Contexto y objetivo

La spec 026 (RF-9) quería que el campo «Define by» del Hoek-Brown
generalizado ofreciera, además de «GSI», la entrada directa de mb, s y a.
Se aplazó porque abre un camino de cálculo nuevo: hoy mb, s y a se
calculan siempre desde GSI, mi y D (Hoek et al. 2002, ecs. 3–5), y de esa
derivación dependen la envolvente, los resultados, el informe, el
portapapeles, la simulación de ensayos, la calibración, el σ3max por
aplicación y la API. Mientras tanto «Define by» está deshabilitado con su
motivo (regla 7).

Introducir mb, s y a directamente es útil cuando vienen de un ajuste a
ensayos del macizo, de otro programa o de la bibliografía, sin un GSI
asociado. El criterio en esa forma es el de Hoek et al. (2002), ec. 2:
σ1 = σ3 + σci (mb σ3/σci + s)^a.

## Usuarios / actores

- Geotécnico que tiene mb, s y a de un ajuste o de un informe y quiere
  usarlos tal cual.

## Historias de usuario

- H1: Como geotécnico quiero introducir mb, s y a de un macizo para
  obtener su envolvente y su Mohr-Coulomb equivalente sin inventar un GSI.
- H2: Como geotécnico quiero saber qué resultados no se pueden calcular
  sin GSI, y por qué.

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA ofrecerá en «Define by» dos opciones: «GSI» (como
  hoy) y «mb, s, a».
- **RF-2**: MIENTRAS «Define by» sea «mb, s, a», EL SISTEMA pedirá σci,
  mb, s y a, y mostrará deshabilitados, con su motivo, GSI, mi y D.
- **RF-3**: MIENTRAS «Define by» sea «GSI», EL SISTEMA mostrará
  deshabilitados mb, s y a con los valores que resultan de GSI, mi y D.
- **RF-4**: CUANDO «Define by» pase de «GSI» a «mb, s, a», EL SISTEMA
  rellenará mb, s y a con los valores calculados en ese momento, para que
  la envolvente no cambie.
- **RF-5**: MIENTRAS «Define by» sea «mb, s, a», EL SISTEMA calculará la
  envolvente, σt, σc, σcm y el Mohr-Coulomb equivalente con las
  ecuaciones de Hoek et al. (2002) a partir de mb, s y a.
- **RF-6**: SI «Define by» es «mb, s, a», ENTONCES EL SISTEMA no calculará
  Erm por los métodos que necesitan GSI y D, y dirá por qué
  [NECESITA ACLARACIÓN: ¿Erm queda sin calcular, se pide Erm directamente,
  o se deduce un GSI equivalente de s con un D supuesto?].
- **RF-7**: EL SISTEMA tratará igual los parámetros residuales: con
  «mb, s, a», mb, s y a residuales directos.
- **RF-8**: EL SISTEMA aceptará mb > 0, 0 ≤ s ≤ 1 y 0,5 ≤ a < 1 [NECESITA
  ACLARACIÓN: ¿estos límites, que salen de las ecuaciones de Hoek et al.
  2002, o otros?], y SI un valor queda fuera, ENTONCES lo dirá junto al
  campo sin calcular.
- **RF-9**: EL SISTEMA dará los mismos resultados en la ventana, el
  informe, el portapapeles, la simulación de ensayos y la API para un
  mismo material definido por mb, s y a.
- **RF-10**: CUANDO se abra un proyecto anterior a esta spec, EL SISTEMA lo
  leerá como «Define by» = «GSI», sin cambiar nada.

## Requisitos no funcionales

- Validación numérica (regla 1): con mb, s y a iguales a los que da un
  caso por GSI, todos los resultados deben coincidir con los del camino
  por GSI, que ya está validado; y contra al menos un caso publicado con
  mb, s y a directos.
- Ninguna referencia al programa de referencia (regla 9).
- Textos con `tr()` y su español; la ayuda de cada campo nuevo, con su
  fuente (spec 025f).

## UX

U2 (lo que no se usa en el modo activo, deshabilitado y explicado), U7,
U9, U11.

## Casos límite

- s = 0 (macizo sin resistencia a tracción): σt = 0.
- a = 0,5 con s = 1: debe coincidir con el Hoek-Brown clásico de roca intacta.
- Cambiar de «mb, s, a» a «GSI»: vuelven los valores calculados desde GSI
  (lo introducido a mano se pierde, o se pregunta: [NECESITA ACLARACIÓN]).
- Calibración y ajuste que producen un material GHB: siguen produciéndolo
  por GSI.

## Fuera de alcance

- Otras opciones de «Define by» sin descripción documentada.
- Cambios en los métodos de Erm.

## Criterios de finalización

Cada RF con su test, incluida la coincidencia con el camino por GSI;
proyectos antiguos que abren igual; suite en verde.

## Dudas abiertas

- [NECESITA ACLARACIÓN: qué hacer con Erm sin GSI (RF-6)]
- [NECESITA ACLARACIÓN: límites de mb, s y a (RF-8)]
- [NECESITA ACLARACIÓN: qué pasa con los valores manuales al volver a «GSI»]
- [NECESITA ACLARACIÓN: un caso publicado con mb, s y a directos para validar]




Cuando quieras implementarla, me hacen falta cuatro respuestas:

Erm sin GSI: los métodos de Erm necesitan GSI y D. ¿Lo dejo sin calcular (con su motivo), te pido Erm directamente, o deduzco un GSI equivalente a partir de s con un D supuesto?
Límites: propongo mb > 0, 0 ≤ s ≤ 1 y 0,5 ≤ a < 1, que salen de las ecuaciones de Hoek et al. (2002). ¿Te valen?
Al volver a "GSI": ¿se pierden los valores que se escribieron a mano, o el programa pregunta antes?
Caso para validar: ¿tienes algún caso publicado con mb, s y a directos?