# Tareas 025b — Ventana principal: resultados a la vista

En orden de dependencia. Tests primero; suite entera en verde al cerrar
cada tarea; una tarea cada vez.

- [x] **T1** `QSettings` aislado en los tests: `gui/settings.py` (`app_settings()`), la ventana y `__main__` lo usan, el runner lo apunta a una carpeta temporal — RF-4 (base)
  - Hecho cuando: un test comprueba que el fichero de ajustes de la suite está en la carpeta temporal y la suite no toca `HKCU\Software\OpenGeoRock\OGR-Data`.
  - Hecho el 2026-11-24: `tests/test_ux_025b.py` (3 tests); suite 227/0. Comprobado a mano: con `theme = dark` puesto en el registro, la suite entera lo deja en `dark` (sin aislar, `test_theme.py` lo escribía a `light` al terminar).
- [ ] **T2** Acciones como atributos (`_new_act`, `_open_act`, `_save_act`, `_copy_*_act`, `_compute_act`) sin cambiar los menús — RF-7 (base)
  - Hecho cuando: los tests de menús existentes siguen en verde y las acciones se alcanzan por atributo.
- [ ] **T3** `ResultsPanel` en un dock a la derecha, rellenado desde `_redraw`; `results_text()`; botón Copiar material — RF-1, RF-2, RF-3
  - Hecho cuando: tests de RF-1…3 en verde y los que leían `_outputs.text()` leen el panel.
- [ ] **T4** RF-9: MC equivalente o mensaje para los criterios que no son GHB — RF-9
  - Hecho cuando: test de Mohr-Coulomb (mensaje) y Power Curve (c, φ = `overlay_mc`).
- [ ] **T5** Muestreador en el panel y en la barra de estado — RF-8
  - Hecho cuando: test de RF-8 y `test_samplers.py` en verde.
- [ ] **T6** *Project Settings* (título y unidad) y `set_project_title`; fuera `_title_edit` — RF-6
  - Hecho cuando: test del diálogo y del paso de deshacer; los 5 archivos de test migrados.
- [ ] **T7** Barra de herramientas con las mismas acciones y el selector de unidad — RF-7
  - Hecho cuando: test de RF-7.
- [ ] **T8** Barra lateral por secciones; fuera unidad, título, archivo y portapapeles — RF-5, RF-6
  - Hecho cuando: test de RF-5/RF-6; captura a 1366×768.
- [ ] **T9** Estado del panel y de la barra en `QSettings` y a través del cambio de idioma; View > Results panel / Toolbar — RF-4
  - Hecho cuando: test de RF-4 (cerrar y abrir, cambio de idioma).
- [ ] **T10** Textos en español y revisión de `test_i18n.py` — todos
  - Hecho cuando: `test_i18n.py` en verde.
- [ ] **T11** Validación final — todos los RF
  - Hecho cuando: cada RF con su test, lista UX de la guía marcada con capturas EN/ES y claro/oscuro a 1366×768 y 1280×720, suite entera en verde.
