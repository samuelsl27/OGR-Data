# Spec 001 — Calculadora Hoek-Brown (núcleo GHB + envolventes)

## Qué se construye

El núcleo de OGR-Data: cálculo de los parámetros del criterio de
**Hoek-Brown generalizado 2002** (mb, s, a) a partir de σci, GSI, mi y D;
los parámetros derivados de la masa de roca (sigt, sigc, sigcm); los
**parámetros Mohr-Coulomb equivalentes** (c, φ) sobre un rango de tensión
definido por el usuario (Custom o General = σci/4); y el **módulo de
deformación** Erm con los métodos de Hoek-Diederichs 2006 (generalizado y
simplificado) y Hoek-Carranza-Torres-Corkum 2002. Interfaz Qt con barra
lateral de entrada interactiva (estilo viejo RocData) y dos gráficas
matplotlib: σ1–σ3 y τ–σn.

## Por qué

Es la funcionalidad central (equivale a ORMAS y al corazón de RocData) y la
base sobre la que se montan los demás criterios, los pick dialogs y el
portapapeles.

## Criterios de aceptación

1. Con σci=30 MPa, GSI=50, mi=10, D=0: mb=1,6768; s=0,0039; a=0,5057;
   sigt=−0,0692 MPa; sigc=1,8068 MPa; sigcm=5,2300 MPa (validado contra
   ORMAS, tolerancia 0,5 %).
2. Con σ3max=7,5 MPa: MC equivalente c=1,4941 MPa, φ=30,52° (validado
   contra ORMAS).
3. Con Ei=12000 MPa: Erm=3686,23 MPa (Hoek-Diederichs 2006 generalizado,
   validado contra ORMAS).
4. Las gráficas σ1–σ3 y τ–σn se actualizan al cambiar cualquier entrada,
   en menos de 200 ms.
5. El módulo de cálculo (`ogr_data.core`) no importa Qt; se prueba solo.

## Fuera de alcance

- Otros criterios (spec 002), pick dialogs (003), USCS (004), portapapeles
  (005), ajuste a datos (006).
- Estimación de σ3max para túnel/talud por profundidad/altura (pendiente de
  extraer la fórmula exacta de la Ref. 1, §6). Se entrega Custom y General.

## Referencias

- `../../Referencias/Ejemplos/ORMAS_analisis/00_resumen.md` (valores de
  validación).
- `../../Referencias/Bibliografia/Rocas/Hoek_CarranzaTorres_Corkum_2002_Hoek-Brown_2002_edition.pdf`
- `../../Referencias/Ejemplos/RSData_analisis/01_modelos_material.md`
  (parámetros GHB de RSData: pestaña Strength, Define by GSI/mi…).
