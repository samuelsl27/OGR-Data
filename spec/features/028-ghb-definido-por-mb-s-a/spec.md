# Spec 028 — Hoek-Brown generalizado definido por mb, s y a

> Estado: **aprobada** (2026-11-28). Borrador del 2026-11-24; dudas
> resueltas y spec aprobada por la propietaria el 2026-11-28.

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
- H3: Como geotécnico quiero dar Erm a mano o, si lo prefiero, deducir el
  GSI equivalente de mb, s y a para usar los métodos de Erm.

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
- **RF-6**: MIENTRAS «Define by» sea «mb, s, a», EL SISTEMA pedirá Erm a
  mano en lugar de calcularlo por los métodos que necesitan GSI y D; SI el
  campo está vacío, ENTONCES mostrará Erm «sin calcular» con su motivo.
- **RF-6b**: CUANDO el usuario pulse «Deducir GSI equivalente», EL SISTEMA
  despejará GSI de a (ec. 5), D de s y GSI (ec. 4) y mi de mb, GSI y D
  (ec. 3) de Hoek et al. (2002), los escribirá en sus campos y pasará
  «Define by» a «GSI», sin que cambie la envolvente; la acción se podrá
  deshacer y tendrá su entrada en un menú (regla 3).
- **RF-6c**: SI el D deducido queda fuera de 0 ≤ D ≤ 1, o a = 0,5 hace que
  GSI no se pueda despejar con sentido, ENTONCES EL SISTEMA no deducirá
  nada y dirá por qué junto al botón.
- **RF-7**: EL SISTEMA tratará igual los parámetros residuales: con
  «mb, s, a», mb, s y a residuales directos.
- **RF-8**: EL SISTEMA aceptará mb > 0, 0 ≤ s ≤ 1 y
  0,5 ≤ a ≤ 1/2 + (1 − e^(−20/3))/6 ≈ 0,6665, el recorrido que dan las
  ecuaciones 3–5 de Hoek et al. (2002) para GSI entre 100 y 0; SI un
  valor queda fuera, ENTONCES lo dirá junto al campo y no calculará.
- **RF-9**: EL SISTEMA dará los mismos resultados en la ventana, el
  informe, el portapapeles, la simulación de ensayos y la API para un
  mismo material definido por mb, s y a.
- **RF-10**: CUANDO se abra un proyecto anterior a esta spec, EL SISTEMA lo
  leerá como «Define by» = «GSI», sin cambiar nada.
- **RF-11**: CUANDO «Define by» vuelva de «mb, s, a» a «GSI», EL SISTEMA
  conservará en el material (y en el proyecto guardado) los mb, s, a y Erm
  escritos a mano, y los repondrá si se vuelve a «mb, s, a»; no preguntará
  nada (U5: el cambio se deshace).

## Requisitos no funcionales

- Validación numérica (regla 1), contra:
  1. **Caso publicado con m y s directos**: ensayos triaxiales de Jaeger
     sobre andesita muy diaclasada de Bougainville, recogidos en FHWA
     (1989) *Rock Slopes: Design, Excavation, Stabilization*
     (FHWA-TS-89-045), p. 5.27: σci = 265,5 MPa, m = 0,277, s = 0,0002,
     a = 0,5 (ajuste por regresión, r = 0,99). La envolvente debe quedar
     dentro del 10 % de los σ1 medidos con σ3 ≥ 0,35 MPa (6 ensayos; el
     error del ajuste publicado llega al 9,7 %). El ensayo con σ3 = 0
     (σ1 = 1,24 MPa) no lo reproduce ni la regresión publicada (3,75 MPa) y
     se excluye, diciéndolo en el test.
  2. **Soluciones cerradas** de Hoek et al. (2002) con a ≠ 0,5: σc (ec. 6),
     σt (ec. 7) y σcm (ec. 17), calculadas aparte en el test.
  3. **Coincidencia con el camino por GSI** (ya validado): el ejemplo de
     Hoek et al. (2002, § 7: σci = 50 MPa, mi = 10, GSI = 45, D = 0) da los
     mismos resultados por las dos vías, y «Deducir GSI equivalente» devuelve
     GSI = 45, mi = 10 y D = 0.
- Formato `.ogrdata`: guarda «Define by», los mb, s, a y Erm manuales; se
  actualizan antes las specs 007/011 y los ficheros viejos siguen abriendo
  (RF-10). Portapapeles (spec 005): sin cambio de contrato; se comprueba
  qué copia con «mb, s, a».
- Ninguna referencia al programa de referencia (regla 9).
- Textos con `tr()` y su español; la ayuda de cada campo nuevo, con su
  fuente (spec 025f).

## UX

U2 (lo que no se usa en el modo activo, deshabilitado y explicado), U5
(volver a «GSI» no pierde nada y se deshace), U7, U9, U11.

## Casos límite

- s = 0 (macizo sin resistencia a tracción): σt = 0.
- a = 0,5 con s = 1: debe coincidir con el Hoek-Brown clásico de roca intacta.
- Cambiar de «mb, s, a» a «GSI»: vuelven los valores calculados desde GSI;
  lo escrito a mano se conserva para cuando se vuelva (RF-11).
- a muy cerca de 0,5: GSI deducido muy sensible (cerca de 100); con
  a = 0,5 exacto, GSI = 100 y s debe ser 1 para que D tenga sentido.
- Calibración y ajuste que producen un material GHB: siguen produciéndolo
  por GSI.

## Fuera de alcance

- Otras opciones de «Define by» sin descripción documentada.
- Cambios en los métodos de Erm.

## Criterios de finalización

Cada RF con su test, incluida la coincidencia con el camino por GSI;
proyectos antiguos que abren igual; suite en verde.

## Dudas abiertas

Resueltas el 2026-11-28:

- Erm sin GSI: se pide a mano, con un botón para deducir el GSI
  equivalente que rellena GSI, mi y D y pasa a «GSI» (RF-6, RF-6b, RF-6c).
- Límites: los de Hoek et al. (2002) (RF-8).
- Volver a «GSI»: los valores manuales se conservan y vuelven (RF-11).
- Caso para validar: FHWA (1989), datos de Jaeger, más las soluciones
  cerradas y la coincidencia con el camino por GSI (requisitos no
  funcionales).
