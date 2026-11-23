# Tasks 012 — Estados de fallo y rutas de tensión

- [x] Spec 012 (plan.md, tasks.md; spec.md sin cambios)
- [x] core/states.py: FailureState, StressPath, círculo de Mohr, ruta en
      σ1–σ3, parser de tablas y CSV
- [x] Material con estados y rutas (persistencia v2 aditiva, plantillas
      Rock/Soil, duplicar)
- [x] Diálogos Define Failure States / Define Stress Paths con tablas
      (cortar/copiar/pegar/insertar/borrar/importar/exportar)
- [x] Árbol con hijos, menús Failure States / Stress Paths, menú contextual
- [x] Dibujo: puntos y círculos de Mohr (RocData guide pp. 13, 47-48),
      rutas como polilíneas, leyenda, export CSV
- [x] Diálogo de ajuste (006) con el parser común
- [x] tests/test_states.py; suite en verde; commit y push
- [x] Segunda iteración: fuentes guardadas (ayuda RSData, Machaček 2023,
      UTM); pestaña Stress Path Graphs; rutas en τ–σn; campos y defectos
      oficiales de RSData en el diálogo de rutas
- [ ] Verificación en RSData de columnas y semántica de Loading Direction
      → spec 021 (prompt de Claude Desktop)
