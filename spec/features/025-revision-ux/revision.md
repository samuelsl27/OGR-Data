# Revisión de UX de OGR-Data (2026-11-24)

Revisión de la interfaz completa contra la
[guía de UX](../../constitution/ux-guidelines.md), sobre el commit
`ba1298d`. Método: lectura de `ogr_data/gui/` y capturas offscreen a
1366×768 de la ventana (EN, ES, tema claro y oscuro, las dos pestañas) y
de los diálogos de estados de fallo, simulaciones, ajuste, calibración,
clasificador USCS, informe y editor de gráficas. La suite estaba en verde
(220 tests, 0 fallos).

Prioridades: **P0** bug visible · **P1** bloquea o confunde el flujo
principal · **P2** fricción o incoherencia · **P3** pulido.

## Lo que ya está bien

- Las envolventes se redibujan al instante al editar (U17).
- Deshacer/rehacer de todo el proyecto, asterisco de cambios y Guardar /
  Descartar / Cancelar al cerrar (U5, U15).
- Interfaz completa en inglés y español, con separador decimal por idioma
  y test que impide textos sin traducir (U14).
- Tema claro/oscuro con los tokens de la suite (spec 020).
- Las tablas bibliográficas citan su fuente en el propio diálogo (U11, U15).
- Los formularios de parámetros usan `QFormLayout` (etiqueta y campo
  asociados) y los diálogos usan `QDialogButtonBox` (orden de la plataforma).

## Bugs (P0) — se reportan antes de corregir (regla 6)

| Id | Dónde | Qué se ve | Regla |
|---|---|---|---|
| B1 | `gui/fit_dialog.py:53-54` | El desplegable *Criterion* del ajuste muestra las claves internas (`mohr_coulomb`, `generalized_hoek_brown`) en vez de los nombres, en los dos idiomas: `addItem(key, key)` sin etiqueta ni `tr()` | U8, U14 |
| B2 | `gui/themes.py` (hoja oscura) | En tema oscuro la barra lateral sigue gris claro: la hoja no da fondo al `QScrollArea` ni a su *viewport*, así que la columna de controles queda clara entre la barra de menús y las gráficas oscuras. Visto offscreen; falta confirmarlo en Windows real | U13 |
| B3 | `gui/soil_classifier.py:101-120` | La carta de plasticidad queda aplastada a ~10 px entre las entradas y los resultados: la etiqueta «Source: …» no parte líneas y obliga a la columna de resultados a ocupar casi todo el ancho (diálogo de ~1490 px) | U2 |
| B4 | `gui/calibration_dialog.py` | Al abrir la calibración sin estados de fallo ya aparece un error en rojo, en minúsculas y sin solución: «the selected failure states have no (non-excluded) points». No dice que hay que definir estados primero ni ofrece hacerlo | U6, U7 |

## Hallazgos de diseño

### P1

**F1 — El resultado principal no se ve (U1).** La barra lateral mide
1292 px y su ventana visible 719 px a 1366×768. El bloque *Computed* (mb,
s, a, σt, σc, σcm, c, φ, Erm), que es lo que el usuario viene a buscar,
empieza unos 1000 px más abajo: hay que desplazar siempre para verlo, y
al desplazar se pierden los parámetros que se están cambiando. Causa y
efecto quedan en pantallas distintas.

**F2 — La barra lateral mezcla cuatro niveles sin agrupar (U2, U12).**
De arriba abajo: materiales; criterio; dos herramientas (clasificador,
ajuste); el nombre del material (sin etiqueta, solo *placeholder*); la
unidad de tensión (del programa); el título (del proyecto); copiar
material/datos/gráfica; Guardar/Abrir/Importar (repiten el menú
Archivo); aplicación y σ3max; parámetros; rigidez; resultados. El nombre
del material queda separado de su árbol por dos botones de herramientas,
y la acción que justifica el programa —copiar el material a Slip2D—
está a media columna entre ajustes globales.

**F3 — Once menús, cinco con una sola entrada (U3).** *Failure States*,
*Tests*, *Stress Paths*, *Calibrate* y *Compute* tienen una entrada cada
uno; *Analysis* mezcla muestreadores, superposiciones, base de datos e
informes; el clasificador y el ajuste no están en ningún menú (solo en
botones de la barra lateral: incumple la regla 3 de `AGENTS.md`).

**F4 — Faltan convenciones de Windows (U4, U14).** Solo Deshacer/Rehacer
tienen atajo: no hay Ctrl+N, Ctrl+O, Ctrl+S, *Guardar como*, archivos
recientes, F1 ni Supr para borrar un material. Los menús no tienen
aceleradores (`&File`), así que Alt+A/Alt+F no abren nada. En inglés
dice *Load…* y en español *Abrir…*: el estándar es *Open…* / *Abrir…*.
*Help* solo tiene *About*. El título de la ventana muestra el título del
proyecto, no el nombre del archivo.

**F5 — Estados vacíos mudos (U6).** La pestaña *Stress Path Graphs* abre
cuatro ejes vacíos de −0.04 a 0.04 sin decir que faltan trayectorias o
simulaciones ni cómo crearlas; el panel de animación está deshabilitado
sin explicación; el diálogo de estados de fallo abre con todo
deshabilitado y un botón «+» de 30 px como única salida.

### P2

**F6 — Notación (U8).** `sigma1`, `sigma3`, `sig3max` en ASCII en
etiquetas y ejes (en lugar de σ₁, σ₃, σ3max); `deg` en lugar de °;
«Mohr Coulomb» sin guion; «Sigma3» y «sigma3» según el diálogo; seis
decimales fijos en los parámetros (`10.500000 kPa`), cuatro en σ3max
(`7500.0000 kPa`); `Erm = 3686230.82 kPa` (en MPa o GPa se leería);
en la calibración, claves internas en el resultado (`phi_b = …`).

**F7 — Unidades incoherentes (U8, U14).** La ventana trabaja en kPa y el
diálogo de ajuste en MPa. El selector de unidad vive entre los campos del
material, aunque es un ajuste del programa.

**F8 — Confirmaciones donde basta deshacer (U5).** Borrar un material
pide confirmación aunque se puede deshacer; borrar un estado de fallo o
una trayectoria no la pide: dos comportamientos para la misma acción. Hay
23 `QMessageBox` en la interfaz; varios son informativos («no hay series
que exportar», «Erm solo para GHB») y estarían mejor como acción
deshabilitada con tooltip o mensaje en la barra de estado.

**F9 — Sin ayuda contextual (U11).** Solo 5 `setToolTip` en toda la
interfaz y ningún `setStatusTip`. Los parámetros (GSI, mi, D, σci, mb…)
no dicen qué son, su rango típico ni su fuente; el botón *Delete*
deshabilitado no dice por qué (último material).

**F10 — Accesibilidad (U13).** Las etiquetas de la barra lateral son
`QLabel` sueltas sin *buddy* (0 `setBuddy`, 0 `setAccessibleName`): un
lector de pantalla no asocia «Failure criterion» con su desplegable, y el
campo de nombre no tiene etiqueta. Falta revisar orden de tabulación y
contraste del tema oscuro (los grises `#9ab6d6` sobre `#2b2b2b` de los
títulos de grupo).

**F11 — Sin indicador de trabajo (U15, U17).** No hay `QProgressDialog`
ni cursor de espera en ningún sitio. A verificar cuánto tardan la
simulación (Compute), la calibración y el informe con datos reales; si
pasan de ~1 s, necesitan progreso y cancelar.

### P3

**F12 — Coherencia de flujo.** El clasificador USCS necesita pulsar
*Classify* mientras la ventana principal es en vivo; ajuste y
calibración piden pulsar porque calculan, que es razonable. Botones
«Pick…» repetidos por fila: correcto, pero ganarían con un icono y el
tooltip de qué tabla abren.

## Propuesta de orden

1. Bugs B1–B4 (pequeños, sin decisión de diseño).
2. F1 + F2 (reorganizar la ventana: resultados a la vista, barra lateral
   por secciones, barra de herramientas con lo frecuente).
3. F3 + F4 (menús y convenciones).
4. F5 + F8 (estados vacíos y confirmaciones).
5. F6 + F7 (notación y unidades).
6. F9 + F10 + F11 (ayuda, accesibilidad, progreso).

Los requisitos están repartidos en seis specs, una por fase: ver el
[índice](README.md). Los bugs B1–B4 se corrigieron el mismo día (025a).
