# Spec 005 — Portapapeles: contrato de materiales

## Qué se construye

El mecanismo de transferencia de materiales de OGR-Data a OGR-Slip2D y
OGR-FEM2D, con un **contrato abierto y documentado** (el hallazgo del
análisis fue que el formato del fabricante del programa de referencia es un objeto .NET privado e
irreproducible — ver `04_integracion.md` en el análisis privado del programa de referencia, en
`Referencias/Ejemplos/`):

1. **Formato primario**: texto Unicode con prefijo `OGR-DATA-MATERIAL:` +
   JSON:
   ```json
   OGR-DATA-MATERIAL:{"format": "ogr-material/1", "name": "Granite GHB",
     "criterion": "generalized_hoek_brown",
     "parameters": {"sigci_kpa": 50000, "gsi": 50, "mi": 32, "d": 0},
     "computed": {"mb": ..., "s": ..., "a": ...}}
   ```
   Unidades: los parámetros viajan en **kPa** (unidades del registro).
   Los programas consumidores (OGR-Slip2D, OGR-FEM2D) detectan el prefijo
   al pegar en su lista de materiales; si no está, ignoran el texto.
2. **Copia tabulada** (botón "Copy data"): resumen `nombre\tvalor` de
   parámetros y resultados calculados, para pegar en Excel (como el
   "Copy Data" del programa de referencia antiguo).
3. **Copia de imagen**: la gráfica activa al portapapeles como imagen
   (QPixmap nativo de Qt).

## Criterios de aceptación

1. Round-trip: `parse(material_text(...))` recupera criterio y parámetros.
2. Texto sin el prefijo → `None` (no se interpreta nada ajeno).
3. Versionado: campo `format: ogr-material/1`; otras versiones → error
   claro, no excepción.
4. La copia tabulada incluye todos los parámetros del criterio activo.
5. Tests sin Qt; humo offscreen de los botones.

## Fuera de alcance

- El "pegar" en OGR-Slip2D/OGR-FEM2D: esos repositorios implementan su
  lado del contrato (encargo escrito para sus sesiones, pendiente).
- Portapapeles nativo de Windows con formato propietario: innecesario, el
  contrato es texto plano deliberadamente.
