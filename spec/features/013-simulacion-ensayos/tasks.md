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

## 13b

- [x] Leer los manuales RS2/RSData (DP, CC/MCC, SH, MC, HB) desde las páginas renderizadas
- [x] Motor en tensores con retorno espectral; superficies genéricas y conjunto activo robusto
- [x] Corte a tracción (pico/residual) en MC, DP y Softening-Hardening
- [x] Drucker-Prager (frágil, no asociado); corregir el signo de qφ en su envolvente (spec 002)
- [x] Cam-Clay y Modified Cam-Clay (elasticidad no lineal, OCR, endurecimiento, vértice de CC)
- [x] Softening-Hardening, mecanismo desviador hiperbólico con las dos opciones de dilatancia
- [x] Simple Shear (drenado / no drenado)
- [x] Verificación: soluciones cerradas, integración de referencia MCC, ejemplos de los manuales (comparación documentada)
- [x] Plan, roadmap; suite en verde; commit
- [ ] NorSand (sin manual público); General Test (entradas sin documentar)
- [ ] Softening-Hardening: casquete vertical / elíptico y endurecimiento tabular

## 13c (pendiente)

- [ ] Modelos cíclicos y pestaña Animation
