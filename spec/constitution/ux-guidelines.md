# Guía de UX de OGR-Data

Parte de la constitución: toda spec que toque la interfaz la cumple, y su
`spec.md` dice qué puntos de esta guía aplica (ver la plantilla). La guía
traduce unas referencias externas, elegidas por la propietaria
(2026-11-24), a reglas concretas para un programa de escritorio de
ingeniería: formularios con muchos parámetros numéricos, gráficas que se
actualizan al instante, diálogos de datos y usuarios técnicos.

Las reglas U1–U17 mandan; las fuentes explican el porqué. Si una regla
choca con la paridad con el viejo RocData/RSData, se discute en la spec y
gana lo que diga la propietaria.

## Fuentes

| Fuente | Qué es | Para qué la usamos |
|---|---|---|
| [Laws of UX](https://lawsofux.com/articles/) | 30 leyes de psicología aplicada al diseño (Jon Yablonski) | El porqué de casi todas las reglas: Hick, Fitts, Miller, Jakob, Tesler, proximidad, región común, Doherty, Peak-End, Zeigarnik |
| [Fluent 2](https://fluent2.microsoft.design/) | Sistema de diseño de Microsoft | Convenciones de Windows (la plataforma principal): menús, atajos, diálogos, foco, contraste |
| [Checklist Design](https://www.checklist.design/) | Listas de comprobación por componente y por pantalla | Revisar formularios, entradas, botones, diálogos, tablas, estados vacíos y mensajes de error |
| [Autodesk HIG (Weave)](https://github.com/Autodesk/hig) | Sistema de diseño de Autodesk para aplicaciones profesionales tipo CAD | Densidad (alta/baja), entrada numérica, árboles, paneles, temas claro/oscuro |
| [Humane by Design](https://humanebydesign.com/) | Principios de producto humano: resiliente, capacitador, finito, inclusivo, intencional, respetuoso, transparente | Respeto al tiempo y la atención del usuario, accesibilidad, transparencia |
| [Growth.Design — Psychology](https://growth.design/psychology) | Catálogo de sesgos cognitivos aplicados a producto | Carga cognitiva, revelado progresivo, sesgo por defecto, anclaje, reconocer mejor que recordar |
| [GoodUI](https://goodui.org/) | Patrones de interfaz respaldados por tests A/B | Deshacer en vez de confirmar, valores por defecto inteligentes, mostrar el estado, diseñar para cero datos, convenciones |
| [Deceptive Design](https://deceptive.design/) | Catálogo de patrones engañosos (*dark patterns*) | Lo que **nunca** se hace (ver «Patrones prohibidos») |

Solo se enlazan: el texto de Laws of UX es CC BY-NC-ND y no se copia.

## Reglas

**U1 — El resultado, siempre a la vista.** Lo que el usuario vino a
buscar (mb, s, a, c, φ, σt, σcm, Erm, el factor del ajuste…) se ve sin
desplazar nada en una pantalla de 1366×768. *Visibilidad del estado,
atención selectiva, umbral de Doherty.*

**U2 — Agrupar por lo que significa.** Lo relacionado va junto y en una
región común (material → criterio y parámetros → rango de tensiones →
resultados). Lo del proyecto (título, unidades) y lo del programa (tema,
idioma) no se mezcla con los campos del material. Bloques de 7 ± 2
elementos como mucho. *Proximidad, región común, chunking, Miller.*

**U3 — Pocas decisiones a la vez.** La barra de menús tiene como mucho
~9 menús y ninguno con una sola entrada; las acciones raras van a un
submenú o a un diálogo, no a la primera línea. *Hick, sobrecarga de
elección, fatiga de decisión.*

**U4 — Las convenciones de la plataforma.** Archivo con Nuevo / Abrir /
Guardar / Guardar como / Recientes y sus atajos (Ctrl+N, Ctrl+O, Ctrl+S,
Ctrl+Mayús+S), F1 para la ayuda, Supr para borrar, Esc cierra un
diálogo, Intro acepta. Los botones de un diálogo con `QDialogButtonBox`,
que pone el orden de la plataforma. *Jakob, Fluent 2.*

**U5 — Deshacer mejor que preguntar.** Toda edición del proyecto se
deshace (spec 023), así que borrar un material o un estado no pide
confirmación: se borra y se dice en la barra de estado cómo deshacerlo.
Se pregunta solo lo irreversible: cerrar con cambios sin guardar,
sobrescribir un archivo. *GoodUI «Undos instead of prompting»; Humane
«Empowering».*

**U6 — Un estado vacío enseña el siguiente paso.** Una gráfica, tabla o
lista sin datos dice qué falta y ofrece el botón o el menú que lo crea
(«Sin trayectorias: defina una en Trayectorias > Definir…»), en vez de
unos ejes vacíos. *GoodUI «Designing for zero data»; Checklist «Empty
states».*

**U7 — Errores a tiempo y que digan cómo arreglarlos.** Validación en
línea junto al campo, después de que el usuario actúe (no al abrir el
diálogo). El mensaje dice qué pasa y qué hacer, en frase normal, sin
códigos internos. Aceptar lo razonable (coma o punto decimal, espacios) y
devolver siempre en un formato. *Postel; Checklist «Error messages».*

**U8 — Notación técnica correcta.** σ₁, σ₃, σci, φ, ° y las unidades de
la spec 017 en pantalla; las claves internas (`mohr_coulomb`, `phi_b`)
nunca. Decimales significativos según la magnitud (no seis decimales
fijos); la misma unidad de tensión en la ventana y en todos los
diálogos. *Modelo mental; similitud.*

**U9 — Valores por defecto sensatos, y a la vista.** Cada parámetro
arranca en un valor típico y con fuente; lo preseleccionado nunca cambia
un resultado sin que se vea. Un ajuste que no mueve el número no existe
(regla 7 de AGENTS.md). *Smart defaults, sesgo por defecto; Deceptive
«Preselection», «Sneaking».*

**U10 — Revelado progresivo, sin esconder lo frecuente.** Lo avanzado
(rigidez, casquetes, opciones de ajuste) puede plegarse; lo que se usa
en cada sesión queda expuesto. *Tesler, revelado progresivo; GoodUI
«Exposing options».*

**U11 — Reconocer mejor que recordar.** Cada parámetro lleva un tooltip
con su definición, su unidad y su fuente bibliográfica; los selectores
«Elegir…» muestran tablas, no piden recordar valores. *Recognition over
recall, carga cognitiva.*

**U12 — Lo frecuente, grande y cerca.** Las acciones de cada sesión
(copiar material, guardar, calcular) tienen un sitio fijo y visible
(barra de herramientas o panel), con objetivos de al menos 24 px.
*Fitts; Pareto.*

**U13 — Accesible.** Todo se alcanza con teclado y con un orden de
tabulación lógico; el foco se ve; cada etiqueta tiene su *buddy*; el
contraste de texto llega a WCAG AA (4,5:1) en los dos temas; el color
nunca es la única pista (material: color **y** símbolo). El tema oscuro
cubre toda la ventana. *Fluent 2 (accesibilidad); Humane «Inclusive».*

**U14 — Una palabra por concepto.** El mismo término en menús, botones,
diálogos, informe, API y documentación, en inglés y en español (el
glosario de la spec 024). *Consistencia, similitud.*

**U15 — Respeto y transparencia.** Sin avisos repetidos, sin telemetría,
sin red no pedida. Se dice qué se guarda, qué se copia al portapapeles y
de dónde sale cada número. Lo que tarda muestra progreso y se puede
cancelar. *Humane «Respectful», «Transparent», «Finite».*

**U16 — Cerrar bien.** Al terminar un flujo (guardar, copiar, exportar,
generar el informe, aplicar un ajuste) la barra de estado dice qué se
hizo y dónde. *Peak-End.*

**U17 — Respuesta en menos de 400 ms.** Cambiar un parámetro redibuja al
instante; si un cálculo va a tardar más, se ve que está trabajando y no
bloquea la ventana. *Umbral de Doherty; flow.*

## Patrones prohibidos

De [deceptive.design](https://deceptive.design/), los que podrían colarse
en un programa como este: preselección que cambia resultados, información
escondida o retrasada (*sneaking*), interrupciones repetidas (*nagging*),
redacción ambigua en confirmaciones (*trick wording*: «¿No quiere no
guardar?»), obstrucción para exportar o salir, confirmación que culpabiliza
(*confirmshaming*), interferencia visual que esconde una opción. Ninguno
tiene excusa.

## Lista de comprobación de una spec o un cambio de interfaz

Se copia en la sección «UX» del `spec.md` y se marca al validar.

- [ ] U1 El resultado principal se ve sin desplazar a 1366×768.
- [ ] U2 Controles agrupados por significado; nada de proyecto/programa entre los del material.
- [ ] U3 No añade un menú de una sola entrada.
- [ ] U4 Atajos y nombres de la plataforma; `QDialogButtonBox`; Esc e Intro.
- [ ] U5 Lo destructivo se deshace; solo se confirma lo irreversible.
- [ ] U6 Cada vista vacía dice cómo llenarla.
- [ ] U7 Validación en línea, tras actuar, con cómo arreglarlo.
- [ ] U8 Símbolos, unidades y decimales correctos; ninguna clave interna en pantalla.
- [ ] U9 Valores por defecto con fuente; cada ajuste mueve el número (test).
- [ ] U10 Lo avanzado plegado, lo frecuente expuesto.
- [ ] U11 Tooltips con definición, unidad y fuente.
- [ ] U12 Acción frecuente en sitio fijo y visible.
- [ ] U13 Teclado, foco, *buddies*, contraste AA, tema oscuro completo.
- [ ] U14 Términos iguales en EN/ES, menús, informe y API.
- [ ] U15 Sin *nagging*, red ni telemetría; progreso y cancelar si tarda.
- [ ] U16 Mensaje final de qué se hizo.
- [ ] U17 Respuesta < 400 ms o indicador de trabajo.
- [ ] Ningún patrón prohibido.
