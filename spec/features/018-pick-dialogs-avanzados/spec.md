# Spec 018 — Pick dialogs avanzados (Barton y c/φ numéricos)

## Qué se construye

Completar los diálogos "Pick" que el viejo RocData tenía y OGR-Data aún
no, **solo con fuentes oficiales verificables** (regla de la casa: no
inventar datos):

1. **Barton-Bandis**: tablas/escalas de φb (por tipo de roca y estado
   seco/húmedo), JRC (escala visual de Barton con perfiles típicos 0-20)
   y JCS. Fuente: Barton & Bandis (1990) o Barton (1973) — de dominio
   público no es; verificar disponibilidad legal o usar los rangos
   documentados en bibliografía descargada (Hoek PRE trata JRC/JCS en
   el cap. de discontinuidades). Si no hay fuente libre suficiente, la
   spec lo dice y se implementa solo lo verificable.
2. **c/φ de suelos por clase USCS con valores numéricos**: la tabla NRCS
   (fig. 3-22) es cualitativa; se localizará una fuente oficial numérica
   (candidata: NAVFAC DM 7.1 "Soil Mechanics", manual público del DoD
   con tablas típicas) y se documentará en Bibliografia antes de
   implementar. Con ello, el clasificador USCS (spec 004) podrá proponer
   valores iniciales numéricos y crear el material.
3. ~~**D (disturbance factor)**~~: pasa a la spec 022 (estimación sin
   ensayos), junto con GSI, mi y Ei (revisión 2026-11-23).

## Criterios de aceptación

- Cada tabla nueva lleva cita de fuente y test de spot-check contra el
  documento original.
- El pick de D devuelve valores dentro de [0, 1] con la descripción del
  nivel de alteración.

## Dependencias

Spec 004 (USCS) para el punto 2; spec 003 para el patrón de pick dialogs.
