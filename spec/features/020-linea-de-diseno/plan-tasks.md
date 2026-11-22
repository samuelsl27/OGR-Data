# Plan 020 — Línea de diseño

- `ogr_data/gui/themes.py`: hojas QSS light/dark (adaptadas de
  OGR-Slip2D `ogr_gui/themes`, mismo propietario, con atribución),
  `THEMES`, `apply_theme(app, name)` y `mpl_colors(name)` con los
  colores de las series para matplotlib.
- Persistencia con `QSettings("OpenGeoRock", "OGR-Data")`, clave
  `theme`; conmutación en caliente desde el menú View.
- `plots.py`: `EnvelopeCanvas.set_theme(colors)` recolorea figura, ejes,
  rejilla y las dos líneas (envolvente y MC) conservando los datos.
- `main_window`: QMenuBar (File/Edit/View/Help) reutilizando los
  handlers existentes; About con la versión del paquete.

# Tasks 020

- [x] Spec y plan
- [ ] themes.py (QSS + mpl colors)
- [ ] Menú, QSettings, conmutación en caliente
- [ ] Canvas reactivos al tema
- [ ] Tests; commit y push
