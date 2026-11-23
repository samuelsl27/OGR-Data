# Spec 019 — Capa de operaciones y servidor MCP

## Qué se construye

El equivalente OGR-Data del patrón `ogr_api` + `ogr_mcp` de OGR-Slip2D
(spec 008 de Slip2D): una capa de operaciones con nombre, sin Qt, que
manejen el programa por las mismas operaciones que la UI (definir
materiales, clasificar suelos, ajustar, calcular envolventes, copiar al
portapapeles), y un servidor MCP (extra opcional `[mcp]`, SDK MIT) para
que los agentes de IA operen el programa.

## Motivación

La suite entera sigue esta arquitectura (constitution de Slip2D:
"Un agente de IA, un script y el puente con la interfaz manejan el
programa por las MISMAS operaciones con nombre"). OGR-Data nació como
calculadora personal, pero encaja en la suite y la usuaria ya opera con
agentes.

## Alcance v1

Revisado al desarrollarla (23-11-2026): el alcance original es anterior a
las specs 012–022 y se amplía a lo que el programa hace hoy.

- `ogr_data.api`: operaciones puro-python sobre proyectos en memoria (sin
  ventana), con handles `project_id`, validación con sugerencias y
  errores con código (patrón de `ogr_api` de Slip2D). Grupos: proyecto
  (`.ogrdata`), materiales (definir, calcular, copiar/pegar con el
  contrato de portapapeles, importar `.roc`), datos (estados de fallo,
  rutas de tensión, ajuste a datos, calibración), simulación de ensayos,
  estimación sin ensayos (GSI cuantificado y por carta digitalizada,
  tablas, USCS, Barton), base de datos de materiales, salidas (PNG de la
  envolvente e informe HTML).
- Unidades de la API, de entrada y salida: kPa, kN/m3, m, grados.
- `ogr-data-mcp` (no `ogr-mcp`, para no chocar con el de Slip2D):
  servidor stdio con el SDK `mcp` (extra `[mcp]`), una herramienta por
  operación más `server_info`, y la guía como recurso
  `ogr-data://guide`. Sin `--attach` (no hay ventana viva que adjuntar).
- Lógica que vivía en la ventana (σ3max por aplicación, valores
  calculados del portapapeles, MC equivalente, aplicar un ajuste,
  materiales creados desde USCS / base de datos / calibración) pasa al
  núcleo (`core/material_results.py`, `core/material_factory.py`) para
  que ventana y API usen las mismas funciones.
- Tests del servidor con el cliente en memoria del SDK (como Slip2D).

## Criterios de aceptación

- Las mismas operaciones, llamadas desde tests, producen los mismos
  resultados que la UI (mismas funciones de núcleo, sin duplicar lógica).
- El servidor arranca y responde `server_info` con la ventana cerrada.
- El caso ORMAS (GHB por defecto) da por la API y por el protocolo MCP
  los mismos c, φ, Erm y σ3max de túnel/talud que la ventana.

## Fuera de alcance

- Modo `--attach` contra una ventana viva (puente F4 de Slip2D).
- Permisos/undo transaccional (decidir en plan si se hereda el patrón).
