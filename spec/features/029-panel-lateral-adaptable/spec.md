# Spec 029 — Panel lateral legible y adaptable

> Estado: hecha (2026-11-28). Aprobada el mismo día («puedes elaborar un
> plan y solucionarlo», con el plan aprobado)

## Contexto y objetivo

Revisión de UX del panel izquierdo (2026-11-28; capturas con el estilo
`windows11` de PySide6 6.12, 1366×768, EN/ES, claro/oscuro):

- **H1 (P0)** El panel tenía un ancho máximo fijo (360 px dentro de un
  área de 380) y su contenido necesitaba 407 px (Mohr-Coulomb, EN) o
  431 px (Hoek-Brown, ES). Qt aplastaba los campos por debajo de su mínimo:
  «0,01(» en vez de 0,0105 MPa, «12000 M», «Ángulo de rozamiento de pic»,
  «Hoek & Diederichs generaliz».
- **H2 (P0)** La hoja de estilo de los temas daba borde y relleno a los
  campos numéricos sin definir sus botones: con `windows11` salían flechas
  antiguas, de unos 45×10 px, que tapaban el número; con Fusion no se
  dibujaba ninguna flecha.
- **H3 (P1)** El panel no crecía más de 380 px, y al estrecharlo aparecía
  una barra horizontal que cortaba los botones y los campos.

Objetivo: con cualquier idioma, tema, criterio y ancho del divisor, cada
número, etiqueta y botón del panel se ve entero, y las flechas son
visibles y no tapan el texto.

## Usuarios / actores

- Geotécnico que introduce los parámetros de un material en el panel
  lateral, en cualquier idioma y tema y con la ventana a cualquier tamaño.

## Historias de usuario

- H1: Como geotécnico quiero leer entero el valor de cada parámetro para
  no confundir un número cortado con otro distinto.
- H2: Como geotécnico quiero ensanchar o estrechar el panel y que se
  reorganice, para dar más sitio a las gráficas o a los campos según lo
  que esté haciendo.

## Requisitos funcionales (EARS)

- **RF-1** (ubicuo): EL SISTEMA mostrará entero el valor de cada campo
  numérico del panel, sin que las flechas tapen ningún carácter, en EN y
  ES, en los dos temas, con cualquier criterio y a cualquier ancho
  permitido del panel.
- **RF-2** (ubicuo): EL SISTEMA dibujará las flechas de subir y bajar de
  los campos numéricos con la hoja de estilo de cada tema: visibles, de al
  menos 18 px de ancho y con un hueco propio a la derecha del texto. Vale
  para todos los campos numéricos de la aplicación, también los de los
  diálogos.
- **RF-3** (evento): CUANDO el usuario arrastre el divisor, EL SISTEMA dará
  al panel el ancho que marque el divisor, sin tope fijo, y los campos
  crecerán con él.
- **RF-4** (no deseado): SI el panel es más estrecho de lo que necesita una
  fila etiqueta + campo, ENTONCES EL SISTEMA pondrá la etiqueta encima del
  campo en vez de cortarla. El panel nunca mostrará una barra de
  desplazamiento horizontal.
- **RF-5** (ubicuo): EL SISTEMA no dejará estrechar el panel por debajo del
  mínimo en que caben sus botones y campos, ni colapsarlo, y lo abrirá con
  un ancho en que todo cabe.

## Requisitos no funcionales

- Idiomas EN/ES; estilos `windows11` (el de la aplicación en Windows 11) y
  Fusion (el de los tests sin pantalla).
- Sin textos nuevos visibles, sin cambios en `.ogrdata` ni en el
  portapapeles.

## UX

- **U1**: los valores y los parámetros se leen sin desplazar en horizontal.
- **U2**: los grupos del panel no cambian; solo cómo se reparten el ancho.
- **U8**: un número cortado es notación incorrecta (H1).
- **U12**: botones de las flechas con un objetivo mayor que el de antes.
- **U13**: las flechas se dibujan igual en los dos temas.

Lista de comprobación:

- [x] U1 El resultado principal se ve sin desplazar a 1366×768.
- [x] U2 Controles agrupados por significado; nada de proyecto/programa entre los del material.
- [x] U3 (no aplica) No añade un menú de una sola entrada.
- [x] U4 Atajos y nombres de la plataforma; `QDialogButtonBox`; Esc e Intro.
- [x] U5 Lo destructivo se deshace; solo se confirma lo irreversible.
- [x] U6 Cada vista vacía dice cómo llenarla.
- [x] U7 Validación en línea, tras actuar, con cómo arreglarlo.
- [x] U8 Símbolos, unidades y decimales correctos; ninguna clave interna en pantalla.
- [x] U9 Valores por defecto con fuente; cada ajuste mueve el número (test).
- [x] U10 Lo avanzado plegado, lo frecuente expuesto.
- [x] U11 Tooltips con definición, unidad y fuente.
- [ ] U12 Acción frecuente en sitio fijo y visible. (Parcial: flechas de 18 × 12 px, más que antes pero por debajo de 24 px de alto.)
- [x] U13 Teclado, foco, *buddies*, contraste AA, tema oscuro completo.
- [x] U14 Términos iguales en EN/ES, menús, informe y API.
- [x] U15 Sin *nagging*, red ni telemetría; progreso y cancelar si tarda.
- [x] U16 Mensaje final de qué se hizo.
- [x] U17 Respuesta < 400 ms o indicador de trabajo.
- [x] Ningún patrón prohibido.

## Casos límite

- Valores largos (notación científica, seis cifras significativas,
  negativos) con sufijo de unidad.
- Campos desactivados (spec 026 RF-3): la flecha desactivada también se ve.
- Criterios con campos de tabla (spec 013b) o con botón «Elegir…».

## Fuera de alcance

- Guardar el ancho del panel entre sesiones.
- Revisar el resto de la ventana y los diálogos (salvo las flechas, que
  vienen de la hoja de estilo común).

## Criterios de finalización

- Todos los RF con su test en verde y la suite entera en verde.
- Capturas antes/después en los dos idiomas y los dos temas.
