# Spec 013 — Simulación de ensayos (test simulations)

## Qué se construye

El módulo de **Tests** de RSData (captura `20_*`): definir ensayos
simulados sobre el material (Test Type: Uniaxial / Triaxial / Biaxial /
Simple Shear / General; Seepage: Drained / Undrained; Loading Direction:
Compression / Tension; Maximum Strain; Number of Steps; ciclos) y
**Compute** integra el modelo constitutivo paso a paso, produciendo las
curvas de la pestaña **Stress Path Graphs** (q-p', σ1-ε, εv-ε, etc. según
los tutoriales de RSData: NorSand/Fraser River Sand, Modified Cam Clay).

## Faseado propuesto

- **13a — Marco e integración elastoplástica asociada para MC y HB/GHB**
  (flujo perfectamente plástico, drenado; pasos de tensión controlada).
  Cubre la mayoría del valor con los modelos ya implementados.
- **13b — Modelos de suelo avanzados** (Cam-Clay/MCC/NorSand/Softening-
  Hardening/Drucker-Prager como simulación constitutiva real, con sus
  reglas de endurecimiento documentadas en los manuales oficiales ya
  descargados; noDrainage real con presión de poros).
- **13c — Cíclicos y animación** (cargas cíclicas, pestaña Animation de
  RSData).

## Criterios de aceptación (fase 13a)

- Ensayo triaxial CD simulado sobre MC: curva q-ε1 con meseta en q_f
  calculado analíticamente (coincidencia 1 %).
- Comparación documentada contra los tutoriales RSData cuando el modelo
  esté en 13b.

## Riesgos

- Es la spec más grande del backlog; por eso el faseado. Los manuales
  oficiales (DP, CC/MCC, SH) ya están en Bibliografia; NorSand carece de
  manual público (misma limitación que en spec 002).
