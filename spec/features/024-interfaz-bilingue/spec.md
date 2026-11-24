# Spec 024 — Interfaz en inglés y español

## Qué se construye

La interfaz de OGR-Data está solo en inglés (los nombres del programa de referencia).
Buena parte de quienes la usarán trabajan en español,
y la suite ya tiene el precedente de OGR-Slip2D (`ogr_gui/i18n`, ~1200
textos traducidos) y, en este programa, las cartas GSI bilingües de la
spec 022. El roadmap lo tenía apuntado como «i18n (la suite programa en
inglés; decidir idioma de UI)»: la decisión es **UI en dos idiomas,
código en inglés**.

1. **Selector de idioma** en View > Language: English / Español. Se
   guarda en `QSettings("OpenGeoRock", "OGR-Data")` (clave `language`).
   Primer arranque: español si el idioma del sistema es español, inglés
   en otro caso.
2. **Separador decimal según el idioma** (decisión del propietario,
   23-11-2026): coma en español y punto en inglés, sea cual sea la
   configuración regional de Windows, en los campos numéricos (se puede
   escribir con coma o con punto), las gráficas, los resultados, las tablas
   de los diálogos y el informe HTML.
3. **Qué se traduce** (todo lo que el usuario lee en la ventana):
   - menús, acciones, pestañas, botones, títulos de ventana y diálogos,
     etiquetas, textos de ayuda (tooltips), mensajes de la barra de estado
     y de los cuadros de aviso/error;
   - el formulario de materiales: nombres de criterios y de parámetros
     (registro de `core/models.py`), opciones de los desplegables
     (p. ej. métodos de Erm, tipos de ensayo, drenado/no drenado);
   - las gráficas: títulos, ejes y leyendas (`sigma3`, `sigma1`, «normal
     stress»… en su forma española), y los textos del editor de gráficas;
   - los diálogos de estimación (σci, GSI, mi, D, MR, Barton, USCS), de
     ajuste, calibración, estados de fallo, rutas, simulación, base de
     datos e informe;
   - **el informe HTML** se escribe en el idioma de la interfaz
     (secciones, rótulos de tablas, nombres de parámetros);
   - las cartas GSI digitalizadas (spec 022) toman por defecto el idioma
     de la interfaz; su selector propio se mantiene.
4. **Qué no se traduce**:
   - el contenido de las tablas bibliográficas y de la base de datos
     (nombres de rocas de Hoek, descripciones de D y MR, registros CANMET
     y MnDOT, textos UFC): se citan en el idioma de la fuente; traducirlos
     sería poner en boca de la fuente lo que no dice. Excepción: lo que ya
     es bilingüe (cartas GSI);
   - la API, el servidor MCP, la línea de órdenes, los mensajes de log,
     el código y la documentación del repositorio (regla de la suite);
   - los ficheros: `.ogrdata`, CSV y el contrato del portapapeles no
     cambian con el idioma (un proyecto guardado en español abre igual en
     inglés);
   - los ficheros de datos: CSV, portapapeles y `.ogrdata` escriben los
     números con punto en los dos idiomas (lo que se pega en otro programa
     o se lee de nuevo no cambia con el idioma).
5. **Terminología**: un glosario único, coherente con el de las cartas GSI
   (spec 022: macizo rocoso, discontinuidad, meteorizado/alterado,
   «espejos de falla»…) y con el de OGR-Slip2D cuando el término es común
   (cohesión, ángulo de rozamiento, peso específico, tensión efectiva).
   Donde el nombre del programa de referencia es la referencia del usuario (criterios,
   «Failure State», «Stress Path»), el texto español lleva el nombre
   inglés en el tooltip.
6. **Mecanismo** (a fijar en el plan, con Slip2D como punto de partida):
   `tr("texto inglés")` con diccionarios Python en `ogr_data/gui/i18n`,
   el inglés como clave (la interfaz inglesa no cambia ni un carácter).
   El núcleo no conoce idiomas (constitución): los textos que viven en el
   núcleo (etiquetas del registro, secciones del informe) se traducen en
   la capa de interfaz o el informe recibe el idioma como parámetro.

## Criterios de aceptación

- En español no queda ningún texto visible en inglés salvo la lista
  permitida (nombres propios, unidades, símbolos, nombres del programa de referencia entre
  paréntesis o en tooltips, contenido bibliográfico). Un test offscreen
  abre la ventana y cada diálogo, recorre sus widgets y comprueba que todo
  texto está traducido o en la lista permitida.
- En inglés la interfaz es idéntica a la actual (la suite existente pasa
  sin tocar sus textos esperados).
- Cambiar de idioma conserva el proyecto, la selección, las gráficas y el
  historial de deshacer (spec 023); si el cambio pide reiniciar la
  ventana, lo dice y no pierde nada.
- Ninguna clave del diccionario sin usar y ninguna llamada a `tr()` sin
  traducción española (test).
- El informe HTML generado en español tiene secciones y rótulos en
  español y los mismos valores numéricos que en inglés.
- Abrir en inglés un `.ogrdata` guardado en español (y al revés) da el
  mismo proyecto.

## Decisiones para el plan

- Cambio de idioma en caliente (retraducir la ventana abierta) o al
  reiniciar la ventana; Slip2D como referencia de lo que funcionó.
- Diccionarios Python (como Slip2D) frente a Qt Linguist (.ts/.qm).
- Cómo traducir los textos del núcleo sin que el núcleo importe la
  interfaz (tabla de traducción en la GUI por clave del registro, o un
  parámetro `lang` en `core/report.py`).
- Si los mensajes de error que el núcleo lanza (ValueError con texto
  inglés) se muestran traducidos (catálogo de mensajes) o tal cual con un
  rótulo español delante.

## Fuera de alcance

- Otros idiomas (la estructura debe permitirlos, sin traducirlos aún).
- Traducir el contenido bibliográfico y la base de datos.
- Traducir la API / MCP.

## Referencias

- OGR-Slip2D: `ogr_gui/i18n/__init__.py` (`tr()`, diccionario `es`,
  `add_translations`) y su diálogo de preferencias.
- Spec 022: glosario de las cartas GSI
  (`Referencias/Bibliografia/Rocas/flysch 2000 y heterogénea 2013/README.md`)
  y bloque `i18n` de `ogr_data/data/gsi_digitized_*.json`.
- Constitución, `tech-stack.md`: «Idioma: código y docs del repo en
  inglés»; «el núcleo no conoce Qt, unidades de usuario ni idiomas».
