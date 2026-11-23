---
name: ux-review
description: Revisa una pantalla, diálogo o flujo de OGR-Data contra la guía de UX de la constitución (Laws of UX, Fluent 2, Checklist Design, Autodesk HIG, Humane by Design, Growth.Design, GoodUI, Deceptive Design). Úsala cuando se pida revisar la interfaz o la usabilidad. Devuelve hallazgos con evidencia, no arreglos.
argument-hint: "<ventana, diálogo o flujo; vacío = toda la interfaz>"
---

# Revisión de UX

1. Lee `spec/constitution/ux-guidelines.md` (reglas U1–U17 y patrones
   prohibidos) y el código de la pantalla en `ogr_data/gui/`.
2. **Mira la interfaz de verdad**: captura offscreen con un script en el
   scratchpad (`QT_QPA_PLATFORM=offscreen`,
   `QT_QPA_FONTDIR=C:/Windows/Fonts`, `widget.grab().save(...)`), a
   1366×768, en inglés y español y en los dos temas. Abre los diálogos con
   `show()`, nunca con `exec()`.
3. Para cada hallazgo: regla U-n (y la ley o fuente), dónde
   (`archivo:línea` o pantalla), evidencia (qué se ve, medida si la hay),
   impacto y prioridad:
   - **P0** bug visible (texto interno en pantalla, control roto, tema a medias);
   - **P1** bloquea o confunde el flujo principal;
   - **P2** fricción o incoherencia;
   - **P3** pulido.
4. Separa lo que es bug (regla 6: se reporta antes de corregir) de lo que
   es mejora (necesita spec).
5. No cambies código. Si se pide convertir los hallazgos en trabajo, usa
   `/sdd-spec` con ellos como requisitos.
