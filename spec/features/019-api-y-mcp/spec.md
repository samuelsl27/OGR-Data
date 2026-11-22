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

- `ogr_data.api`: operaciones puros-python sobre un objeto proyecto en
  memoria (sin ventana): `material_define/material_list/material_compute/
  classify_uscs/fit/copy_material/save/load`.
- `ogr-mcp`: servidor stdio con el SDK `mcp` (extra `[mcp]`), sin
  `--attach` (no hay ventana viva que adjuntar en v1; opera sobre
  proyectos de archivo).
- Tests del servidor con el cliente de pruebas del SDK (como Slip2D).

## Criterios de aceptación

- Las mismas operaciones, llamadas desde tests, producen los mismos
  resultados que la UI (mismas funciones de núcleo, sin duplicar lógica).
- El servidor arranca y responde `server_info` con la ventana cerrada.

## Fuera de alcance

- Modo `--attach` contra una ventana viva (puente F4 de Slip2D).
- Permisos/undo transaccional (decidir en plan si se hereda el patrón).
