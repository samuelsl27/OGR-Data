# Plan 004 — Clasificador USCS

## Núcleo (`core/uscs.py`, sin Qt)

- `UsCSInput` (fines_pct, sand_pct, cu, cc, ll, pi, organic_ratio, highly_organic).
- `classify(input) -> UsCSResult` (symbol, group, description, notes) siguiendo
  la fig. 3-17: gruesos limpios GW/GP (Cu>4, 1<Cc<3) y SW/SP (Cu>6);
  5–12% finos → símbolos dobles; >12% finos → GM/GC (A-line, PI 4/7);
  finos ML/CL/OL/MH/CH/OH (LL=50, A-line, ratio 0,7); PT si altamente orgánico.
- `a_line_pi(ll)` y `uscs_properties(symbol)` desde el JSON.

Decisiones: seguir NRCS (nuestra fuente citada) en los límites estrictos
(Cu>4, Cc entre 1 y 3, ratio orgánico 0,7). Símbolo triple ("GW-GM-GC")
solo en el caso límite PI 4–7 con 5–12% finos, indicado como tal.

## GUI

`gui/soil_classifier.py`: diálogo con los campos, carta de plasticidad
(QLabel con canvas matplotlib: A-line, U-line opcional, punto del suelo),
resultado con ficha y fuente. Acceso desde la ventana principal (botón en
la barra lateral).
