"""Spanish of the main window, plots, animation, stiffness, table field and graph editor (spec 024)."""

ES = {
    # ------------------------------------------------------------ menus
    "File": "Archivo",
    "New Project": "Nuevo proyecto",
    "Import .roc…": "Importar .roc…",
    "Exit": "Salir",
    "Undo": "Deshacer",
    "Redo": "Rehacer",
    "Undo {0}": "Deshacer {0}",
    "Redo {0}": "Rehacer {0}",
    "Copy material": "Copiar material",
    "Copy data": "Copiar datos",
    "Copy plot": "Copiar gráfica",
    "Materials": "Materiales",
    "Add Material": "Añadir material",
    "Add Rock Template": "Añadir plantilla de roca",
    "Add Soil Template": "Añadir plantilla de suelo",
    "Duplicate Material": "Duplicar material",
    "Rename Material": "Renombrar material",
    "Delete Material": "Eliminar material",
    "Failure States": "Estados de rotura",
    "Define Failure States…": "Definir estados de rotura…",
    "Tests": "Ensayos",
    "Define Test Simulations…": "Definir simulaciones de ensayo…",
    "Define Stress Paths…": "Definir trayectorias de tensiones…",
    "Calibrate…": "Calibrar…",
    "Compute": "Calcular",
    "Analysis": "Análisis",
    "Stress Sampler": "Muestreador de tensiones",
    "Instantaneous MC Sampler": "Muestreador de MC instantáneo",
    "Overlay MC Envelope": "Superponer envolvente de MC",
    "Overlay Mogi Line": "Superponer línea de Mogi",
    "Material Database…": "Base de datos de materiales…",
    "Report Generator…": "Generador de informes…",
    "Add View To Report": "Añadir vista al informe",
    "Manage Report View…": "Gestionar vistas del informe…",
    "View": "Vista",  # as OGR-Slip2D (and the report's "View" column)
    "Theme": "Tema",
    "Light": "Claro",
    "Dark": "Oscuro",
    "Graph Editor…": "Editor de gráficas…",
    "Help": "Ayuda",
    "About OGR Data": "Acerca de OGR Data",
    "<b>OGR Data</b> {0}<br/>Rock and soil material properties for the OpenGeoRock suite.<br/>"
    "Design language: OGR-Slip2D (QGIS-inspired).": "<b>OGR Data</b> {0}<br/>Propiedades de materiales de roca y suelo "
    "para la suite OpenGeoRock.<br/>Lenguaje de diseño: OGR-Slip2D (inspirado en QGIS).",
    # ---------------------------------------------------------- sidebar
    "Custom": "Personalizada",  # (aplicación) personalizada; same key in es_report
    "Tunnel": "Túnel",
    "Slope": "Talud",
    "Tunnel depth": "Profundidad del túnel",
    "Slope height": "Altura del talud",
    "Unit weight": "Peso específico",
    "Parameters": "Parámetros",
    "Failure criterion": "Criterio de rotura",
    "Soil classifier (USCS)…": "Clasificador de suelos (USCS)…",
    "Fit lab data…": "Ajustar datos de laboratorio…",
    "Material name": "Nombre del material",
    "Stress unit": "Unidad de tensión",
    "Project title": "Título del proyecto",
    "Application (sigma3max range)": "Aplicación (rango de sigma3max)",
    "sig3max (envelope range)": "sig3max (rango de la envolvente)",
    "Computed": "Resultados",
    "envelope not available for this criterion yet": "envolvente aún no disponible para este criterio",
    "Pick…": "Elegir…",
    "Pick": "Elegir",
    "Duplicate": "Duplicar",
    "Delete": "Eliminar",
    # ------------------------------------------------------ material tree
    "Rename": "Renombrar",
    "Automatic color": "Color automático",
    "Symbol": "Símbolo",
    "Edit Failure State…": "Editar estado de rotura…",
    "Edit Test Simulation…": "Editar simulación de ensayo…",
    "Edit Stress Path…": "Editar trayectoria de tensiones…",
    "Failure state": "Estado de rotura",
    "Test simulation": "Simulación de ensayo",
    "Stress path": "Trayectoria de tensiones",
    "Material color": "Color del material",
    # ----------------------------------------------------------- graphs
    "Principal Stresses": "Tensiones principales",
    "Shear - Normal Stresses": "Tensión tangencial - tensión normal",
    "sigma3 ({0})": "sigma3 ({0})",
    "sigma1 ({0})": "sigma1 ({0})",
    "normal stress ({0})": "tensión normal ({0})",
    "shear stress ({0})": "tensión tangencial ({0})",
    "Strength Graphs": "Gráficas de resistencia",
    "Stress Path Graphs": "Gráficas de trayectorias de tensiones",
    "Axial Stress vs Axial Strain": "Tensión axial frente a deformación axial",
    "Volumetric Strain vs Axial Strain": "Deformación volumétrica frente a deformación axial",
    "q vs Deviatoric Strain": "q frente a deformación desviadora",
    "q vs p": "q frente a p",
    "Axial Strain": "Deformación axial",
    "Axial Stress": "Tensión axial",
    "Volumetric Strain": "Deformación volumétrica",
    "Deviatoric Strain": "Deformación desviadora",
    "Copy Graph as Image": "Copiar gráfica como imagen",
    "Save Graph as Image…": "Guardar gráfica como imagen…",
    "Export Graph to Excel (CSV)…": "Exportar gráfica a Excel (CSV)…",
    "Zoom Extents": "Ajustar a la extensión",
    "Save graph as image": "Guardar gráfica como imagen",
    "PNG image (*.png);;JPEG image (*.jpg);;BMP image (*.bmp)":
        "Imagen PNG (*.png);;Imagen JPEG (*.jpg);;Imagen BMP (*.bmp)",
    "Export graph to CSV": "Exportar gráfica a CSV",
    "There is no series to export on this plot.": "Esta gráfica no tiene series que exportar.",
    # ------------------------------------------------- status and messages
    "Material Database": "Base de datos de materiales",
    "Failure state '{0}' added to {1} ({2} points from record {3}).":
        "Estado de rotura «{0}» añadido a {1} ({2} puntos del registro {3}).",
    "Material created from database record {0}: GSI and D keep their defaults; set them for the rock mass.":
        "Material creado a partir del registro {0} de la base de datos: GSI y D conservan sus valores por defecto; "
        "ajústelos para el macizo rocoso.",
    "Stiffness": "Rigidez",
    "Erm is computed for Generalized Hoek-Brown materials only.":
        "Erm solo se calcula para materiales de Hoek-Brown generalizado.",
    "Compute: 1 test simulation computed": "Calcular: 1 simulación de ensayo calculada",
    "Compute: {0} test simulations computed": "Calcular: {0} simulaciones de ensayo calculadas",
    ", {0} not simulated": ", {0} sin simular",
    "View added to the report (1 view)": "Vista añadida al informe (1 vista)",
    "View added to the report ({0} views)": "Vista añadida al informe ({0} vistas)",
    "Save project": "Guardar proyecto",
    "OGR Data project (*.ogrdata)": "Proyecto de OGR Data (*.ogrdata)",
    "Save failed": "Error al guardar",
    "Import RocData file": "Importar archivo de RocData",
    "Import failed": "Error al importar",
    "Unsaved changes": "Cambios sin guardar",
    "The project has unsaved changes. Save them?": "El proyecto tiene cambios sin guardar. ¿Desea guardarlos?",
    # -------------------------------------------------------- animation
    "Animation": "Animación",
    "▶ Play": "▶ Reproducir",
    "⏸ Pause": "⏸ Pausa",
    # -------------------------------------------------------- stiffness
    "Stiffness ({0})": "Rigidez ({0})",
    "CamClay Isotropic": "CamClay isótropo",
    "Elastic Parameter": "Parámetro elástico",
    "Poisson's Ratio": "Coeficiente de Poisson",
    "Young's Modulus": "Módulo de Young",
    "Shear Modulus": "Módulo de corte",
    "Shear modulus at reference": "Módulo de corte de referencia",
    "Reference pressure for shear modulus": "Presión de referencia del módulo de corte",
    "Modulus exponent": "Exponente del módulo",
    "Poisson's ratio": "Coeficiente de Poisson",
    "Minimum Shear Modulus": "Módulo de corte mínimo",
    "Young's modulus = rock mass modulus Erm (Generalized Hoek-Brown)":
        "Módulo de Young = módulo del macizo rocoso Erm (Hoek-Brown generalizado)",
    # ------------------------------------------------------ table field
    "Edit table (1 row)…": "Editar tabla (1 fila)…",
    "Edit table ({0} rows)…": "Editar tabla ({0} filas)…",
    "The table needs at least one row.": "La tabla necesita al menos una fila.",
    # ----------------------------------------------------- graph editor
    "Graph Editor": "Editor de gráficas",
    "Principal Stress Plot": "Gráfica de tensiones principales",
    "Normal/Shear Stress": "Tensión normal/tangencial",
    "Title and Axis": "Título y ejes",
    "Graph Display": "Visualización de la gráfica",
    "Series Display": "Visualización de las series",
    "default plot title": "título por defecto de la gráfica",
    "Title:": "Título:",
    "Axis Label Position": "Posición de las etiquetas de los ejes",
    "Outside": "Fuera",
    "Inside": "Dentro",
    "X-Axis:": "Eje X:",
    "Y-Axis:": "Eje Y:",
    "Axis Range": "Rango de los ejes",
    "Use Default Axis Range": "Usar el rango de ejes por defecto",
    "{0}-Axis": "Eje {0}",
    "Min:": "Mín.:",
    "Max:": "Máx.:",
    "Use Square Axis": "Usar ejes cuadrados",
    "Show grid": "Mostrar cuadrícula",
    "Series": "Serie",
    "Width": "Grosor",
    "Style": "Estilo",
    "Envelope": "Envolvente",
    "Equivalent MC": "MC equivalente",
    "MC tangent (sampler)": "Tangente de MC (muestreador)",
    "Mogi line": "Línea de Mogi",
    "{0} color": "Color: {0}",
    "default": "por defecto",
    "solid": "continua",
    "dashed": "discontinua",
    "dash-dot": "trazo y punto",
    "dotted": "punteada",
    "Language": "Idioma",
    # ------------------------------------------------ spec 025b: window layout
    "Stress range": "Rango de tensiones",
    "Results": "Resultados",
    "Results panel": "Panel de resultados",
    "Sampler": "Muestreador",
    "Toolbar": "Barra de herramientas",
    "Project Settings…": "Configuración del proyecto…",
    "No envelope for these parameters.": "No hay envolvente con estos parámetros.",
    "This criterion has no derived parameters: its strength parameters are the inputs.": (
        "Este criterio no tiene parámetros derivados: sus parámetros de resistencia son los datos de entrada."
    ),
    "Over the stress range up to sig3max = {0}.": "En el rango de tensiones hasta sig3max = {0}.",
    # ------------------------------------------------ spec 025c: menus and conventions
    "Open…": "Abrir…",
    "Save": "Guardar",
    "Save As…": "Guardar como…",
    "Recent Projects": "Proyectos recientes",
    "(none)": "(ninguno)",
    "Untitled": "Sin título",
    "Open project": "Abrir proyecto",
    "Open failed": "Error al abrir",
    "Saved {0}": "Guardado {0}",
    "{0} no longer exists: removed from Recent Projects.": "{0} ya no existe: se quita de Proyectos recientes.",
    "Keyboard Shortcuts": "Atajos de teclado",
    "Action": "Acción",
    "Shortcut": "Atajo",
    # ------------------------------------------------ spec 025d: empty states and confirmations
    "No stress paths or computed test simulations": "Sin trayectorias ni simulaciones calculadas",
    "This material has no stress paths or computed test simulations. Define one to fill these graphs:": (
        "Este material no tiene trayectorias de tensiones ni simulaciones calculadas. Defina una para ver estas gráficas:"
    ),
    "No computed test simulation to animate: define one in Tests > Define Test Simulations… and run Tests > Compute (F5).": (
        "No hay simulaciones calculadas que animar: defina una en Ensayos > Definir simulaciones de ensayo… "
        "y ejecute Ensayos > Calcular (F5)."
    ),
    "Deleted '{0}'. Undo (Ctrl+Z) brings it back.": "Eliminado «{0}». Deshacer (Ctrl+Z) lo recupera.",
    "A project keeps at least one material.": "Un proyecto conserva al menos un material.",
    "This graph has no data to export.": "Esta gráfica no tiene datos que exportar.",
    # ------------------------------------------------ spec 025f: help, accessibility, progress
    "Unit": "Unidad",
    "Typical range": "Rango típico",
    "Source": "Fuente",
    "Computing test simulations…": "Calculando las simulaciones de ensayo…",
    "Compute cancelled: {0} of {1} test simulations computed": "Cálculo cancelado: {0} de {1} simulaciones calculadas",
    "Field estimates of the uniaxial compressive strength (Hoek, Practical Rock Engineering, Table 2; grades after Brown 1981).": (
        "Estimaciones de campo de la resistencia a compresión simple (Hoek, Practical Rock Engineering, tabla 2; grados según Brown 1981)."
    ),
    "Values of the constant mi by rock group (Hoek, Practical Rock Engineering, Table 3).": (
        "Valores de la constante mi por grupo de roca (Hoek, Practical Rock Engineering, tabla 3)."
    ),
    "GSI chart (Marinos and Hoek 2000) and quantified GSI (Hoek, Carter and Diederichs 2013).": (
        "Carta del GSI (Marinos y Hoek 2000) y GSI cuantificado (Hoek, Carter y Diederichs 2013)."
    ),
    "Guidelines for the disturbance factor D (Hoek, Carranza-Torres and Corkum 2002, Table 1).": (
        "Guía para el factor de alteración D (Hoek, Carranza-Torres y Corkum 2002, tabla 1)."
    ),
    "Ei = MR x sigci, with MR after Deere (1968) and Palmstrom and Singh (2001) (Hoek, Practical Rock Engineering).": (
        "Ei = MR x sigci, con MR según Deere (1968) y Palmstrom y Singh (2001) (Hoek, Practical Rock Engineering)."
    ),
    "Basic friction angle and the residual one with the Schmidt rebound correction (FHWA 1989, after Barton).": (
        "Ángulo de rozamiento básico y el residual con la corrección del martillo Schmidt (FHWA 1989, según Barton)."
    ),
    "JRC from the profiles of Barton and Choubey (1977), with the scale correction of Barton and Bandis (1982).": (
        "JRC a partir de los perfiles de Barton y Choubey (1977), con la corrección de escala de Barton y Bandis (1982)."
    ),
    "JCS from field estimates of strength (Hoek, Table 2; FHWA 1989, Table II), with the scale correction of Barton and Bandis (1982).": (
        "JCS a partir de estimaciones de campo de la resistencia (Hoek, tabla 2; FHWA 1989, tabla II), con la corrección de escala "
        "de Barton y Bandis (1982)."
    ),
    "Typical c and phi of compacted soils by USCS group (UFC 3-220-01N, Table 8-3.1).": (
        "c y phi típicos de suelos compactados por grupo USCS (UFC 3-220-01N, tabla 8-3.1)."
    ),
}
