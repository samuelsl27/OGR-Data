# Spec 020 — Línea de diseño OGR-Slip2D (estética)

## Qué se construye

La interfaz de OGR-Data pasa a seguir la línea de diseño de OGR-Slip2D
("QGIS-inspired", verificado en `ogr_gui/themes/__init__.py` de
OGR-Slip2D), que hoy no se parece:

1. **Hoja de estilos QSS light y dark** con los mismos tokens de la
   suite: fondo `#f3f3f3`/`#2b2b2b`, selección `#b9d7f7`/`#4a5a75`,
   acento `#4a90d9`, bordes `#c0c0c0`, tooltips `#fffddc`, scrollbars de
   12 px, groupbox con título `#40607a`/`#9ab6d6`.
2. **Barra de menús** (la ventana no tenía): File (Save/Load/Import
   .roc/Exit), Edit (Copy material/Copy data), View (Theme: light/dark),
   Help (About). Los botones laterales se mantienen (espíritu viejo
   RocData) pero el programa gana la estructura de la suite.
3. **Tema persistente** (QSettings) y conmutación en caliente: la hoja
   Qt y los canvas matplotlib se actualizan juntos.
4. **Canvas matplotlib a juego**: fondo de figura según tema, ejes y
   rejilla con los colores de la suite, envolvente en azul acento
   (`#4a90d9` light / `#6aa3d5` dark), MC equivalente en `#40607a`.

## Criterios de aceptación

- Con cada tema, la hoja Qt y los dos canvas usan la paleta del tema
  (tests de tokens en el QSS y de los colores de las líneas).
- El tema elegido sobrevive a reiniciar (QSettings).
- La suite coexiste: mismos colores de selección que OGR-Slip2D (ojo al
  copiar entre repos: ambos son del mismo propietario; se copia la hoja
  con atribución).

## Fuera de alcance

- Iconos de toolbar (no hay toolbar propia aún; se decide con la spec
  de multi-material).
- Fuentes personalizadas (Slip2D no fija fuente; tampoco OGR-Data).
