# Roadmap de OGR-Data

Hecho (specs 001–007, desarrolladas): calculadora GHB validada contra
ORMAS · los 10 criterios del programa de referencia · pick dialogs Hoek/GSI · clasificador
USCS · contrato de portapapeles · ajuste a datos de ensayo · proyectos
e importación `.roc`. Después: 020 (línea de diseño), 008, 009, 017,
016, 011 (proyectos multi-material, formato `.ogrdata` v2) y 012
(estados de fallo y rutas de tensión, con la pestaña Stress Path
Graphs) y **021** (estados y rutas verificados en la interfaz del programa de referencia
1.009).

**022 — Estimación sin ensayos** hecha (selectores de un clic: σci, GSI
con carta cuantificada 2013 y calculadora, mi con filtros, D, Ei/MR y
método de Erm; y las cartas digitalizadas con clic: general 2000,
flysch 2000 y heterogénea de V. Marinos 2007, con textos EN/ES).
**014 — Calibración** hecha (varios estados, MC/GHB/Power Curve/
Barton-Bandis, lab o macizo, LR/LM/Simplex, error absoluto/relativo;
contrastada con el programa de referencia) y **010 — Base de datos de materiales** (al estilo de la base de datos de referencia, 150 registros con fuente: tablas de Hoek, CANMET 1995 y MnDOT
2018; favoritos, CSV, PDF, probetas → estado de fallo) y **018 — Pick
dialogs avanzados** (φr, JRC y JCS de Barton-Bandis con corrección de
escala; c/φ numéricos por grupo USCS de UFC 3-220-01N, y el clasificador
crea el material; perfiles de JRC pendientes por copyright) y **015 —
Informes** (Report Generator / Add View To Report / Manage Report View:
HTML autocontenido con las secciones del programa de referencia, vistas de gráficas con
parámetros y resultados, secciones vacías omitidas). **013a —
Simulación de ensayos** hecha (Tests / Compute: uniaxial, triaxial y
biaxial, drenado/no drenado, compresión/extensión, cíclico básico;
elastoplástico MC/HB/GHB con residual frágil; rigidez lineal isótropa;
verificado contra soluciones cerradas) y **013b** (Drucker-Prager,
Cam-Clay/MCC, Softening-Hardening, cortes a tracción y Simple Shear,
contrastados con los manuales del programa de elementos finitos de referencia y del programa de referencia; NorSand y General Test
sin fuente), completada después con NorSand (FLAC3D + Nova, contrastado
con el tutorial del programa de referencia), General Test, casquetes y tablas de
Softening-Hardening, los campos reales del diálogo (σ'h0, K0) y **013c**
(animación). **019 — API y MCP** hecha (`ogr_data.api`, 36
operaciones sin Qt con las mismas funciones de núcleo que la ventana, y
`ogr-data-mcp` por stdio, extra `[mcp]`). Con ella se cierra el backlog
de specs; quedan pendientes menores dentro de 010, 012/021, 013, 014,
015 y 018 (ver sus tasks).

Backlog de specs (spec.md redactadas; plan y tasks se hacen al
desarrollar cada una). Orden propuesto tras la evaluación en profundidad
del programa de referencia y ORMAS V2.0 (`05_profundizacion.md`, en el análisis privado del programa de referencia en `../../Referencias/Ejemplos/`):

1. **008 — Muestreadores y superposiciones**: stress sampler,
   instantaneous MC sampler, overlay MC, línea de Mogi. (Chico, alto
   valor, completa la paridad con el programa de referencia antiguo.)
2. **009 — σ3max por aplicación** (túnel/talud): extraer fórmulas de
   Hoek 2002 §6 / Marinos-Hoek §2.2 y validar contra ORMAS.
3. **017 — Unidades y settings** (kPa/MPa en toda la UI).
4. **016 — Opciones de gráfica y exportación** (graph editor, guardar
   imagen, export CSV para Excel, zoom extents).
5. **011 — Proyectos multi-material** (contenedor de las siguientes).
6. **012 — Failure states y stress paths** (puntos pico/residual, rutas).
7. **014 — Calibración** multi-estado (sobre 006 + 011 + 012).
8. **010 — Base de datos de materiales** (equivalente a la base de datos de referencia, datos
   propios de bibliografía oficial).
9. **018 — Pick dialogs avanzados** (Barton, c/φ USCS numéricos con
   fuente oficial, factor D).
10. **015 — Informes** (HTML autocontenido).
11. **013 — Simulación de ensayos** (faseada 13a elastoplástica básica,
    13b modelos avanzados, 13c cíclicos/animación). La más grande.
12. **019 — API de operaciones y servidor MCP** (patrón de la suite).

Siguientes (spec.md redactadas el 23-11-2026; plan y tasks al desarrollarlas):

13. **023 — Deshacer y rehacer** (hecha): historial de ediciones del
    proyecto en `core/history.py` (instantáneas comparadas; el texto del
    paso se deduce del cambio), Edit > Undo/Redo con atajos, asterisco y
    Guardar / Descartar / Cancelar; en la API, un paso por operación que
    edita y `project_history`. Requisito del modo `--attach` del servidor
    MCP.
14. **024 — Interfaz en inglés y español** (hecha): View > Language
    (la ventana se reabre en el idioma sin perder nada), toda la ventana,
    los diálogos y el informe HTML en español; código, API, MCP y
    ficheros siguen en inglés; contenido bibliográfico en su idioma.

Siguientes (24-11-2026):

15. **025 — Revisión de UX**: la
    [revisión](../features/025-revision-ux/revision.md) de toda la
    interfaz contra la nueva [guía de UX](ux-guidelines.md), en seis
    specs ([índice](../features/025-revision-ux/README.md)): **025a**
    errores visibles (hecha), **025b** ventana principal con los
    resultados en un panel a la derecha (hecha), **025c**
    menús y convenciones (hecha), **025d** estados vacíos y confirmaciones (hecha),
    **025e** notación, decimales y unidades (hecha), **025f** ayuda,
    accesibilidad y progreso (hechas todas; las fuentes que faltan para
    la ayuda de parámetros, en `025f-.../fuentes-pendientes.md`).

16. **026 — Anomalías de los parámetros** (hecha, salvo «Define by: mb, s, a», aplazada): valores
    por defecto fuera de rango (N de NorSand, JCS), Power Curve que ignora
    c y la ondulación, unidades de *a*, y 13 campos que ningún cálculo lee
    (regla 7).
17. **027 — Retirar las referencias al fabricante del programa de
    referencia** (hecha): regla 9 de `AGENTS.md`, con test.
18. **028 — Hoek-Brown generalizado definido por mb, s y a** (aprobada el
    2026-11-28, en curso): la opción aplazada de la spec 026; Erm a mano o
    por GSI equivalente deducido, límites de Hoek et al. (2002).
19. **029 — Panel lateral legible y adaptable** (hecha): campos
    numéricos aplastados, flechas que tapan el número y panel de ancho
    fijo; revisión de UX del 2026-11-28.

Otras ideas registradas sin spec aún: export PDF nativo, unidades
imperiales, σ3max "General" = σci/4 como opción más del selector.
