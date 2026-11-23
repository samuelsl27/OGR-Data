# Spec 025a — Errores visibles de la revisión de UX

> Estado: **hecha** (2026-11-24). Aprobada por la propietaria el
> 2026-11-24 («arregla ya los 4 bugs»).

## Contexto y objetivo

La [revisión de UX](../025-revision-ux/revision.md) encontró cuatro bugs
que se ven en pantalla. Son pequeños y no piden decisiones de diseño, así
que van antes que el resto de la serie 025.

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA mostrará en el desplegable de criterio del ajuste
  el nombre traducido de cada criterio, nunca su clave interna. *(B1)*
- **RF-2**: MIENTRAS el tema sea oscuro, EL SISTEMA pintará toda la
  ventana, barra lateral incluida, con la paleta oscura; al volver al
  claro, la paleta será la de antes de aplicar ningún tema. *(B2)*
- **RF-3**: EL SISTEMA mostrará la carta de plasticidad del clasificador
  con al menos 300 px de ancho, con los textos largos de fuente partidos
  en líneas, en un diálogo que quepa en 1366 px con las fuentes de
  Windows (1198 px medidos). *(B3)*
- **RF-4**: SI ningún estado de fallo tiene puntos, ENTONCES EL SISTEMA
  dirá en la calibración qué hay que hacer, sin texto de error, y
  ofrecerá un botón «Define Failure States…» que cierra la calibración y
  abre ese diálogo. *(B4)*
- **RF-5**: SI hay estados con puntos pero ninguno seleccionado, ENTONCES
  EL SISTEMA pedirá seleccionar uno, sin texto de error. *(B4)*

## UX

U6, U7, U8, U13, U14 de la guía.

## Fuera de alcance

El resto de hallazgos (025b–f).

## Criterios de finalización

Cada RF con su test en `tests/test_ux_025a.py` y la suite entera en verde.
