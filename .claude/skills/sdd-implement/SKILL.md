---
name: sdd-implement
description: Implementa UNA tarea de un tasks.md aprobado de OGR-Data (fase 5 del flujo SDD), con tests primero, y para. Úsala cuando se pida implementar la tarea Tn de una spec.
argument-hint: "<NNN> <Tn>"
---

# Implementar una tarea

1. Lee `AGENTS.md`, la spec, el plan y `tasks.md`. Si la tarea no existe,
   no está aprobada o depende de una sin hacer, para y dilo.
2. Implementa **solo** esa tarea. Si descubres que hace falta algo que no
   está en la spec, para y pregunta (cambio = primero la spec).
3. **Tests primero**: escribe el test del RF (en la capa más baja que
   tenga la regla: `core` o `api` sin Qt; la ventana solo si es de la
   ventana), compruébalo en rojo, luego el código.
4. Cumple las reglas de `AGENTS.md`: `tr()` y español para todo texto
   visible, acción alcanzable desde un menú, SPDX en archivos nuevos,
   estado global restaurado en los tests, ninguna opción que no mueva el
   número, guía de UX.
5. Ejecuta la suite entera:
   `QT_QPA_PLATFORM=offscreen .venv/Scripts/python tests/_runner.py`.
   Prohibido seguir en rojo.
6. Marca `[x]` la tarea en `tasks.md`.
7. Responde: qué cambiaste, qué RF cubre, el resultado de la suite
   (`Passed: N  Failed: 0`) y qué falta por probar. **Para.** No empieces
   la siguiente tarea. Sin commit salvo que se pida.

Si algo existente parece un bug, repórtalo con evidencia antes de
corregirlo (regla 6).
