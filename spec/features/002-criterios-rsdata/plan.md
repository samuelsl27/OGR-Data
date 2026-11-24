# Plan 002 — Los diez criterios

## Estructura

- `ogr_data/core/models.py`: `Field` (key, label, default, unit, kind),
  `Criterion` (key, label, category rock/soil, fields, envelope space) y el
  registro `CRITERIA` con los diez criterios y sus por defecto del programa de referencia.
- `ogr_data/core/criteria_envelopes.py`: envolventes genéricas a partir del
  registro. Criterio con espacio "principal": función σ1(σ3) (MPa);
  derivada por diferencias centradas para la construcción tangente
  (reutiliza la lógica de `envelope.py` generalizada). Criterio "shear":
  función τ(σn) directa.
- GUI: selector de criterio + formulario dinámico reconstruido desde el
  registro; las gráficas se actualizan por el mismo mecanismo de refresh.
  Los parámetros derivados extra (mb/s/a, sigt…) se muestran solo para GHB
  (reutiliza `hoek_brown.compute`).

## Conversión de unidades

Los campos se guardan en **kPa** (como en los diálogos del programa de referencia); el núcleo
trabaja en **MPa** (convención de la spec 001). Conversión en la frontera de
la capa de envolventes.

## Alternativas descartadas

- Implementar las superficies de fluencia completas de CC/MCC y NorSand:
  requieren el estado de consolidación (simulación), no una envolvente; se
  aplaza a la fase de test simulations.
- Derivadas analíticas por criterio: más rápidas pero duplican fórmulas; la
  diferencia central sobre 200 puntos es despreciable (<0,1 %) y mantiene
  el código junto a la fórmula única.

## Riesgos

- Semántica exacta de c y Waviness en Power Curve, y de los enums de
  Softening-Hardening: se registran sin efecto hasta verificarlo (anotado en
  la spec, sin inventar).
