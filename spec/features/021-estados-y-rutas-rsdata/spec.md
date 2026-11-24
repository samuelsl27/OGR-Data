# Spec 021 — Estados de fallo y rutas de tensión fieles al programa de referencia

## Qué se construye

Rehacer los objetos de la spec 012 con la disposición verificada en la
interfaz del programa de referencia (`07_estados_y_rutas_verificado.md` del análisis
privado en `Referencias/Ejemplos/`, capturas 44–74, exportaciones Excel):

1. **Failure States**: Test Type = Triaxial (Sigma3, Sigma1, Exclude) ·
   Direct Shear (SigmaN, Tau, Exclude) · General (StressXX, StressYY,
   StressZZ, TauXY, TauYZ, TauXZ; sin Exclude). **Una sola tabla por
   estado** (no hay pestañas Peak/Residual). *Exclude* quita el punto de
   la calibración y de las gráficas.
2. **Stress Paths**: Test Type = Uniaxial · Triaxial · Biaxial · Simple
   Shear (no hay General). Campos y columnas por combinación (tabla del
   documento 07): Strain Type None/Volumetric/Lateral (uniaxial);
   Seepage, Loading Direction None/Axial/Lateral, σ'h0 (100) y K0 (1)
   (triaxial/biaxial); σ'h0 y K0 (simple shear). En no drenado la última
   columna es Pore Water Pressure.
3. **Semántica verificada numéricamente** (Loading Direction = Axial):
   SigmaZZ es la tensión axial impuesta; la radial se mantiene en σ'h0;
   K0 no influye; q sin signo; εq = εa − εv/3; en no drenado se grafican
   tensiones efectivas σ − u.

## Decisiones de OGR-Data donde el programa de referencia muestra comportamientos dudosos

- **Uniaxial**: el programa de referencia calcula p y q con una tensión radial oculta de
  100 kPa; OGR usa radial 0 (definición del ensayo) y lo indica en el
  diálogo.
- **Loading Direction = Lateral**: el programa de referencia sobrescribe la columna SigmaXX
  con σ'h0 y grafica la axial como 0; OGR guarda la columna tal cual y no
  dibuja la ruta (significado no verificable). Igual para None, Biaxial
  (invariantes de deformación plana no verificados) y Simple Shear.
- **Strain Type = Lateral**: el programa de referencia reescribe EpsilonXX como −εa/2; OGR
  conserva los datos del usuario.
- **Rutas en las Strength Graphs**: el programa de referencia no las dibuja; OGR sí (puntos
  de tensión en σ1–σ3 y cimas de Mohr en τ–σn), petición expresa del
  propietario.
- Columnas de tensión con unidad en la cabecera (el programa de referencia no la pone en
  rutas ni en "Tau").

## Criterios de aceptación

- Cada combinación muestra los campos y columnas de la tabla verificada.
- Los números de la verificación (TX_Axial K1/K0,5, σ'h0 150, no
  drenado con u, UX_Volumetric) se reproducen en tests.
- Exclude: la calibración MC del programa de referencia con el punto anómalo excluido
  (c = 10,4788 kPa, φ = 34,9894°) se reproduce con el ajuste de la 006.
- Ficheros de la 012 cargan: los puntos residuales pasan a un estado
  propio "<nombre> (residual)"; Compression/Extension → Lateral; ruta
  "General" → Uniaxial.

## Fuera de alcance (pendiente)

- Selección de variables de eje en las Stress Path Graphs (el programa de referencia: Graph
  Editor → Axis Type, 27 variables: componentes, p, q, σ1–σ3, presión de
  poro, totales…) → ampliación de la spec 016.
- Que la 2.ª gráfica pase a Pore Water Pressure cuando todas las rutas
  son no drenadas (no verificado en el programa de referencia).
- Uso interno de K0 en el programa de referencia (posiblemente inicialización de la
  simulación, spec 013).
