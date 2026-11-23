# Misión

OGR-Data es el programa de la suite OpenGeoRock para **obtener, ajustar y
transferir las propiedades geomecánicas de los materiales** (suelos y masas
de roca) que usan OGR-Slip2D y OGR-FEM2D.

Hereda el espíritu del antiguo RocData de Rocscience (2004): una herramienta
simple e interactiva donde cambiar un parámetro actualiza al instante las
envolventes de resistencia, con estimación de parámetros desde tablas
bibliográficas y ajuste de datos de ensayo. Añade lo que el usuario valora
del RSData actual (modelos avanzados, clasificación de suelos) sin su
complejidad de interfaz.

## Objetivos

1. **Calculadora de resistencia**: los diez criterios observados en RSData —
   Mohr-Coulomb, Hoek-Brown, Drucker-Prager, Generalized Hoek-Brown,
   Cam-Clay, Modified Cam-Clay, Softening-Hardening, NorSand, Power Curve y
   Barton-Bandis — con parámetros MC equivalentes sobre un rango de tensión
   elegido por aplicación (túnel/talud/personalizado).
2. **Parámetros de masa de roca**: mb, s, a; sigt, sigc, sigcm; módulo Em
   con los métodos Hoek-Diederichs 2006 y Hoek 2002 (como ORMAS).
3. **Estimación bibliográfica**: diálogos "Pick" con valores típicos por
   tipo de roca (sigci, mi, GSI — Hoek) y por clase de suelo (USCS — NRCS).
4. **Clasificación de suelos** USCS (ASTM D2487) a partir de granulometría
   y Atterberg, con propuesta de parámetros.
5. **Ajuste a datos de ensayo** (fase 2): triaxial y corte directo, con
   Levenberg-Marquardt/Simplex/regresión.
6. **Transferencia por portapapeles** a OGR-Slip2D y OGR-FEM2D mediante un
   contrato abierto y documentado.

## No objetivos (de momento)

- Integración con el formato privado de portapapeles de Rocscience.

Los otros dos no objetivos del arranque —simulación de ensayos y estados
de fallo, rutas y calibración— pasaron a objetivos con las specs 012,
013, 014 y 021 (ver `roadmap.md`).

## Principios y UX

Los principios innegociables están en [`principles.md`](principles.md) y
la guía de interfaz en [`ux-guidelines.md`](ux-guidelines.md).
