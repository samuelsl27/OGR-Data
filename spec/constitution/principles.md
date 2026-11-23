# Principios innegociables

Toda spec, plan y tarea de OGR-Data los cumple. Si una tarea no puede
cumplir alguno, se para y se pregunta a la propietaria.

1. **La spec manda.** No se implementa nada que no esté en una spec
   aprobada. Si falta una decisión, se marca
   `[NECESITA ACLARACIÓN: …]` y se pregunta; no se rellena inventando.
2. **Cambio = primero la spec.** Un requisito nuevo o distinto actualiza
   el `spec.md` (y se enseña el diff) antes de tocar el código.
3. **Números con referencia externa.** Toda fórmula se valida contra una
   fuente publicada, una solución cerrada o un programa de referencia
   (ORMAS, manuales de RSData/RS2), nunca contra lo que el código imprime
   hoy. Una fórmula plausible pero incorrecta es el peor resultado.
4. **Cálculo separado de la interfaz.** `ogr_data.core` no conoce Qt,
   unidades de usuario ni idiomas; `ogr_data.api` no importa PySide6 ni
   `ogr_data.gui`. La ventana pregunta al núcleo; no copia sus reglas.
5. **Tests como puerta.** Cada tarea termina con la suite en verde. Se
   prohíbe avanzar con tests en rojo.
6. **La interfaz respeta al usuario.** Cumple la
   [guía de UX](ux-guidelines.md): resultado a la vista, deshacer antes
   que preguntar, convenciones de la plataforma, accesible y sin
   patrones engañosos.
7. **Datos abiertos y locales.** Proyectos `.ogrdata` en JSON legible,
   portapapeles con contrato documentado, sin red ni telemetría.
8. **Idioma.** Código, identificadores, API y ficheros en inglés; la
   interfaz en inglés y español (spec 024); specs y notas en español.
