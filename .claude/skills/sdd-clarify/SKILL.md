---
name: sdd-clarify
description: Revisa como QA una spec de OGR-Data antes del plan (fase 2 del flujo SDD). Úsala cuando se pida revisar, clarificar o auditar un spec.md. Solo detecta problemas; no propone soluciones ni reescribe.
argument-hint: "<NNN de la spec>"
---

# Clarificación

Lee `AGENTS.md`, `spec/constitution/` y `spec/features/<NNN>-*/spec.md`.
No reescribas la spec. Devuelve cuatro bloques numerados:

1. **Ambigüedades**: requisitos con más de una lectura, adjetivos sin
   medida, términos sin definir (¿qué unidad?, ¿qué tensión?).
2. **Contradicciones**: entre RF, con otras specs o con el código actual.
3. **Casos límite sin cubrir**: valores cero/negativos/extremos, material
   sin datos, idioma español, tema oscuro, ficheros antiguos, API/MCP.
4. **Choques con la constitución**: principios, guía de UX (U1–U17),
   reglas de `AGENTS.md`, referencia numérica ausente.

Cada punto cita el RF o la sección. **No propongas soluciones** hasta que
te las pidan. Después, con las respuestas de la propietaria, actualiza
`spec.md` (quitando los `[NECESITA ACLARACIÓN]` resueltos), enseña el diff
y espera la aprobación.
