# Tasks 013 — Simulación de ensayos

## 13a

- [x] `core/simulation.py`: ensayo, rigidez lineal isótropa, resistencia MC/HB/GHB pico y residual
- [x] Return mapping multisuperficie en tensiones principales (aristas y vértice) con potencial no asociado
- [x] Control mixto: uniaxial, triaxial y biaxial; drenado y no drenado; compresión y extensión; cíclico básico
- [x] `Material.stiffness` y `Material.test_simulations` en `.ogrdata` (claves opcionales); plantilla de suelo con Test 1
- [x] Menús Tests / Compute, diálogo Define Test Simulations, hijos en el árbol, grupo Stiffness con botón Erm
- [x] Curvas simuladas en Stress Path Graphs y ruta σ'3–σ'1 en Strength Graphs; caché por entradas
- [x] Sección Defined Test Simulations del informe (spec 015)
- [x] Tests contra soluciones cerradas (criterio de aceptación: meseta triaxial CD MC al 1 %)
- [x] Roadmap; suite en verde; commit

## 13b (pendiente)

- [ ] Drucker-Prager, Cam-Clay, Modified Cam-Clay, Softening-Hardening, NorSand (manuales oficiales en Bibliografia)
- [ ] Simple Shear (rotación de ejes principales) y General Test
- [ ] Cortes a tracción (Peak/Residual Tensile Strength)
- [ ] Comparación documentada con los tutoriales de RSData

## 13c (pendiente)

- [ ] Modelos cíclicos y pestaña Animation
