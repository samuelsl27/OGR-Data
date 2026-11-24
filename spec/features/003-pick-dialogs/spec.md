# Spec 003 — Pick dialogs bibliográficos

## Qué se construye

Los diálogos "Pick" del programa de referencia antiguo, con datos reales extraídos de la
bibliografía oficial de la suite:

1. **sigci** (GHB y HB): Tabla 2 de Hoek, Practical Rock Engineering cap. 11
   — estimación de campo de la resistencia uniaxial (grados R0–R6 con
   ejemplos de roca).
2. **mi** (GHB): Tabla 3 del mismo capítulo — valores de mi por tipo de roca,
   clase, grupo y textura (± desviación; entre paréntesis = estimados).
3. **GSI** (GHB): carta de Hoek & Marinos (2000) — selector de **estructura
   de la masa** (6 categorías) × **condición superficial de las
   discontinuidades** (5 categorías) → rango GSI. Las celdas se leen de las
   curvas de nivel impresas en la carta (lectura aproximada, indicativa —
   igual que el propio programa de referencia antiguo: "Quoting a range from 33 to 37 is more
   realistic than stating that GSI = 35").

Los datos viven en `ogr_data/data/*.json` con su fuente por tabla. La GUI
añade un botón "Pick…" junto a los campos habilitados.

## Criterios de aceptación

1. Los tres JSON cargan y pasan tests de integridad (rangos, valores
   clave: Granite mi=32±3, Gneiss 28±5, Tuff 13±5, R6 >250 MPa…).
2. El diálogo de tabla devuelve el valor elegido; el de GSI devuelve un GSI
   dentro del rango de la celda seleccionada.
3. Los tests corren sin Qt; el humo de GUI abre los tres pickers offscreen.

## Fuera de alcance

- Tablas c/φ de suelos (llegan con la spec 004, USCS).
- Carta GSI de flysch/roca débil heterogénea (la carta general cubre GSI
  10–100; la extensión a GSI 5 queda documentada para una fase posterior).
- Barton (φb, JRC, JCS): pendiente de fuente oficial descargable.
