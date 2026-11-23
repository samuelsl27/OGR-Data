# Plan 024 — Interfaz en inglés y español

## Decisiones

- **Diccionarios Python y `tr()`** (como OGR-Slip2D, `ogr_gui/i18n`), no Qt
  Linguist: sin compilar, editable a mano. El inglés es la clave: en
  inglés `tr(x) == x` y la interfaz no cambia ni un carácter.
- **Cambio de idioma: se reabre la ventana**, en el mismo proceso, con el
  mismo proyecto, material seleccionado, historial de deshacer (spec 023),
  vistas del informe, tema y geometría. Retraducir en caliente cada widget
  obligaría a cada diálogo a reconstruir sus textos; Slip2D pide reiniciar
  el programa y el idioma no se aplica hasta entonces. Reabrir la ventana
  es inmediato y no pierde nada.
- **Textos de Qt** (Aceptar/Cancelar, Guardar/Descartar, menús contextuales
  de los campos): el catálogo `qtbase_es.qm` que trae PySide6.
- **Primer arranque**: español si `QLocale.system()` es español; si no,
  inglés. Después, lo guardado en `QSettings` (clave `language`).
- **Textos del núcleo** (etiquetas del registro de criterios, opciones de
  los desplegables, tipos de ensayo, secciones y rótulos del informe): el
  núcleo sigue sin conocer idiomas. La interfaz traduce con `tr(label)`
  (la etiqueta inglesa es la clave) y el informe recibe una función de
  traducción (`build_html(..., translate=tr)`, por defecto la identidad).
- **Desplegables con valores guardados** (opciones de los campos `enum`,
  métodos de Erm, Drained/Undrained...): el texto visible se traduce y el
  valor (inglés, el del registro y del fichero) va en `itemData`; se lee
  con `currentData()` y se busca con `findData()`, nunca por el texto.
- **Mensajes de error del núcleo** (`ValueError` en inglés): se muestran
  tal cual tras un rótulo traducido; traducirlos queda fuera de v1.
- **Datos, no interfaz**: nombres de materiales por defecto («Material»,
  «Rock», «Soil»), contenido de tablas bibliográficas y base de datos: no
  se traducen (spec, punto 3).

## Convenciones para los textos

- `from .i18n import tr` (en `ogr_data/gui`), y `tr("texto inglés")`
  SIEMPRE con un literal: nada de `tr(f"...")` ni `tr(variable)` salvo
  para etiquetas que vienen del registro (`tr(field.label)`), cuya
  traducción está en el diccionario del registro.
- Textos con datos: `tr("Delete material '{0}'?").format(name)`.
- Atajos `&` y `…` se conservan dentro de la clave.
- Un diccionario por zona en `ogr_data/gui/i18n/es_<zona>.py` (`ES = {...}`):
  `main`, `dialogs`, `estimation`, `registry` (criterios, parámetros,
  opciones, tipos), `report`. `__init__` los une; una clave repetida con
  dos traducciones distintas es un error (test).

## Glosario (coherente con la spec 022 y Slip2D)

| Inglés | Español |
|---|---|
| failure criterion / strength criterion | criterio de rotura |
| envelope | envolvente |
| principal stresses | tensiones principales |
| normal stress / shear stress | tensión normal / tensión tangencial |
| cohesion / friction angle / dilation angle | cohesión / ángulo de rozamiento / ángulo de dilatancia |
| unit weight | peso específico |
| intact rock / rock mass | roca intacta / macizo rocoso |
| uniaxial compressive strength | resistencia a compresión simple |
| tensile strength | resistencia a tracción |
| disturbance factor | factor de perturbación |
| modulus ratio | relación de módulos |
| failure state | estado de rotura (tooltip: Failure State) |
| stress path | trayectoria de tensiones (tooltip: Stress Path) |
| test simulation | simulación de ensayo |
| triaxial / direct shear / uniaxial / biaxial / simple shear test | ensayo triaxial / de corte directo / de compresión simple / biaxial / de corte simple |
| drained / undrained | drenado / no drenado |
| peak / residual | pico / residual |
| fit / calibrate | ajustar / calibrar |
| sampler | muestreador |
| report / view | informe / vista |
| stiffness / Young's modulus / Poisson's ratio | rigidez / módulo de Young / coeficiente de Poisson |
| strain / volumetric / deviatoric | deformación / volumétrica / desviadora |
| pore pressure | presión intersticial |
| tunnel depth / slope height | profundidad del túnel / altura del talud |
| material / template | material / plantilla |
| Copy / Paste / Undo / Redo | Copiar / Pegar / Deshacer / Rehacer |
| Mohr-Coulomb, Hoek-Brown, Barton-Bandis, Drucker-Prager, Cam-Clay, NorSand | se mantienen (nombres propios); «Generalized Hoek-Brown» = «Hoek-Brown generalizado», «Power Curve» = «Curva potencial», «Softening-Hardening» = «Ablandamiento-endurecimiento» |

## Comprobaciones (tests)

- **Estática** (AST de `ogr_data/gui/*.py`): ningún literal de texto pasado
  directamente a una llamada que pone texto en pantalla (`QLabel`,
  `setText`, `addAction`, `addMenu`, `addTab`, `setWindowTitle`,
  `QPushButton`, `QGroupBox`, `QCheckBox`, `setToolTip`, `addRow`,
  `setPlaceholderText`, `showMessage`, `QMessageBox.*`, `setTitle`,
  `setHorizontalHeaderLabels`, `addItem`...) sin `tr()`; ningún `tr()` con
  algo que no sea un literal (salvo los marcados).
- **Diccionario**: cada `tr("literal")` del código tiene traducción;
  ninguna clave sin uso; cada etiqueta y opción del registro, tipo de
  ensayo y sección del informe tiene traducción.
- **En vivo**: en español, la ventana y cada diálogo no muestran ningún
  texto que sea una clave inglesa del diccionario.
- En inglés, la suite existente sigue en verde sin tocar sus textos.
- Cambio de idioma: proyecto, selección, historial y vistas conservados.
- Informe en español: secciones traducidas, mismos números.
