# Spec 025e — Notación, decimales y unidades

> Estado: **borrador** (2026-11-24), pendiente de aprobación.

## Contexto y objetivo

Hallazgos F6 y F7 de la [revisión](../025-revision-ux/revision.md):
`sigma1`, `sigma3`, `sig3max` y `deg` en pantalla; seis decimales fijos
en todos los parámetros (`10.500000 kPa`), cuatro en σ3max
(`7500.0000 kPa`); `Erm = 3686230.82 kPa`; claves internas en el
resultado de la calibración; el ajuste en MPa con la ventana en kPa.

**Decimales** (decisión de la propietaria, 2026-11-24): según el
parámetro, entre 4 y 6, mirando RSData; **lo que se copia lleva todos
los decimales**. Lo que muestra RSData 1.009 en sus capturas
(`../../../../Referencias/Ejemplos/RSData_analisis/capturas/`): sin ceros
de relleno y hasta 6 cifras significativas — `100000` (UCS), `100`
(GSI), `10` (mi), `0` (D) en la 39; `0.000233284` (cohesión) y
`40.5662` (fricción) en la 74.

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA escribirá σ₁, σ₃, σ3max, σci, σt, σc, σcm, φ, τ y
  ° en etiquetas, ejes, resultados, diálogos e informe, en los dos idiomas.
- **RF-2**: EL SISTEMA mostrará cada parámetro de entrada sin ceros de
  relleno y con como mucho 6 cifras significativas, como RSData.
- **RF-3**: EL SISTEMA mostrará cada resultado con los decimales de su
  parámetro, entre 4 y 6, según una tabla única del plan
  [NECESITA ACLARACIÓN: confirmar la tabla con la propietaria].
- **RF-4**: CUANDO el usuario copie un material o datos, exporte CSV o
  guarde el proyecto, EL SISTEMA escribirá los valores con toda su
  precisión, no con los decimales de pantalla.
- **RF-5**: CUANDO el usuario escriba un valor con más decimales de los
  que se muestran, EL SISTEMA guardará y usará el valor escrito, no el
  redondeado.
- **RF-6**: EL SISTEMA mostrará los módulos (Ei, Erm, E) en la unidad de
  tensión elegida y, si pasan de 10⁶ de esa unidad, en la siguiente
  (kPa → MPa → GPa) [NECESITA ACLARACIÓN: ¿o siempre en la elegida?].
- **RF-7**: EL SISTEMA usará en todos los diálogos (ajuste, calibración,
  estados, trayectorias, simulación, base de datos) la unidad de tensión
  de la ventana.
- **RF-8**: EL SISTEMA no mostrará claves internas (`phi_b`,
  `mohr_coulomb`, `_deg`) en ningún texto visible.
- **RF-9**: EL SISTEMA escribirá los nombres de criterio con su grafía
  bibliográfica (Mohr-Coulomb, Hoek-Brown, Barton-Bandis).

## Requisitos no funcionales

- Separador decimal según el idioma (spec 024) intacto.
- Una sola función de formato en la interfaz (`gui/i18n` o
  `gui/number_format`), no un `:.4f` por sitio.
- `.ogrdata`, portapapeles y CSV no cambian de formato.

## Propuesta de tabla (para el plan)

| Parámetro | Pantalla | Motivo |
|---|---|---|
| mb, s, a, mi, D, GSI, ν | 4–6 cifras significativas | Adimensionales; s puede ser 1e-4 |
| Tensiones (σci, σt, σc, σcm, c) | 6 cifras significativas | Como RSData |
| Ángulos (φ, φb, φr, ψ) | 4 decimales | RSData `40.5662` |
| Módulos (Ei, Erm, E) | 6 cifras significativas | — |

## UX

U8, U14.

## Casos límite

- s = 0 o muy pequeño (GSI bajo): notación sin redondear a 0.
- Valores negativos (σt).
- Copiar con la ventana en MPa: el portapapeles sigue en kPa (spec 005/017).

## Fuera de alcance

Unidades imperiales (idea registrada sin spec).

## Criterios de finalización

Tests de RF-2, RF-4 y RF-5 con valores de muchos decimales; test estático
de que no queda `sigma1`/`deg` visible; suite en verde.

## Dudas abiertas

- [NECESITA ACLARACIÓN: tabla de RF-3]
- [NECESITA ACLARACIÓN: RF-6, cambio automático de unidad en módulos]
