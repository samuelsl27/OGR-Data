# Roadmap de OGR-Data

Hecho (specs 001–007, desarrolladas): calculadora GHB validada contra
ORMAS · los 10 criterios de RSData · pick dialogs Hoek/GSI · clasificador
USCS · contrato de portapapeles · ajuste a datos de ensayo · proyectos
e importación `.roc`. Después: 020 (línea de diseño), 008, 009, 017,
016, 011 (proyectos multi-material, formato `.ogrdata` v2) y 012
(estados de fallo y rutas de tensión, con la pestaña Stress Path
Graphs) y **021** (estados y rutas verificados en la interfaz de RSData
1.009).

**Siguiente propuesta: 022 — Estimación sin ensayos** (selectores
visibles de σci, GSI con clic sobre la carta y calculadora, mi con
filtros, D, Ei/MR y método de Erm): requisito clave del propietario
(`Referencias/Ejemplos/RSData_analisis/08_estimacion_sin_ensayos.md`).
Después 014 (calibración, opciones ya verificadas).

Backlog de specs (spec.md redactadas; plan y tasks se hacen al
desarrollar cada una). Orden propuesto tras la evaluación en profundidad
de RSData 1.009 y ORMAS V2.0 (`../../Referencias/Ejemplos/RSData_analisis/05_profundizacion.md`):

1. **008 — Muestreadores y superposiciones**: stress sampler,
   instantaneous MC sampler, overlay MC, línea de Mogi. (Chico, alto
   valor, completa la paridad con el viejo RocData.)
2. **009 — σ3max por aplicación** (túnel/talud): extraer fórmulas de
   Hoek 2002 §6 / Marinos-Hoek §2.2 y validar contra ORMAS.
3. **017 — Unidades y settings** (kPa/MPa en toda la UI).
4. **016 — Opciones de gráfica y exportación** (graph editor, guardar
   imagen, export CSV para Excel, zoom extents).
5. **011 — Proyectos multi-material** (contenedor de las siguientes).
6. **012 — Failure states y stress paths** (puntos pico/residual, rutas).
7. **014 — Calibración** multi-estado (sobre 006 + 011 + 012).
8. **010 — Base de datos de materiales** (equivalente RocProp, datos
   propios de bibliografía oficial).
9. **018 — Pick dialogs avanzados** (Barton, c/φ USCS numéricos con
   fuente oficial, factor D).
10. **015 — Informes** (HTML autocontenido).
11. **013 — Simulación de ensayos** (faseada 13a elastoplástica básica,
    13b modelos avanzados, 13c cíclicos/animación). La más grande.
12. **019 — API de operaciones y servidor MCP** (patrón de la suite).

Otras ideas registradas sin spec aún: undo/redo, i18n (la suite programa
en inglés; decidir idioma de UI), export PDF nativo, unidades
imperiales, σ3max "General" = σci/4 como opción más del selector.
