---
name: sdd-plan
description: Escribe el plan técnico de una spec aprobada de OGR-Data (fase 3 del flujo SDD). Úsala cuando la spec esté aprobada y se pida planificar o decidir cómo implementarla. Produce plan.md sin código.
argument-hint: "<NNN de la spec>"
---

# Plan (cómo)

Requisito: la spec está **aprobada** (si no, para y dilo).

1. Lee `AGENTS.md`, `spec/constitution/`, la spec y el código de las capas
   afectadas (`core`, `api`, `gui`, `mcp_server`, `i18n`).
2. Escribe `spec/features/<NNN>-*/plan.md` con la plantilla de
   `spec/features/000-plantilla/plan.md`. **Sin código.** Cada apartado
   dice qué RF cubre.
3. Cada decisión lleva la alternativa descartada y el porqué.
4. Respeta las capas `core → api → {gui, mcp_server}`: el núcleo no
   importa Qt; una regla nueva va al núcleo y la ventana la pregunta.
5. **Validación numérica**: nombra la referencia externa de cada fórmula
   y la tolerancia. Sin referencia, márcalo como riesgo y pregunta.
6. Si toca la interfaz: cómo cumple cada regla UX de la spec, qué textos
   nuevos van a `gui/i18n/es_*.py` y cómo se prueban idioma y tema.
7. Pide aprobación. No escribas tareas ni código sin ella.
