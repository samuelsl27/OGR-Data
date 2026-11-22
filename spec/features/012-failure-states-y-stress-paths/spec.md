# Spec 012 — Estados de fallo y rutas de tensión

## Qué se construye

Los dos tipos de objeto observados en RSData (capturas `31_*`, `32_*`),
sobre el proyecto multi-material (spec 011):

1. **Failure State**: nombre/color/símbolo; Test Type; dos tablas de
   puntos **Peak Points** y **Residual Points** (σ3, σ1, Exclude) con
   cortar/pegar/importar/exportar CSV. Se dibujan como puntos sobre las
   gráficas (puntos pico y residuales, como el "Plot Test Data" de
   RocData) y alimentan el ajuste (spec 014) y la calibración.
2. **Stress Path**: nombre/color; Test Type, Seepage Condition (drenado/
   no drenado), Loading Direction (compresión/tracción), Initial
   Effective Lateral Stress (kPa), Initial Effective K0, Strain Type
   (p. ej. Lateral); tabla de pasos (EpsilonZZ, SigmaZZ, EpsilonXX).
   Se representa como ruta en las gráficas (pestaña Stress Path Graphs).

## Criterios de aceptación

- Crear/editar/borrar estados y rutas por material; round-trip.
- Puntos de un estado se dibujan en ambas gráficas (puntos σ1-σ3 y
  círculos de Mohr en cortante-normal, como documenta el manual RocData).
- Importar/exportar CSV de puntos (mismo parseo que el diálogo de ajuste,
  spec 006).
- Las rutas de tensión se dibujan como polilíneas sobre las gráficas
  principales.

## Fuera de alcance

- Simular la ruta con el modelo constitutivo (spec 013); aquí la ruta es
  un dibujo de datos introducidos.
- Calibrar contra estados (spec 014).
