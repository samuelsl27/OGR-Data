# Spec 007 — Proyectos e importación de archivos `.roc`

## Qué se construye

1. **Persistencia propia**: archivos `.ogrdata` (JSON versionado
   `ogr-data-project/1`) con nombre, criterio, parámetros (kPa) y sig3max.
   Botones Save / Load en la ventana principal.
2. **Importación de archivos `.roc`** (del programa de referencia antiguo): parser del formato de texto `.roc`
   (versión 3.013 observada), documentado por los 11 ejemplos oficiales de
   `Referencias/Doc_Guia/Doc_Roc_Data3_0/Examples`:
   - `failure criterion`: 0 = Hoek-Brown (GHB), 1 = Mohr-Coulomb,
     2 = Barton-Bandis, 3 = Power Curve.
   - `units: 0` = MPa (la única observada; otros códigos → error claro).
   - Secciones de parámetros por criterio + `sig3max` + bloques
     `lab data` / `rock mass data` con los pares de puntos.
   - Conversión MPa → kPa al registro. Botón "Import .roc…" que rellena
     criterio, parámetros, nombre (título) y sig3max.

## Criterios de aceptación

1. Round-trip `.ogrdata`.
2. Los 10 archivos `.roc` de ejemplo importan con el criterio esperado y
   parámetros correctos (p. ej. Granite: GHB, sigci 369270 kPa; 7 puntos
   de datos triaxiales con el primer par (−21, 30) MPa).
3. Unidades distintas de MPa → error claro, no importación silenciosa.
4. Tests sin Qt; humo offscreen de los tres botones.

## Fuera de alcance

- Multi-materiales por proyecto (el modelo de proyecto del programa de referencia con árbol
  de materiales es una fase posterior; hoy un archivo = un material).
- Re-importar los puntos de ensayo al diálogo de ajuste (los datos se
  parsean y quedan accesibles programáticamente).
- Exportación a `.roc` (solo importación).
