# Plan NNN — <Nombre de la funcionalidad>

Sin código. Cada apartado dice qué RF cubre.

## Decisiones

| Decisión | Alternativa descartada y por qué | RF |
|---|---|---|
| … | … | RF-1 |

## Capas y archivos

Respetando `core → api → {gui, mcp_server}` (el núcleo no importa Qt):

- `ogr_data/core/…` — …
- `ogr_data/api/ops/…` — operación nueva o cambiada (si aplica)
- `ogr_data/gui/…` — …
- `ogr_data/gui/i18n/es_….py` — textos nuevos

## Modelo de datos

Cambios en `.ogrdata`, portapapeles o tablas de `ogr_data/data/`, con
ejemplo y compatibilidad con ficheros antiguos.

## Validación numérica

Contra qué referencia externa se comprueba cada fórmula (publicación,
solución cerrada, ORMAS, el programa de referencia) y con qué tolerancia.

## Estrategia de tests

- Núcleo/API (sin Qt): …
- Ventana (offscreen): …
- Idioma y tema: …

## Riesgos

- …
