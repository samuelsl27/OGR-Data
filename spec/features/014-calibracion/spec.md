# Spec 014 — Calibración (calibrate)

## Qué se construye

El diálogo **Calibration** de RSData (captura `33_*`) sobre las specs 006,
011 y 012:

- Elegir el **Material Model** de origen y definir el modelo calibrado
  (nombre de Material y de Material Model, Strength type).
- **Curve Fit Analysis**: Algorithm, Error Summation, Error Type
  (combos a replicar con sus opciones exactas — extraerlas de RSData en
  la fase de plan), Prediction Interval (%).
- Selección de **Failure States** contra los que calibrar y **Failure
  Data Type** (Lab Data / Rock Mass Data); para macizo, σci y D fijos.
- Resultado: nuevo material calibrado en el proyecto.

## Diferencia con la spec 006

La 006 ajusta un criterio a un par de columnas. La 014 calibra **contra
varios estados a la vez** (puntos pico y residuales de varios ensayos),
crea un **nuevo** material sin tocar el original y expone el error
global. Es la evolución natural: se apoya en el núcleo de ajuste.

## Criterios de aceptación

- Calibrar un MC contra dos estados sintéticos con ruido: parámetros
  entre los de ambos estados, error global reportado.
- El material original no se modifica; el calibrado aparece en el árbol.

## Pendiente de extracción (en fase de plan)

Opciones exactas de Algorithm / Error Summation / Error Type y la
definición del "error summation" global (suma de SSR por estado,
ponderada o no — verificar en RSData).
