# OGR Data

Propiedades de materiales para la suite OpenGeoRock: criterios de
resistencia (Hoek-Brown generalizado, Mohr-Coulomb, Barton-Bandis, Power
Curve, Drucker-Prager, Cam-Clay, NorSand…), clasificación USCS,
estimación desde bibliografía, ajuste y calibración con datos de ensayo,
simulación de ensayos, informes y transferencia por portapapeles a OGR
Slip2D y OGR FEM2D, con la línea de diseño de OGR Slip2D.

*OpenGeoRock* (u *OGR Suite*) es el paraguas; **OGR Data** es este
programa y lo único que contiene este repositorio. Paquete instalable
`ogr-data`, paquete de importación `ogr_data`. Es **independiente**: no
depende de `ogr-core` (ver `spec/constitution/tech-stack.md`).

Autor y titular del copyright: Samuel Sáez López (UPCT). Licencia
AGPL-3.0-or-later.

> Este archivo es el **contrato de trabajo** con cualquier agente de IA.
> Se lee antes de cada acción, junto con la constitución
> (`spec/constitution/`) y la spec activa. Si algo aquí contradice lo que
> parece razonable, gana este archivo — y si de verdad está mal, dilo
> antes de saltártelo.

---

## Stack

- **Lenguaje**: Python 3.11+, con anotaciones de tipo donde aclaren.
- **GUI**: PySide6 (Qt 6), gráficas con Matplotlib embebido.
- **Numérico**: NumPy, SciPy.
- **Agentes**: servidor MCP con el SDK `mcp` (extra `[mcp]`).
- **Tests**: runner propio `tests/_runner.py`, sin pytest.
- **Formato de proyecto**: `.ogrdata`, JSON puro.

## Comandos

Todo con el intérprete del entorno del repositorio, `.venv`
(`.venv\Scripts\python` en Windows); donde pone `python`, es ese.

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py   # toda la suite (la puerta de cada tarea)
python -m ogr_data                                  # abrir la aplicación
ogr-data-mcp --workdir ../proyectos-mcp             # servidor MCP (stdio)
python -m pip install -e ".[mcp]"                   # instalar en editable, una vez
```

En PowerShell: `$env:QT_QPA_PLATFORM='offscreen'; .venv\Scripts\python tests\_runner.py`.

`QT_QPA_PLATFORM=offscreen` es **obligatorio** en los tests: construyen
widgets reales que nunca llegan a una pantalla. Para capturas de la
ventana sin pantalla, añade `QT_QPA_FONTDIR=C:/Windows/Fonts` o el texto
sale en cuadros.

El runner no filtra: corre todo. Un test suelto se prueba importando su
archivo en un script; la evidencia de una tarea es siempre la suite entera.
Coste medido el 2026-11-24 en el PC de desarrollo: 267 tests, entre 2 y 3 min
en serie. Si crece mucho, se dice en el changelog de la spec que lo causó.

**Código de salida 127 con `Failed: 0`** (Git Bash; es 0xC0000409, un
`abort()` al cerrar el intérprete): pasa a veces con la suite entera,
también en `ba1298d` sin ningún cambio (medido el 2026-11-24: 1 de 3
corridas). Los totales son el veredicto; el aborto es una anomalía
abierta, sin diagnosticar (en OGR Slip2D la misma firma eran objetos de Qt
destruidos por el recolector, `ogr_gui/gc_guard.py`).

## Estructura

| Ruta | Contenido |
|---|---|
| `ogr_data/core/` | Cálculo puro: criterios, Hoek-Brown, ajuste, calibración, estados y rutas, simulación, USCS, base de datos, informe HTML, historial de deshacer, proyecto. **Sin Qt** |
| `ogr_data/data/` | Tablas bibliográficas versionadas (JSON/CSV), con fuente por fila |
| `ogr_data/api/` | Operaciones con nombre sin ventana (spec 019). No importa PySide6, `ogr_data.gui` ni `mcp` |
| `ogr_data/mcp_server/` | Servidor MCP: una herramienta por operación de la API |
| `ogr_data/gui/` | Ventana PySide6, diálogos, temas e `i18n/` (diccionarios `es_*.py`) |
| `tests/` | `test_<area>.py`, funciones `test_*` sin argumentos |
| `spec/constitution/` | Misión, roadmap, stack, **principios** y **guía de UX** |
| `spec/features/NNN-nombre/` | `spec.md`, `plan.md`, `tasks.md` de cada feature; `000-plantilla/` |
| `.claude/skills/` | Las fases del flujo SDD como *skills* de Claude Code (otros agentes las leen como texto) |

Capas en un solo sentido: `core → api → {gui, mcp_server}`. Una regla que
hoy solo impone la ventana se **mueve** al núcleo y la ventana la
pregunta; copiarla es cómo acaban diciendo cosas distintas.

Fuera del repositorio, en la carpeta de la suite: `../Referencias/`
(bibliografía, análisis de los programas de referencia, documentación de
terceros: nunca se publica) y `../Promps/` (prompts de desarrollo).

---

## Flujo SDD

Metodología [hello-sdd](https://github.com/mouredev/hello-sdd), como el
resto de la suite. Cada paso deja su artefacto en el repo y **termina
esperando la aprobación explícita de la propietaria**.

| # | Fase | Artefacto | Skill | Regla clave |
|---|---|---|---|---|
| 0 | Constitución | `spec/constitution/*.md` | — | Cambia poco y solo con OK |
| 1 | Especificación | `spec/features/NNN-x/spec.md` | `/sdd-spec` | Qué y por qué; RF en EARS; sin código ni stack; preguntas de una en una (máx. 6) |
| 2 | Clarificación | Lista de dudas, luego `spec.md` corregido | `/sdd-clarify` | Solo detecta: ambigüedades, contradicciones, casos límite, choques con la constitución |
| 3 | Plan | `plan.md` | `/sdd-plan` | Sin código; cada decisión con su alternativa descartada y sus RF |
| 4 | Tareas | `tasks.md` | `/sdd-tasks` | ≤ 30 min, en orden, con RF y «Hecho cuando» |
| 5 | Implementación | Código + tests | `/sdd-implement Tn` | **Una tarea**, tests primero, suite en verde, marcar `[x]` y **parar** |
| 6 | Validación | Informe RF → test → resultado | `/sdd-validate` | Veredicto con evidencia; la lista UX marcada |
| 7 | Cambio | Diff de `spec.md` | `/sdd-spec` | **Primero la spec**, se enseña el diff, luego el código |

Además, `/ux-review` revisa una pantalla o diálogo contra la
[guía de UX](spec/constitution/ux-guidelines.md) y devuelve hallazgos,
no arreglos.

Al empezar una feature, actualiza `spec/constitution/roadmap.md`; al
terminarla, márcala hecha allí.

---

## Reglas

Heredadas de las siete de OGR Slip2D (cada una salió de un problema real)
y adaptadas a este programa.

### 1. El trabajo numérico se valida contra algo EXTERNO

Una fórmula necesita un valor de referencia: un caso publicado (Hoek et
al. 2002, Hoek-Diederichs 2006…), una solución cerrada, o un programa de
referencia con su captura en `../Referencias/` (que no se nombra en el
repositorio, regla 9). **Nunca** una instantánea de lo que
el código imprime hoy: consagra el bug. Si no hay referencia, se dice en
la spec y en el test.

### 2. Todo texto visible pasa por `tr()`

```python
from ogr_data.gui.i18n import tr
label = QLabel(tr("Peak cohesion"))
```

y lleva su entrada en el `es_*.py` que toque. `tests/test_i18n.py` falla
si un texto no pasa por `tr()`, si le falta el español o si una clave
sobra. Términos geotécnicos castellanos estándar (glosario de la spec 024).

### 3. Toda acción es alcanzable desde un menú

Un botón o un menú contextual pueden ser atajos, pero la acción vive
también en la barra de menús.

### 4. Cabecera de licencia

```python
# SPDX-License-Identifier: AGPL-3.0-or-later
```

Hoy solo la lleva `ogr_data/gui/themes.py` (deuda conocida: 103 de 104
archivos sin ella). Todo archivo **nuevo** la lleva; poner la de los
existentes es una tarea aparte, con OK.

### 5. Los tests no filtran estado

Idioma, tema, unidades, `QSettings`, cachés de módulo: lo que un test
cambia, lo restaura. Un idioma olvidado en español rompe tests ajenos solo
en la suite completa.

Los ajustes del programa salen siempre de `gui.settings.app_settings()`
(nunca `QSettings(...)` a mano; un test lo impide). Con `tests/_runner.py`
van a un INI en una carpeta temporal y no tocan los del usuario; un script
que cargue tests por su cuenta debe llamar antes a
`gui.settings.isolate_for_tests(carpeta)`.

### 6. Las anomalías se reportan ANTES de corregirlas

Si algo parece incorrecto, dilo con la evidencia antes de cambiarlo. Un
arreglo rápido tapa el diagnóstico.

### 7. Ningún ajuste puede no hacer nada

Una opción que no mueve el resultado es peor que no tenerla. Si añades
una opción, añade el test que demuestra que **mueve el número**.

### 8. La interfaz cumple la guía de UX

[`spec/constitution/ux-guidelines.md`](spec/constitution/ux-guidelines.md)
(reglas U1–U17, patrones prohibidos y lista de comprobación). Toda spec
que toque la interfaz dice qué reglas aplica y marca la lista al validar.

### 9. Ninguna referencia a Rocscience ni a sus productos

Regla de la propietaria (2026-11-24). Ni la empresa ni sus programas
(RocData, RSData, RS2, RS3, Slide, RocPlane, RocProp…) se nombran en el
código, los comentarios, la interfaz, la ayuda, los datos que se
distribuyen, los tests ni la documentación del repositorio. Sus manuales
se pueden **leer** en `../Referencias/` para entender qué hace una
función, pero **no se citan**: las fórmulas se citan por su fuente
científica original, y lo que solo documenta ese fabricante queda sin
fuente hasta encontrar una citable. Donde haga falta, «el programa de
referencia». Las menciones que quedan de antes de la regla las retira la
spec 027.

---

## Forma de trabajar

- **Antes de una tarea no trivial, propón un plan y espera el OK.**
- **Una tarea a la vez.** Al terminar, di qué cambiaste y qué probaste.
- **Si no estás seguro al 80 %, pregunta. No inventes**, sobre todo en
  fórmulas: una ecuación plausible pero incorrecta es el peor resultado
  posible, porque parece que funciona.
- **Sé escéptico con lo que te piden.** Si algo huele mal, dilo.
- Commit y push solo cuando la propietaria lo pida.

## Al terminar cualquier tarea

1. Ejecuta la suite entera y confirma en tu respuesta `Failed: 0`.
2. Marca la tarea `[x]` en su `tasks.md`.
3. Di qué RF cubre, qué probaste y qué falta por probar.
4. Para. No empieces la siguiente.

---

## No hagas

- **No implementes nada que no esté en una spec aprobada**, ni edites
  `spec/` fuera del flujo SDD sin que se pida.
- **No instales dependencias sin preguntar**, y comprueba que su licencia
  es compatible con AGPL.
- **No uses `pytest`**: no está instalado; el runner es `tests/_runner.py`.
- **No abras diálogos modales en código que ejecute un test**: bloquean
  sin pantalla. La ventana tiene ganchos para los tests (p. ej.
  `ask_unsaved`).
- **No cambies el formato `.ogrdata` ni el contrato del portapapeles**
  sin actualizar antes su spec (007/011 y 005); los ficheros viejos deben
  seguir abriendo.
- **No toques los tests de validación** (soluciones cerradas, casos
  publicados, programas de referencia) para hacer pasar un cambio: si fallan, el fallo está en el código.
- **No añadas telemetría ni llamadas de red.**
- **No cambies `LICENSE`** ni las cabeceras SPDX sin pedirlo.
- **No copies texto de manuales comerciales** (`../Referencias/`): se
  leen para entender qué hace una función; las fórmulas se citan por su
  fuente científica original.

## Convenciones de código

- Comentarios que explican **por qué**, no qué; la spec que motiva un
  bloque se cita (`# spec 017: …`).
- Docstrings en funciones públicas, **con la referencia de toda fórmula**
  (autor y año).
- Nombres en inglés en el código; español solo en `gui/i18n/` y en `spec/`.
- Unidades internas: kPa, kN/m³, m, grados. La conversión a la unidad de
  pantalla (spec 017) se hace solo en la interfaz.
- Desplegables con valor guardado: texto traducido, valor en `itemData`
  (se lee con `currentData()`, nunca por el texto).

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
