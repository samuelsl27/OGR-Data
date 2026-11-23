# Stack y convenciones

Decisiones estructurales iniciales (pendientes de ratificación por el
propietario — ver `../../Promps/`):

| Decisión | Motivo |
|---|---|
| **Python 3.11+**, sin Rust | La app no ejecuta cálculos pesados; los ajustes son regresiones pequeñas (scipy basta). |
| **PySide6 (Qt 6)** | Misma pila que OGR-Slip2D: línea de diseño continuista y personal cualificada. |
| **No depende de ogr-core (standalone)** | OGR-Data no maneja geometría ni proyectos del núcleo; sus materiales viven en su propio esquema y se transfieren por portapapeles. Se revisa si en el futuro Slip2D/FEM2D quieren compartir el esquema de materiales a través del core. |
| **Cálculo núcleo sin Qt** | Módulo puro `ogr_data.core` (o similar) con los criterios, equivalentes MC y ajustes: testeable y reusable. |
| **Gráficas** | matplotlib embebido en Qt (decisión del propietario, 2026-11-22), estilo OGR-Slip2D. |
| **Portapapeles** | Contrato abierto documentado (prefijo `OGR-DATA-MATERIAL:` + JSON), ver análisis en `../../Referencias/Ejemplos/RSData_analisis/04_integracion.md`. |
| **Datos bibliográficos** | Tablas en JSON/CSV versionados dentro del repo, con cita de fuente por fila (NRCS, Hoek). |
| **Idioma** | Código y docs del repo en inglés (regla de la suite); notas privadas en español. |
| **Licencia** | AGPL-3.0-or-later, como los demás programas. |
| **Metodología SDD** (github.com/mouredev/hello-sdd) | Igual que el resto de la suite: spec/constitution + spec/features (spec.md, plan.md, tasks.md). Contrato con agentes en `AGENTS.md` (`CLAUDE.md` lo importa); fases como *skills* en `.claude/skills/` (2026-11-24). |

## Separaciones que no deben romperse

- **Cálculo ↔ interfaz**: el núcleo no conoce Qt, unidades de usuario ni
  idiomas.
- **Aplicación ↔ transferencia**: el contrato de portapapeles es un módulo
  aparte con su spec propia; Slip2D/FEM2D consumirán el mismo contrato.
