# Plan y tareas 029 — Panel lateral legible y adaptable

Aprobados el 2026-11-28 junto con la spec.

## Decisiones

| Decisión | Alternativa descartada | RF |
|---|---|---|
| Botones y flechas de `QAbstractSpinBox` definidos en la hoja de cada tema, con flechas SVG propias (`ogr_data/gui/icons/`) cuya ruta absoluta se pone en la hoja al cargar el módulo | Forzar el estilo Fusion: sin hoja de botones tampoco dibuja las flechas; quitar las flechas (`NoButtons`): pierde el ajuste con ratón | RF-2 |
| `NumberSpinBox` mide su ancho con el texto más largo que puede mostrar `format_number` (+ sufijo) en vez de con el rango (±1e12) | Ancho fijo en píxeles: no sigue a la fuente ni al idioma | RF-1 |
| Formularios del panel con `WrapLongRows` y `AllNonFixedFieldsGrow` | Etiquetas con salto de línea (`setWordWrap`): parte palabras técnicas y descoloca los *buddies* | RF-3, RF-4 |
| Sin ancho máximo; mínimo del área = mínimo del contenido; divisor no colapsable; barra horizontal desactivada | Mantener el tope y achicar fuentes: no arregla el ensanchar | RF-3, RF-5 |

## Tareas

- [x] **T1** Tests de los RF-1…RF-5 (`tests/test_spec_029.py`), en rojo.
  Hecho cuando: fallan por H1–H3 y no por otra cosa.
- [x] **T2** Flechas en la hoja de estilo (RF-2). Hecho cuando: el test de
  RF-2 pasa en los dos temas.
- [x] **T3** Ancho de `NumberSpinBox` y panel adaptable (RF-1, RF-3, RF-4,
  RF-5). Hecho cuando: todos los tests de la spec y la suite entera pasan.
- [x] **T4** Validación: capturas antes/después y lista de UX marcada.

## Validación (2026-11-28)

Suite entera: **279 tests, 0 fallos** (código de salida 127: el aborto
al cerrar ya anotado en `AGENTS.md`).

| RF | Test (`tests/test_spec_029.py`) | Resultado |
|---|---|---|
| RF-1 | `test_numbers_are_whole_and_arrows_beside_them` | ok |
| RF-2 | `test_arrows_are_drawn_by_the_theme` | ok |
| RF-3 | `test_sidebar_follows_the_splitter` | ok |
| RF-4 | `test_narrow_sidebar_wraps_rows_instead_of_cutting` | ok |
| RF-5 | `test_sidebar_opens_wide_enough` y el anterior (no colapsa) | ok |

Los tests recorren Fusion y `windows11`, EN/ES, claro/oscuro, y los
criterios Mohr-Coulomb, Hoek-Brown generalizado y Softening Hardening.
Pasan con y sin `QT_QPA_FONTDIR`. Sin carpeta de fuentes el texto mide más
y la gráfica impone su mínimo; los tests lo tienen en cuenta.

Capturas antes y después con la plataforma real de Windows y el estilo
`windows11`, a 240, 300, 380 y 600 px.

Decisiones tomadas al implementar:

- El ancho inicial es el que piden las filas en una línea, con un tope del
  40 % del divisor para que las gráficas conserven el resto. Se mide tras
  el primer `show()` (un `QTimer` de 0 ms), porque antes ni la hoja ni la
  ventana han dado su tamaño.
- Tolerancia de 1 px en el RF-4: `QFormLayout` redondea al decidir si parte
  una fila (un desplegable recibió 107 px con un mínimo de 108).

Pendiente:

- Los botones de las flechas miden 18 × 12 px: más que antes, pero por
  debajo de los 24 px de U12 en altura, que no da un campo de una línea.
- Detalles de pulido vistos en las capturas, fuera de alcance: el
  desplegable de criterio, cuando pasa bajo su etiqueta, queda sangrado; el
  texto de «Añadir material» queda lejos de su flecha.
