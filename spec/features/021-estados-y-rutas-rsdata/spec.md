# Spec 021 — Estados de fallo y rutas de tensión fieles a RSData

## Qué se construye

Completar los objetos de la spec 012 con la disposición exacta de RSData
para todos sus tipos de ensayo, una vez verificada en la interfaz:

1. **Failure States**: tipos oficiales Triaxial, Simple Shear y General
   (ayuda online de RSData). Hoy OGR-Data solo tiene Triaxial (σ3, σ1,
   verificado) y su extensión Direct Shear (RocData). Falta saber qué
   columnas/campos piden Simple Shear y General, si todos llevan pestañas
   Peak/Residual y qué hace *Exclude* exactamente; y dibujarlos (Simple
   Shear: presumiblemente τ–σn; General: tensor completo → principales).
2. **Stress Paths**: columnas por combinación (Uniaxial × Strain Type
   Lateral/Volumetric; Triaxial × Loading Direction Lateral/Axial ×
   Drained/Undrained; Biaxial; Simple Shear; General) y la **semántica
   de Loading Direction** (qué tensión varía, cuál se mantiene y cómo
   entra K0). Hoy OGR-Data usa una interpretación provisional:
   - Triaxial/Axial: varía SigmaZZ, la lateral se mantiene en σ'h0.
   - Triaxial/Lateral: varía SigmaXX (columna verificada en la figura
     oficial), la axial se mantiene en σ'v0 = σ'h0/K0.
   - Biaxial, Simple Shear, General: se guardan pero no se dibujan.
3. **Stress Path Graphs**: segunda gráfica según la condición (Volumetric
   Strain en drenado, Pore Water Pressure en no drenado — requiere saber
   si/cómo la ruta aporta presión de poro), lista de variables de eje
   seleccionables con clic derecho (como RSData) y convención de signos.

## Motivación

La 012 dejó estos puntos anotados porque la ayuda oficial no documenta
las columnas ni la semántica y el código de RSData no se decompila. Son
la base de la calibración (014) y de la simulación (013): sin la
disposición exacta, los datos introducidos en OGR-Data no serían
intercambiables con RSData.

## Fuentes y verificación

- Hecho: ayuda online oficial guardada en
  `Referencias/Ejemplos/RSData_analisis/ayuda_online/` y resumida en
  `06_ayuda_online.md`; nombres internos de los ensamblados (sin
  decompilar).
- Pendiente: verificación en la interfaz con Claude Desktop (computer
  use) según `Data/Promps/2026_11_23_Prompt_Claude-Desktop_RSData-ORMAS.md`,
  que deja el resultado en `RSData_analisis/07_estados_y_rutas_verificado.md`.
  **Esta spec se desarrolla cuando ese documento exista.**

## Criterios de aceptación

- Cada combinación tipo/dirección del diálogo de OGR-Data muestra los
  mismos campos, defectos y columnas que RSData (tabla del documento 07).
- La interpretación provisional de la 012 se sustituye por la deducida
  numéricamente en RSData (mismos p, q y tensión axial para la misma
  ruta); tests con esos números.
- Los estados Simple Shear y General se introducen, guardan y dibujan.
- Ficheros `.ogrdata` de la 012 siguen cargando (migración si cambian
  claves o columnas).

## Fuera de alcance

- Simular las rutas con el modelo constitutivo (013).
- Calibración (014).
