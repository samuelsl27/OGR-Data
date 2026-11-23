# Spec 025f — Ayuda contextual, accesibilidad y progreso

> Estado: **borrador** (2026-11-24), pendiente de aprobación.

## Contexto y objetivo

Hallazgos F9–F12 de la [revisión](../025-revision-ux/revision.md): 5
tooltips en toda la interfaz, ninguna etiqueta suelta asociada a su
campo, ningún indicador de progreso, y el clasificador pide pulsar
*Classify* aunque ya se actualiza solo.

## Historias de usuario

- H1: Como geotécnico quiero saber qué es un parámetro, su rango típico y
  de dónde sale sin abrir un manual.
- H2: Como usuario de teclado o lector de pantalla quiero llegar a todo y
  saber qué es cada campo.
- H3: Como usuario quiero saber que un cálculo largo avanza y poder pararlo.

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA mostrará en cada parámetro de material un tooltip
  con su definición, unidad, rango típico y referencia bibliográfica
  (autor y año), tomados del registro del núcleo.
- **RF-2**: EL SISTEMA mostrará en cada acción de menú un texto de estado
  (*status tip*) de una frase.
- **RF-3**: EL SISTEMA asociará cada etiqueta a su campo (*buddy* o
  `QFormLayout`) y dará nombre accesible a los campos y botones sin texto.
- **RF-4**: EL SISTEMA tendrá un orden de tabulación de arriba abajo y de
  izquierda a derecha en la ventana y en cada diálogo.
- **RF-5**: EL SISTEMA tendrá un contraste de texto de al menos 4,5:1
  (WCAG AA) en los dos temas, comprobado por un test sobre los colores de
  la hoja.
- **RF-6**: SI un cálculo (simulación, calibración, informe) dura más de
  1 s, ENTONCES EL SISTEMA mostrará progreso y permitirá cancelarlo sin
  bloquear la ventana.
- **RF-7**: EL SISTEMA clasificará el suelo al cambiar cualquier dato y
  quitará el botón *Classify*.
- **RF-8**: EL SISTEMA mostrará en cada botón «Pick…» un tooltip con la
  tabla que abre y su fuente.

## Requisitos no funcionales

- Definiciones y referencias en el registro del núcleo (`core/models.py`),
  no en la interfaz; la API puede exponerlas en `catalog`.
- Textos con `tr()` y español; la referencia bibliográfica no se traduce.

## UX

U11, U13, U15, U17.

## Casos límite

- Parámetro sin referencia publicada: el tooltip lo dice, no inventa.
- Cancelar una simulación a medias: no deja resultados parciales en el
  proyecto.

## Fuera de alcance

Manual de usuario y ayuda en línea.

## Criterios de finalización

Test de que todo parámetro del registro tiene definición, unidad y
referencia; test de *buddies*; test de contraste; medición de la
duración de los cálculos con un caso real antes de decidir RF-6; suite en
verde.

## Dudas abiertas

- [NECESITA ACLARACIÓN: ¿quién redacta las definiciones de parámetros, a
  partir de qué fuentes (Hoek 2007, manuales de RSData como guía)?]
- [NECESITA ACLARACIÓN: el umbral de RF-6 se fija tras medir.]
