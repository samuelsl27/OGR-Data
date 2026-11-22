# Spec 004 — Clasificador de suelos USCS

## Qué se construye

Clasificador **USCS (ASTM D2487)** según los criterios de laboratorio del
NRCS NEH 631 cap. 3 (fig. 3-17, verificada en página renderizada) y la carta
de plasticidad (A-line **PI = 0,73·(LL − 20)** en texto oficial del NEH 650
cap. 4; NRCS usa ratio orgánico LL(horno)/LL(aire) **< 0,7**):

- Entradas: %finos (tamiz No. 200), %arena del total (el grueso se deduce),
  Cu y Cc (para gruesos limpios), LL y PI (para finos), ratio orgánico,
  indicador de suelo altamente orgánico.
- Salida: símbolo USCS (incluidos símbolos dobles GW-GM, CL-ML, triples
  GW-GM-GC en casos límite PI 4–7), más la **ficha de propiedades** de la
  fig. 3-22 del NRCS (nombre típico, resistencia al corte, compresibilidad,
  trabajabilidad, permeabilidad) con cita de fuente.
- Diálogo GUI con carta de plasticidad (punto LL/PI sobre la A-line).

## Decisión documentada: sin valores numéricos c/φ

La tabla oficial NRCS (fig. 3-22) es **cualitativa**: no contiene rangos
numéricos de c/φ por clase. Para no inventar datos, esta spec **no propone
valores numéricos**: la creación automática de materiales con c/φ queda
aplazada a una spec posterior con fuente numérica oficial (p. ej. NAVFAC
DM 7.1), como anota `01_clasificacion_de_suelos.md` en la bibliografía.

## Criterios de aceptación

1. Casos de prueba canónicos (GW, GP, SW, SP, GM, GC, SM, SC, ML, CL,
   OL, MH, CH, PT y símbolos dobles) clasifican según la fig. 3-17.
2. La A-line reproduce la regla del texto NRCS.
3. La ficha de propiedades cubre las 15 clases de la fig. 3-22.
4. Tests sin Qt; humo offscreen del diálogo.

## Referencias

- `Suelos/NRCS_NEH-631_Ch3_...pdf` figs. 3-14, 3-17, 3-22 (renderizadas y
  verificadas el 2026-11-22).
- `Suelos/NRCS_EFH_Ch4_Elementary-Soils-Engineering_full.pdf` (A-line en
  texto).
- Investigación: `Bibliografia/01_clasificacion_de_suelos.md`.
