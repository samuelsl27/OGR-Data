# Spec 006 — Ajuste a datos de ensayo

## Qué se construye

El "Use Lab Data" del viejo RocData: ajuste de criterios de resistencia a
pares de datos de laboratorio, con los tres métodos documentados en su
manual (Levenberg-Marquardt, Simplex, regresión lineal) y "Residuals"
(suma de cuadrados de distancias verticales).

Compatibilidad criterio/datos (tabla del manual de RocData 2004):

| Datos | GHB intacto (σci, mi) | GHB macizo (mb, s, a) | Mohr-Coulomb | Barton-Bandis | Power Curve |
|---|---|---|---|---|---|
| Triaxial (σ3, σ1) | ✓ (a = 0,5, s = 1) | ✓ (σci, D fijos) | ✓ | | |
| Corte directo (σn, τ) | | | ✓ | ✓ (φb fijo) | ✓ (τ = a(σ+d)^b) |

Métodos por ajuste:
- **HB intacto y MC (triaxial y directo)**: regresión lineal cerrada
  (linealización del manual: y = (σ1−σ3)² para HB, σ1 vs σ3 para MC;
  fórmulas del cap. 11 de Hoek, verificadas en la hoja de cálculo del PDF),
  además de LM/Simplex.
- **GHB macizo, Barton-Bandis, Power Curve**: LM (scipy) y Simplex.

## Criterios de aceptación

1. Datos sintéticos sin ruido: recuperación exacta (lineal) o < 0,5 %
  (LM) de los parámetros en cada ajuste disponible.
2. Residuals ≈ 0 para datos sin ruido.
3. Validación: σ3 ≥ σ1 en datos triaxiales → error (como RocData).
4. La GUI pega datos desde Excel, ajusta y aplica los parámetros al
   criterio activo de la ventana principal.
5. Tests sin Qt del núcleo; humo offscreen del diálogo.

## Fuera de alcance

- Power Curve sobre datos triaxiales (el manual lo permite pero no
  documenta la formulación exacta en espacio principal; se aplaza).
- GHB macizo: aquí se ajustan mb/s/a con σci y D fijos (análisis de datos
  de macizo), no σci/mi.
- **Mejora registrada** (tercera pasada por RSData): el "Define by" del
  GHB admite modo directo **mb, s, a** además de "GSI, mi, D"; cuando el
  registro de OGR-Data lo soporte, el "Apply" de este diálogo podrá
  rellenar el GHB sin el mapeo al HB clásico (hoy anotado como caveat).
