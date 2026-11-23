"""Spanish of the estimation dialogs (spec 024): GSI, mi, D, MR, sigci, Barton-Bandis, compacted soils, USCS.

Only the interface texts: the content of the bibliographic tables (rock names,
D and MR descriptions, UCS grades, USCS properties, sources) is cited in the
language of the source and is not here. The digitized GSI charts carry their
own English / Spanish texts (``ogr_data/data/gsi_digitized_*.json``).
"""

ES = {
    # --- GSI dialog (estimation.GsiDialog)
    "Pick GSI": "Elegir GSI",
    "Chart 2000 (selector)": "Carta 2000 (selector)",
    "Chart 2000 (click)": "Carta 2000 (clic)",
    "Heterogeneous (V. Marinos 2007)": "Heterogénea (V. Marinos 2007)",
    "Quantified chart 2013": "Carta cuantificada 2013",
    "Calculator 2013": "Calculadora 2013",
    "Click on the chart: GSI = 1.5 JCond89 + RQD/2 (Hoek, Carter & Diederichs 2013).":
        "Clic en la carta: GSI = 1.5 JCond89 + RQD/2 (Hoek, Carter & Diederichs 2013).",
    "Sources: Hoek & Marinos (2000); Marinos & Hoek (2001), flysch; V. Marinos (2007), in Marinos (2014), "
    "JRMGE 6(3), Fig. 3; {0} Digitized charts: redrawn from isolines digitized from the sources "
    "(max. error 1.3 GSI at the control points).":
        "Fuentes: Hoek & Marinos (2000); Marinos & Hoek (2001), flysch; V. Marinos (2007), en Marinos (2014), "
        "JRMGE 6(3), fig. 3; {0} Cartas digitalizadas: redibujadas a partir de las isolíneas digitalizadas de las "
        "fuentes (error máximo de 1.3 GSI en los puntos de control).",
    "English (original)": "Inglés (original)",
    "Chart text / Texto de las cartas:": "Texto de las cartas:",
    "RQD from core logging": "RQD de la testificación de sondeos",
    "From discontinuities per metre, lambda (eq. 4)": "A partir de las discontinuidades por metro, lambda (ec. 4)",
    "From volumetric joint count Jv (eq. 6, Palmstrom 2005)":
        "A partir del índice volumétrico de diaclasas Jv (ec. 6, Palmstrom 2005)",
    "From volumetric joint count Jv (eq. 5, Palmstrom 1982)":
        "A partir del índice volumétrico de diaclasas Jv (ec. 5, Palmstrom 1982)",
    "Method": "Método",
    "Jv (joints/m3)": "Jv (diaclasas/m3)",
    "RQD used": "RQD empleado",
    "Joint condition": "Condición de las discontinuidades",
    "JCond89 (eq. 1)": "JCond89 (ec. 1)",
    "JCond89 from Table 1 ratings (eq. 1)": "JCond89 a partir de las valoraciones de la tabla 1 (ec. 1)",
    "JCond76 (eq. 2)": "JCond76 (ec. 2)",
    "Jr / Ja (eq. 3)": "Jr / Ja (ec. 3)",
    "(enter value)": "(introducir valor)",
    "Condition": "Condición",
    "JCond89 = {0:g} (sum of ratings); GSI = 1.5 x {0:g} + {1:.2f}/2":
        "JCond89 = {0:g} (suma de valoraciones); GSI = 1.5 x {0:g} + {1:.2f}/2",
    "GSI = {0:.1f} (chart 2000)": "GSI = {0:.1f} (carta 2000)",
    "Click on the chart.": "Clic en la carta.",
    "Not applicable here (N/A): pick another cell.": "No aplicable aquí (N/A): elija otra celda.",
    # --- table pickers (FilteredTableDialog, pickers.TablePickerDialog)
    "Filter…": "Filtrar…",
    "All ({0})": "Cualquier {0}",
    "Source: {0}": "Fuente: {0}",
    "Pick mi — Hoek-Brown constant for intact rock (Hoek, Table 3)":
        "Elegir mi — constante de Hoek-Brown de la roca intacta (Hoek, tabla 3)",
    "Pick D — disturbance factor (Hoek, Practical Rock Engineering 2023, Fig. 9)":
        "Elegir D — factor de perturbación (Hoek, Practical Rock Engineering 2023, fig. 9)",
    "Pick Ei — modulus ratio MR (Hoek, Practical Rock Engineering 2023, Fig. 13)":
        "Elegir Ei — relación de módulos MR (Hoek, Practical Rock Engineering 2023, fig. 13)",
    "Pick sigci — field estimates of UCS (Hoek, Table 2)":
        "Elegir sigci — estimación de campo de la resistencia a compresión simple (Hoek, tabla 2)",
    # column headers chosen by the program (the cells are cited data)
    "rock": "roca",
    "rock_type": "tipo de roca",
    "class": "clase",
    "group": "grupo",
    "texture": "textura",
    "application": "aplicación",
    "case": "caso",
    "description": "descripción",
    "MR range": "intervalo de MR",
    "MR used": "MR empleado",
    "note": "nota",
    "grade": "grado",
    "term": "término",
    "symbol": "símbolo",
    "soil_type": "tipo de suelo",
    "c' compacted (kPa)": "c' compactado (kPa)",
    "c' saturated (kPa)": "c' saturado (kPa)",
    "dry unit weight g/cm3 (pcf)": "peso específico seco g/cm3 (pcf)",
    "Grade": "Grado",
    "Term": "Término",
    "UCS range": "Intervalo de UCS",
    "Examples": "Ejemplos",
    "Rock": "Roca",
    "Soil": "Suelo",
    "Type": "Tipo",
    "Class": "Clase",
    "Group": "Grupo",
    "Texture": "Textura",
    # --- modulus ratio
    "MR (modulus ratio)": "MR (relación de módulos)",
    # --- GSI 2000 selector (pickers.GsiPickerDialog)
    "Pick GSI — Hoek & Marinos (2000) chart": "Elegir GSI — carta de Hoek & Marinos (2000)",
    "Structure of the rock mass": "Estructura del macizo rocoso",
    "Surface condition of discontinuities": "Condición de la superficie de las discontinuidades",
    "Combination not present on the published chart (N/A).": "Combinación que no figura en la carta publicada (N/A).",
    "Indicative GSI range on the chart: {0:.0f}–{1:.0f}": "Intervalo orientativo de GSI en la carta: {0:.0f}–{1:.0f}",
    # --- Barton-Bandis: phi r, JRC, JCS
    "Pick phi r — basic friction angle (FHWA 1989, after Barton)":
        "Elegir phi r — ángulo de rozamiento básico (FHWA 1989, según Barton)",
    "Dry surfaces (upper value)": "Superficies secas (valor superior)",
    "Wet surfaces (lower value)": "Superficies húmedas (valor inferior)",
    "phi r = phi b (fresh joint walls)": "phi r = phi b (paredes de la discontinuidad sanas)",
    "Weathered walls: phi r = (phi b - 20) + 20 r/R (eq. 5)": "Paredes meteorizadas: phi r = (phi b - 20) + 20 r/R (ec. 5)",
    "Surface condition": "Condición de la superficie",
    "Residual angle": "Ángulo residual",
    "r: rebound on wet weathered joint": "r: rebote sobre la discontinuidad meteorizada y húmeda",
    "R: rebound on dry unweathered sawn surface": "R: rebote sobre una superficie serrada, seca y no meteorizada",
    "{0} {1} Eq. 5: Hoek, Practical Rock Engineering 2023.": "{0} {1} Ec. 5: Hoek, Practical Rock Engineering 2023.",
    "Pick JRC — joint roughness coefficient": "Elegir JRC — coeficiente de rugosidad de la discontinuidad",
    "JRC0 at laboratory scale (visual comparison with the profiles of Barton and Choubey 1977)":
        "JRC0 a escala de laboratorio (comparación visual con los perfiles de Barton y Choubey 1977)",
    "L0, laboratory length (m)": "L0, longitud de laboratorio (m)",
    "Ln, in-situ block size (m)": "Ln, tamaño del bloque in situ (m)",
    "Source: Hoek, Practical Rock Engineering 2023 (eq. 6, Barton and Bandis 1982). The standard roughness "
    "profiles (Barton and Choubey 1977, Figure 5 of that chapter) are a copyrighted figure and are not "
    "reproduced: compare the joint with the figure in the book.":
        "Fuente: Hoek, Practical Rock Engineering 2023 (ec. 6, Barton y Bandis 1982). Los perfiles de rugosidad "
        "tipo (Barton y Choubey 1977, figura 5 de ese capítulo) son una figura protegida por derechos de autor y no "
        "se reproducen: compare la discontinuidad con la figura del libro.",
    "Pick JCS — joint wall compressive strength": "Elegir JCS — resistencia a compresión de las paredes de la discontinuidad",
    "JCS0 (laboratory scale)": "JCS0 (escala de laboratorio)",
    "Rocks: {0} Soils: {1} Scale correction: Hoek, Practical Rock Engineering 2023, eq. 7 "
    "(Barton and Bandis 1982). Weathering can reduce the joint wall strength to as low as one quarter of the "
    "intact UCS (FHWA 1989, p. 5.18, after Barton).":
        "Rocas: {0} Suelos: {1} Corrección de escala: Hoek, Practical Rock Engineering 2023, ec. 7 "
        "(Barton y Bandis 1982). La meteorización puede reducir la resistencia de las paredes de la discontinuidad "
        "hasta la cuarta parte de la resistencia a compresión simple de la roca intacta (FHWA 1989, p. 5.18, según Barton).",
    # --- compacted soils (UFC 3-220-01N)
    "Pick c and phi — typical properties of compacted soils (UFC 3-220-01N)":
        "Elegir c y phi — propiedades típicas de suelos compactados (UFC 3-220-01N)",
    "Cohesion (saturated)": "Cohesión (saturado)",
    "Cohesion (as compacted)": "Cohesión (recién compactado)",
    "Cohesion to use": "Cohesión que se usa",
    # --- USCS soil classifier
    "Soil classifier — USCS (NRCS criteria)": "Clasificador de suelos — USCS (criterios NRCS)",
    "USCS plasticity chart": "Carta de plasticidad USCS",
    "Liquid limit": "Límite líquido",
    "Plasticity index": "Índice de plasticidad",
    "A-line (PI = 0.73 (LL-20))": "Línea A (IP = 0.73 (LL-20))",
    "U-line": "Línea U",
    "Fines, passing No. 200 (%)": "Finos, pasa por el tamiz n.º 200 (%)",
    "Sand, of total sample (%)": "Arena, de la muestra total (%)",
    "Liquid limit, LL": "Límite líquido, LL",
    "Plasticity index, PI": "Índice de plasticidad, IP",
    "LL(oven dry) / LL(air dry)": "LL(secado en estufa) / LL(secado al aire)",
    "Highly organic soil (peat-like)": "Suelo muy orgánico (tipo turba)",
    "Classify": "Clasificar",
    "USCS classification": "Clasificación USCS",
    "Engineering properties (NRCS NEH 631, figure 3-22)": "Propiedades geotécnicas (NRCS NEH 631, figura 3-22)",
    "Typical strength, compacted (UFC 3-220-01N Table 8-3.1, USBR data)":
        "Resistencia típica del suelo compactado (UFC 3-220-01N, tabla 8-3.1, datos del USBR)",
    "Create Mohr-Coulomb material (c' saturated, phi')": "Crear material Mohr-Coulomb (c' saturado, phi')",
    "Typical names: {0}": "Denominaciones típicas: {0}",
    "Shear strength: {0}": "Resistencia al corte: {0}",
    "Compressibility: {0}": "Compresibilidad: {0}",
    "Workability as construction material: {0}": "Trabajabilidad como material de construcción: {0}",
    "Permeability when compacted: {0}": "Permeabilidad una vez compactado: {0}",
    "Notes:": "Notas:",
    "No class": "Sin clase",
    "{0}: not listed in UFC 3-220-01N Table 8-3.1 (no numeric values).":
        "{0}: no figura en la tabla 8-3.1 de UFC 3-220-01N (sin valores numéricos).",
    "{0}: c' as compacted {1}, c' saturated {2}, phi' {3} deg (effective envelope); max dry unit weight "
    "{4} g/cm3 (pcf). '>' = greater than the value shown.":
        "{0}: c' recién compactado {1}, c' saturado {2}, phi' {3} deg (envolvente en tensiones efectivas); peso "
        "específico seco máximo {4} g/cm3 (pcf). '>' = mayor que el valor indicado.",
}
