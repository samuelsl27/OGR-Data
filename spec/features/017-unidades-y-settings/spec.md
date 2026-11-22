# Spec 017 — Unidades y configuración del proyecto

## Qué se construye

El **Project Settings** de RSData (captura `30_*`): selector de unidades
("Metric, stress as kPa" observado; el viejo RocData documenta métricas
MPa/kPa/tsm e imperiales ksf/ksi/psf/psi/tsf) aplicado a todo el
programa, y la configuración de título del proyecto.

## Diseño

- Capa de unidades en el núcleo: hoy el núcleo trabaja en MPa con
  frontera kPa (registro). Se introduce `core/units.py` con factores
  por magnitud (tensión, peso unitario) y dirección de conversión
  centralizada; la UI muestra la unidad elegida y el registro/clipboard
  sigue en kPa (contrato spec 005 inalterado).
- Combo de unidades de tensión: kPa, MPa (+ t/m², imperial en fase 2).
- Título del proyecto en el informe (spec 015) y en la ventana.

## Criterios de aceptación

- Cambiar kPa↔MPa actualiza todos los spinbox, salidas y gráficas sin
  cambiar los valores internos; round-trip idempotente.
- Los `.ogrdata` guardan la unidad de visualización.

## Fuera de alcance

- Unidades imperiales (fase 2, cuando se pida).
- Convergence Settings / Solution Algorithm (pertenecen a la spec 013).
