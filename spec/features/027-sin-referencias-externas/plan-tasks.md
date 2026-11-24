# Plan, tareas y validación 027 — Sin referencias al fabricante

Aprobada el 2026-11-24 («sí, las apruebo»), con el alcance de la regla 9:
código, datos, tests, README y documentos de `spec/`; la historia de git
no se toca.

## Decisiones

| Decisión | Motivo |
|---|---|
| Test que recorre todos los archivos versionados (`tests/test_spec_027.py`) | La regla tiene que fallar sola, no depender de la atención |
| Excepciones: `AGENTS.md` (la regla), esta spec, la etiqueta con que empieza un `.roc` (`roc_import.FORMAT_TAG`) y los patrones de los tests que hacen cumplir la regla; cada línea exenta lleva `rule 9:` | El importador tiene que comparar la etiqueta del formato |
| Los tests localizan los ejemplos `.roc` buscándolos en `../Referencias` (`tests/_references.py`) | Las carpetas privadas llevan el nombre del producto que documentan y no se renombran |
| Las citas de manuales del fabricante pasan a «(as in the reference program)» o a su fuente científica si ya estaba nombrada | Regla 9: no se citan |
| Los registros de la base de datos con «publisher» del fabricante pierden ese campo | Era la única mención en datos distribuidos |

## Tareas

- [x] **T1** Test de la regla
- [x] **T2** Código, datos, tests y README (52 archivos y `tests/_references.py`)
- [x] **T3** Documentos de `spec/` (58 archivos)
- [x] **T4** Validación

## Validación (2026-11-24)

Suite entera: **274 tests, 0 fallos**, con `test_no_vendor_name_in_the_repository` en verde.

## Qué se perdió

- Los números de página y de ecuación de los manuales del fabricante que
  se citaban (ya no se pueden rastrear desde el repositorio; siguen en las
  referencias privadas).
- Donde la historia distinguía los dos programas de referencia, ahora dice
  «el programa de referencia antiguo» y «el programa de referencia».
