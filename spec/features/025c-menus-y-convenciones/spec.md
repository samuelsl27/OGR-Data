# Spec 025c — Menús y convenciones de Windows

> Estado: **borrador** (2026-11-24), pendiente de aprobación.

## Contexto y objetivo

Hallazgos F3 y F4 de la [revisión](../025-revision-ux/revision.md): once
menús, cinco con una sola entrada; el clasificador y el ajuste fuera de
los menús; sin atajos de archivo, *Guardar como*, recientes,
aceleradores Alt ni F1. Decisión de la propietaria (2026-11-24):
**mantener los nombres de RSData** de cada acción, pero agrupar los
menús de forma más limpia.

## Propuesta de menús (8)

Los nombres de las acciones son los de RSData; cambian los contenedores.

| Menú | Entradas |
|---|---|
| **File** / Archivo | New Project (Ctrl+N) · Open… (Ctrl+O) · Save (Ctrl+S) · Save As… (Ctrl+Mayús+S) · Recent Projects ▸ · Import .roc… · Project Settings… · Exit |
| **Edit** / Editar | Undo · Redo · Copy material · Copy data · Copy plot · Delete (Supr) |
| **View** / Ver | Results panel · Toolbar · Theme ▸ · Language ▸ · Stress unit ▸ · Graph Editor… |
| **Materials** / Materiales | Add Material ▸ · Duplicate Material · Rename Material · Delete Material · Material Database… · Soil classifier (USCS)… · Fit lab data… |
| **Tests** / Ensayos | Define Failure States… · Define Stress Paths… · Define Test Simulations… · Compute (F5) · Calibrate… |
| **Analysis** / Análisis | Stress Sampler · Instantaneous MC Sampler · Overlay MC Envelope · Overlay Mogi Line |
| **Report** / Informe | Report Generator… · Add View To Report · Manage Report View… |
| **Help** / Ayuda | Keyboard Shortcuts (F1) · About OGR Data |

*Tests* agrupa lo que RSData reparte en *Failure States*, *Tests*,
*Stress Paths*, *Calibrate* y *Compute*: todo trabaja sobre datos de
ensayo y va en el orden en que se usa (definir → calcular → calibrar).

## Requisitos funcionales (EARS)

- **RF-1**: EL SISTEMA tendrá como mucho 9 menús, ninguno con una sola entrada.
- **RF-2**: EL SISTEMA tendrá cada acción de la interfaz (botones de la
  barra lateral y menús contextuales incluidos) en algún menú de la barra.
- **RF-3**: EL SISTEMA conservará el nombre de RSData de cada acción que
  lo tenga, en inglés, y su traducción en español.
- **RF-4**: EL SISTEMA tendrá los atajos Ctrl+N, Ctrl+O, Ctrl+S,
  Ctrl+Mayús+S, Ctrl+Z, Ctrl+Y, F5 (Compute) y F1, y aceleradores Alt en
  todos los menús y entradas, sin letras repetidas dentro de un menú, en
  los dos idiomas.
- **RF-5**: CUANDO el usuario elija Save en un proyecto sin archivo, EL
  SISTEMA se comportará como Save As.
- **RF-6**: EL SISTEMA guardará los últimos 8 proyectos abiertos o
  guardados en Recent Projects; SI uno ya no existe, ENTONCES lo dirá y
  lo quitará de la lista.
- **RF-7**: CUANDO el usuario pulse Supr con un material, estado,
  trayectoria o simulación seleccionado en el árbol, EL SISTEMA lo borrará
  (un material solo si no es el último).
- **RF-8**: EL SISTEMA mostrará en el título de la ventana el nombre del
  archivo del proyecto (o «Untitled» / «Sin título») y el asterisco de
  cambios sin guardar.
- **RF-9**: CUANDO el usuario pulse F1, EL SISTEMA mostrará la lista de
  atajos de teclado.
- **RF-10**: EL SISTEMA dirá «Open…» en inglés (hoy «Load…»), con el
  mismo término en mensajes y diálogos.

## Requisitos no funcionales

- `tests/test_theme.py` comprueba hoy la lista de menús de la spec 020:
  se actualiza con esta spec.
- La API y el MCP no cambian.

## UX

U3, U4, U5, U12, U14.

## Casos límite

- Aceleradores en español con tildes (Archivo, Edición…).
- Supr mientras se edita el nombre en el árbol: borra texto, no el material.
- Recent Projects vacío: entrada deshabilitada «(none)» / «(ninguno)».

## Fuera de alcance

- Barra de herramientas y panel de resultados (025b).
- Ayuda en línea completa (solo atajos y About).

## Criterios de finalización

Cada RF con su test; un test recorre la barra y falla si una acción de
la ventana no está en ella (regla 3 de AGENTS.md); suite en verde.

## Dudas abiertas

- [NECESITA ACLARACIÓN: ¿«Tests» como nombre del menú agrupado, o
  «Lab Data» / «Datos de ensayo»?]
- [NECESITA ACLARACIÓN: ¿Report como menú propio o dentro de File, como
  en muchos programas de cálculo?]
