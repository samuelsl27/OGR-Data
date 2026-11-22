# Roadmap de OGR-Data

Orden propuesto (cada entrada será una spec en `../features/`):

1. **001 — Calculadora GHB/Hoek-Brown** (núcleo): entrada σci, mi, GSI, D,
   Ei; salida mb/s/a, sigt, sigc, sigcm, MC equivalente (c, φ) por rango
   (custom/túnel/talud), Em (Hoek-Diederichs 2006 y Hoek 2002). Equivalente
   ORMAS validado contra sus resultados. Con gráficas σ1–σ3 y τ–σn.
2. **002 — Criterios MC, Barton-Bandis y Power Curve** con parámetros
   interactivos y envolventes, como el viejo RocData.
3. **003 — Pick dialogs bibliográficos**: tablas por tipo de roca (Hoek ch.11)
   y carta GSI (Marinos-Hoek 2000, incl. flysch).
4. **004 — Clasificador de suelos USCS** (ASTM D2487 vía NRCS 631-3) con
   ficha de propiedades típicas y creación de material.
5. **005 — Portapapeles**: contrato `OGR-DATA-MATERIAL/1` (copiar/pegar con
   OGR-Slip2D y OGR-FEM2D) + copia tabulada para Excel + imagen de gráficas.
6. **006 — Ajuste a datos de ensayo**: triaxial y corte directo,
   Levenberg-Marquardt/Simplex/regresión; residuals; equivalencia MC.
7. **007 — Base de datos de materiales** persistida (proyectos OGR-Data,
   importación de .roc del viejo RocData).
8. Posibles fases 2: muestreadores (stress / instantaneous MC), línea de
   Mogi, export Excel, informes.
