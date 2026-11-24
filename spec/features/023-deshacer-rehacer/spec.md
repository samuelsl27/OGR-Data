# Spec 023 — Deshacer y rehacer (historial de ediciones del proyecto)

## Qué se construye

Hoy ninguna edición tiene vuelta atrás: cambiar de criterio (que repone
los parámetros por defecto), aplicar un ajuste, borrar un material o
cerrar un diálogo de estados de fallo pierde lo anterior sin aviso. Y el
programa tampoco sabe si hay cambios sin guardar: «New Project», «Load…»
y «Exit» descartan el trabajo en silencio.

1. **Edit > Undo / Redo** con los atajos estándar (Ctrl+Z; Ctrl+Y y
   Ctrl+Shift+Z) y el texto de la acción en el menú («Undo Change GSI»,
   «Redo Delete Material»), deshabilitados cuando no hay nada que
   deshacer o rehacer. Profundidad: al menos 100 pasos por proyecto.
2. **Qué es un paso** (una acción del usuario = un paso):
   - un valor del formulario confirmado (al terminar de editar el campo,
     no cada tecla ni cada clic de las flechas: los cambios seguidos del
     mismo campo se agrupan);
   - cambiar de criterio, de rango σ3max o de aplicación (túnel/talud);
   - añadir (también desde plantilla, base de datos, USCS, calibración,
     pegar o importar `.roc`), duplicar, renombrar y borrar materiales;
     cambiar color, símbolo o visibilidad;
   - aceptar un diálogo que edita datos (estados de fallo, rutas de
     tensión, simulaciones de ensayo, rigidez, opciones de gráfica del
     proyecto): un paso por diálogo aceptado, cancelar no deja paso;
   - aplicar un ajuste (Fit to Data → Apply) y elegir un valor con un
     selector (pick de σci, GSI, mi, D, Ei...);
   - el título del proyecto.
3. **Qué no es un paso**: las preferencias de la ventana (tema, unidad de
   visualización, idioma de la spec 024), la selección del material
   activo, los muestreadores y superposiciones de la gráfica, las vistas
   del informe y los cálculos (Compute, simulaciones): no cambian el
   proyecto o no se guardan en él.
4. **Cambios sin guardar**: asterisco en el título de la ventana
   (`OGR Data - Título*`) mientras el proyecto difiere del último
   guardado o cargado; deshacer hasta ese punto lo quita. «New Project»,
   «Load…», «Exit» y cerrar la ventana preguntan Guardar / Descartar /
   Cancelar si hay cambios. Guardar o cargar no vacía el historial de
   deshacer (salvo cargar otro proyecto, que empieza uno nuevo).
5. **Núcleo sin Qt** (como pide la constitución y la spec 019): el
   historial es un módulo de `ogr_data.core` que guarda instantáneas del
   proyecto; la ventana solo lo alimenta y lo dibuja. Así la API (spec
   019) puede ofrecer el mismo deshacer más adelante (`project_history`,
   como Slip2D) y es requisito del modo `--attach`.

## Criterios de aceptación

- Para cada tipo de paso de la lista 2: hacer → deshacer devuelve el
  proyecto exactamente al estado anterior (`to_dict()` idéntico) y la
  ventana lo muestra (formulario, árbol de materiales, gráficas);
  rehacer vuelve al estado posterior. Tests offscreen por tipo.
- Una edición nueva tras deshacer borra la rama de rehacer.
- Escribir «45» en el campo GSI y salir del campo es UN paso; diez clics
  en la flecha del mismo campo seguidos, también uno.
- El texto del menú nombra la acción; sin historial, las dos acciones
  están deshabilitadas.
- Asterisco y pregunta al salir/cargar/nuevo exactamente cuando hay
  cambios respecto al fichero; deshacer hasta el punto guardado lo quita.
- Rendimiento: una instantánea de un proyecto de 20 materiales con datos
  de ensayo tarda menos de 50 ms (no se nota al editar).
- La suite existente sigue en verde (las acciones existentes cambian de
  camino, no de resultado).

## Decisiones para el plan

- **Instantánea**: copia profunda del `Project` (lo que hace Slip2D en
  `ogr_api/snapshot.py`, que descarta el ida y vuelta por JSON porque su
  cargador migra valores) frente a `to_dict()`/`from_dict()`. En OGR-Data
  `Material.__post_init__` completa parámetros con los defaults: hay que
  comprobar que el ida y vuelta es identidad o usar `copy.deepcopy`.
- **Agrupar ediciones del formulario**: por campo y material, cerrando el
  grupo al cambiar de campo, de material o tras una acción de menú.
- **Dónde se registran los pasos**: un único punto de entrada en la
  ventana (p. ej. `self._edit("Change GSI", fn)`) en vez de repartir
  llamadas por todos los manejadores.
- Si la API (019) incorpora ya `project_history` (undo/redo/list) en esta
  spec o se deja para la de `--attach`.

## Fuera de alcance

- Deshacer las preferencias (tema, unidades, idioma) y las vistas del
  informe.
- Guardar el historial en el fichero `.ogrdata`.
- El modo `--attach` del servidor MCP (lo habilita, no lo incluye).

## Referencias

- OGR-Slip2D: `ogr_api/workspace.py` (`mutate`: cada escritura es un paso
  atómico de deshacer), `ogr_api/snapshot.py` (copias sin ida y vuelta
  por JSON), `ogr_api/ops/history.py`, y `ogr_core/project/commands.py`
  (patrón Command). OGR-Data no depende de ogr-core: se adapta el patrón,
  no se importa.
- El programa de referencia tiene Edit > Undo · Redo y un grupo Undo/Redo en la barra
  de herramientas (`03_interfaz_y_menus.md` del análisis privado del programa de referencia en
  `Referencias/Ejemplos/`); `05_profundizacion.md` lo dejó sin spec
  («Edit: Undo/Redo | — | —»). Qué acciones deshace el programa de referencia no está
  documentado: comprobarlo con el programa al hacer el plan.
