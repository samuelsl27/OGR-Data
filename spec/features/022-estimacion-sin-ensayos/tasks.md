# Tasks 022 — Estimación sin ensayos

- [x] Fuentes: paper 2013 (Bibliografia/General), PRE 2023 figs. 9 y 13
- [x] Datos con fuente: gsi_quantified, modulus_ratio, disturbance_factor
- [x] core/gsi.py (ecs. 1-6, valoraciones de la tabla 1, carta)
- [x] Registro GHB: Ei (pick MR) y método de Erm; pick de D
- [x] GSI: carta 2000 + carta cuantificada 2013 con clic + calculadora 2013
- [x] mi con filtros; D por aplicación; Ei = MR·σci
- [x] Picks de un clic y en la unidad de visualización (fallo de σci en MPa)
- [x] tests/test_estimation.py; suite en verde; commit y push
- [x] Cartas digitalizadas con clic (general 2000, flysch 2000 y heterogénea
      V. Marinos 2007/2014): datos en `data/gsi_digitized_*.json` (desde
      `Bibliografia/Rocas/flysch 2000 y heterogénea 2013`), `core/gsi_charts.py`
      (interpolador, N/A, tipos), `gui/gsi_chart_view.py` (redibujo, selector de
      tipo, notas) y textos EN/ES conmutables; `tests/test_gsi_charts.py`
