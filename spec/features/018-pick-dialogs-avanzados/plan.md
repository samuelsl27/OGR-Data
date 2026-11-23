# Plan 018 — Pick dialogs avanzados (Barton y c/φ numéricos)

Regla de la casa: solo fuentes oficiales verificables, transcritas desde
las imágenes de las páginas; lo que no tiene fuente libre queda anotado.

## Fuentes (descargadas a `Referencias/Bibliografia/`)

1. **FHWA-TS-89-045 (1989)**, *Rock Slopes: Design, Excavation,
   Stabilization*, U.S. DOT / FHWA (dominio público; ROSA P dot:42214)
   → `Rocas/FHWA-TS-89-045_Rock-Slopes_Design-Excavation-Stabilization_1989.pdf`.
   - p. 5.18, tabla al margen «Approximate values for the basic friction
     angle φ for different rocks» (según Barton): 14 rocas; el valor
     menor corresponde, en general, a superficies húmedas (tal cual
     impreso) → `data/basic_friction_angle.json`.
   - p. 5.17, Tabla II «Approximate classification of cohesive soil and
     rock»: grados de suelo S1–S5 con su resistencia a compresión simple
     → `data/soil_field_strength.json` (valor de pick = punto medio del
     rango en MPa; S1, abierto, toma su límite superior).
   - La Tabla III (rellenos de juntas) no es utilizable: celdas cortadas
     en el escaneado. No se transcribe.
2. **UFC 3-220-01N (2005)**, *Geotechnical Engineering Procedures for
   Foundation Design of Buildings and Structures* (DoD, dominio público;
   sustituido por UFC 3-220-01, las páginas llevan la marca CANCELLED;
   es la heredera de NAVFAC DM 7) →
   `Suelos/UFC_3-220-01N_2005_Geotechnical-Engineering-Procedures.pdf`.
   Tabla 8-3.1 «Typical Engineering Properties of Compacted Materials»
   (pp. 8-53 a 8-55, datos USBR): por grupo USCS, peso unitario seco
   máximo, humedad óptima, compresibilidad, **cohesión compactada y
   saturada, φ' (envolvente efectiva)**, permeabilidad, CBR y módulo de
   balasto → `data/uscs_compacted_properties.json` (15 grupos). **SP no
   figura** en la tabla; GM, GC, OL y OH no tienen cohesión o φ
   («-----», datos insuficientes). «>38» se usa como 38 (cota inferior).
3. **Hoek, *Practical Rock Engineering* 2023**, capítulo de resistencia
   al corte de discontinuidades (ya en la biblioteca): ec. 5
   φr = (φb − 20) + 20 r/R (martillo Schmidt: r en la junta húmeda
   meteorizada, R en superficie serrada seca sana), ecs. 6 y 7 de
   Barton y Bandis (1982): JRCn = JRC0 (Ln/L0)^(−0,02 JRC0) y
   JCSn = JCS0 (Ln/L0)^(−0,03 JRC0), L0 = 100 mm.

**Sin fuente libre**: los perfiles tipo de JRC (Barton y Choubey 1977,
fig. 5 del capítulo) son una figura con copyright; no se reproducen. El
diálogo de JRC pide JRC0 y remite a la figura del libro.

## Núcleo

- `core/barton.py`: `phi_r_from_schmidt`, `jrc_scaled`, `jcs_scaled`;
  `compacted_properties` (con equivalencias CL-ML → ML-CL y SC-SM →
  SM-SC), `phi_value` y `mohr_coulomb_from_symbol` (c en kPa, φ en °;
  error explícito si el grupo no está o no tiene datos).
- `core/tables.py`: cargadores de las tres tablas nuevas.

## GUI

- Registro: Barton-Bandis φr → `barton_phi`, JRC → `barton_jrc`, JCS →
  `barton_jcs`; Mohr-Coulomb y Softening-Hardening c y φ pico →
  `compacted_soil`.
- `PhiRDialog`: tabla φb con superficie seca/húmeda y φr = φb o la
  corrección de Schmidt (ec. 5).
- `JrcDialog`: JRC0, L0 y Ln con la corrección de escala (ec. 6).
- `JcsDialog`: grados de roca R0–R6 (Hoek, Tabla 2) y de suelo S1–S5
  (FHWA, Tabla II) con filtro Rock/Soil; JCS0 editable en la unidad de
  visualización, corrección de escala (ec. 7) con el JRC actual; devuelve
  kPa.
- `CompactedSoilDialog`: tabla UFC; devuelve c y φ a la vez (cohesión
  saturada o compactada). `MainWindow._pick` admite resultados dict que
  rellenan varios campos (`set_form_values`, en kPa → unidad visible).
- Clasificador USCS: fila numérica de la UFC para la clase obtenida y
  botón **Create Mohr-Coulomb material** (c' saturada, φ'; residual =
  pico) → `MainWindow.add_soil_material`. Se corrige de paso que una
  entrada incoherente (finos + arena > 100 %) lanzara una excepción en
  el slot: ahora se muestra el mensaje.
