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

## Opciones verificadas en RSData 1.009 (2026-11-23)

`RSData_analisis/07_estados_y_rutas_verificado.md` §4:

- Strength type: Mohr Coulomb · Generalized Hoek Brown (defecto) ·
  Power Curve · Barton Bandis.
- Algorithm: None · Linear Regression · Levenberg-Marquardt.
- Error Summation: None · Vertical (con LM). Error Type: None · Absolute
  · Relative. Casilla Prediction Interval. Failure Data Type: Lab Data.
- Crea un material nuevo "Calibrated Material" con el modelo calibrado
  en **solo lectura**; el original no cambia.
- **Caso de validación**: estado triaxial (0; 40,3), (100; 409), (200;
  778), (300; 1500); MC + LM + Vertical + Absolute: con los 4 puntos
  c = 0,000233 kPa, φ = 40,5662°; con (300; 1500) excluido c = 10,4788,
  φ = 34,9894° — el segundo ya lo reproduce el ajuste lineal de la 006
  (test en `test_states.py`). El primero sugiere que LM acota c ≥ 0
  (hipótesis a confirmar en el plan).
- Con Algorithm = Linear Regression y Error = None el modelo salió igual
  al de partida (no verificado si es que no ajusta): aclarar en el plan.

## Pendiente (fase de plan)

Definición del error global con varios estados (suma de SSR por estado,
ponderada o no) y el efecto de Prediction Interval.
