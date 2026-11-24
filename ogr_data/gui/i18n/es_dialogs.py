"""Spanish of the dialogs: failure states, stress paths, test simulations,
calibration, fit, material database and report generator (spec 024).

The labels that come from the core (test types, seepage, loading, symbols,
strength types, algorithms, report sections...) are in ``es_registry``.
"""

ES: dict[str, str] = {
    # ------------------------------------------------ point tables (states_dialog)
    "Cut": "Cortar",
    "Copy": "Copiar",
    "Paste": "Pegar",
    "Insert Row": "Insertar fila",
    "Delete Rows": "Eliminar filas",
    "Import…": "Importar…",
    "Export…": "Exportar…",
    "Import points": "Importar puntos",
    "Export points": "Exportar puntos",
    "CSV / text (*.csv *.txt);;All files (*)": "CSV / texto (*.csv *.txt);;Todos los archivos (*)",
    "Import failed": "Error al importar",
    "row {0}: enter a number in every column": "fila {0}: introduzca un número en cada columna",
    "Exclude": "Excluir",
    "Pore Water Pressure": "Presión intersticial",
    # ------------------------------------------------ list + editor dialogs
    "Delete": "Eliminar",
    "Duplicate": "Duplicar",
    "Up": "Subir",
    "Down": "Bajar",
    "Name": "Nombre",
    "Symbol:": "Símbolo:",
    "Test Type:": "Tipo de ensayo:",
    "Define Failure States - {0}": "Definir estados de rotura - {0}",
    "Define Stress Paths - {0}": "Definir trayectorias de tensiones - {0}",
    "Seepage Condition:": "Condición de drenaje:",
    "Loading Direction:": "Dirección de carga:",
    "Initial Effective Lateral Stress:": "Tensión efectiva lateral inicial:",
    "Initial Effective K0:": "K0 efectivo inicial:",
    "Strain Type:": "Tipo de deformación:",
    "Uniaxial: the radial stress is zero (RSData 1.009 plots p and q with a hidden 100 kPa).": (
        "Compresión simple: la tensión radial es nula (RSData 1.009 dibuja p y q con 100 kPa ocultos)."
    ),
    "Loading Direction Lateral: RSData 1.009 overwrites SigmaXX with the initial lateral stress and "
    "plots no axial stress; the path is kept but not drawn (spec 021).": (
        "Dirección de carga lateral: RSData 1.009 sobrescribe SigmaXX con la tensión lateral inicial y no "
        "dibuja tensión axial; la trayectoria se conserva pero no se dibuja (spec 021)."
    ),
    "Kept but not drawn: the stress invariants of this configuration are not verified (spec 021).": (
        "Se conserva pero no se dibuja: los invariantes de tensión de esta configuración no están verificados "
        "(spec 021)."
    ),
    # ------------------------------------------------ test simulations
    "Define Test Simulations - {0}": "Definir simulaciones de ensayo - {0}",
    "Cyclic Loading Cycles:": "Ciclos de carga cíclica:",
    "Initial Effective Lateral Stress ({0}):": "Tensión efectiva lateral inicial ({0}):",
    "Strain direction:": "Dirección de deformación:",
    "Maximum Strain:": "Deformación máxima:",
    "Number of Steps:": "Número de pasos:",
    "Initial axial stress = lateral stress / K0.": "Tensión axial inicial = tensión lateral / K0.",
    "Biaxial: plane strain (no strain in the second lateral direction); initial axial stress = lateral / K0.": (
        "Biaxial: deformación plana (sin deformación en la segunda dirección lateral); tensión axial inicial = "
        "lateral / K0."
    ),
    "Simple Shear: imposed shear strain (Maximum Strain = gamma), no lateral strains; the initial "
    "vertical stress (lateral / K0) is kept constant when drained.": (
        "Corte simple: deformación tangencial impuesta (deformación máxima = gamma), sin deformaciones "
        "laterales; la tensión vertical inicial (lateral / K0) se mantiene constante en condiciones drenadas."
    ),
    "General Test (OGR Data; RSData does not document its inputs): proportional strain path in the given "
    "direction, Maximum Strain on its largest component. Undrained keeps the volume (normal components "
    "made deviatoric); pore pressure = change of the mean effective stress.": (
        "Ensayo general (OGR Data; RSData no documenta sus datos de entrada): trayectoria de deformación "
        "proporcional en la dirección indicada, con la deformación máxima en su mayor componente. En "
        "condiciones no drenadas se conserva el volumen (componentes normales convertidas en desviadoras); "
        "presión intersticial = variación de la tensión efectiva media."
    ),
    # ------------------------------------------------ calibration
    "Calibration": "Calibración",
    "Material Model:": "Modelo de material:",
    "New Model Settings": "Configuración del nuevo modelo",
    "Strength type:": "Tipo de resistencia:",
    "Curve Fit Analysis": "Análisis de ajuste de curva",
    "Algorithm:": "Algoritmo:",
    "Error Summation:": "Suma de errores:",
    "Error Type:": "Tipo de error:",
    "Failure States": "Estados de rotura",
    "Failure States:": "Estados de rotura:",
    "Failure Data Type:": "Tipo de datos de rotura:",
    "sigci (rock mass data):": "sigci (datos de macizo rocoso):",
    "D (rock mass data):": "D (datos de macizo rocoso):",
    "direct shear": "corte directo",
    "relative": "relativo",
    "{0} triaxial points · residuals (sum of squares, vertical, {1}) = {2}": (
        "{0} puntos triaxiales · residuos (suma de cuadrados, vertical, {1}) = {2}"
    ),
    "{0} direct shear points · residuals (sum of squares, vertical, {1}) = {2}": (
        "{0} puntos de corte directo · residuos (suma de cuadrados, vertical, {1}) = {2}"
    ),
    "There are no failure states with test points yet. Calibration fits a model to "
    "them: define them in Failure States > Define Failure States…": (
        "Aún no hay estados de rotura con puntos de ensayo. La calibración ajusta un modelo "
        "a ellos: defínalos en Estados de rotura > Definir estados de rotura…"
    ),
    "Select at least one failure state with test points.": (
        "Seleccione al menos un estado de rotura con puntos de ensayo."
    ),
    # ------------------------------------------------ fit lab data
    "Fit strength criterion to lab data": "Ajustar el criterio de rotura a datos de laboratorio",
    "Paste from clipboard": "Pegar del portapapeles",
    "Add row": "Añadir fila",
    "Fit": "Ajustar",
    "Apply to material": "Aplicar al material",
    "Criterion": "Criterio",
    "Data type": "Tipo de datos",
    "Method": "Método",
    "Result": "Resultado",
    "Direct shear": "Corte directo",
    "Linear regression": "Regresión lineal",
    "sigci, fixed ({0})": "sigci, fijo ({0})",
    "D, fixed": "D, fijo",
    "phi_b, fixed (deg)": "phi_b, fijo (deg)",
    "Fit failed: {0}": "El ajuste ha fallado: {0}",
    "method: {0}": "método: {0}",
    "residuals: {0}": "residuos: {0}",
    "Note: apply fills the classic Hoek-Brown criterion (mb, s; a is fixed to 0.5 there).": (
        "Nota: aplicar rellena el criterio de Hoek-Brown clásico (mb, s; allí a se fija en 0.5)."
    ),
    # ------------------------------------------------ material database
    "Enter your search key words below. You can use wildcards * to match partial words, "
    'or include words in double quotes " to match an exact phrase.': (
        "Escriba abajo las palabras clave de la búsqueda. Puede usar comodines * para buscar palabras "
        'parciales o poner palabras entre comillas dobles " para buscar una frase exacta.'
    ),
    "Material record": "Registro de material",
    "Record": "Registro",
    "Location": "Ubicación",
    "Reference *": "Referencia *",
    "Compression Data": "Datos de compresión",
    "Tensile Data": "Datos de tracción",
    "Hoek-Brown Data": "Datos de Hoek-Brown",
    "Velocity Data": "Datos de velocidad",
    "* Reference title and author are required: a record without source is not saved.": (
        "* El título y el autor de la referencia son obligatorios: un registro sin fuente no se guarda."
    ),
    "Material Database": "Base de datos de materiales",
    "Search": "Buscar",
    "All records": "Todos los registros",
    "Built-in (bibliography)": "Integrados (bibliografía)",
    "My records": "Mis registros",
    "Favourites": "Favoritos",
    "Reset": "Restablecer",
    "New Record…": "Nuevo registro…",
    "Export Results to Excel (CSV)…": "Exportar resultados a Excel (CSV)…",
    "Export results to Excel (CSV)": "Exportar resultados a Excel (CSV)",
    "Copy to New Record…": "Copiar a un registro nuevo…",
    "Edit this Record…": "Editar este registro…",
    "Delete this Record": "Eliminar este registro",
    "Copy to Clipboard": "Copiar al portapapeles",
    "Use as Material": "Usar como material",
    "Use as Failure State": "Usar como estado de rotura",
    "☆ Favourite": "☆ Favorito",
    "★ Favourite": "★ Favorito",
    "Print / PDF…": "Imprimir / PDF…",
    "none": "ninguno",
    "Record ID {0},  Available test data: {1}": "ID de registro {0},  datos de ensayo disponibles: {1}",
    "Search Records": "Búsqueda de registros",
    "Search Records for {0}": "Búsqueda de registros: {0}",
    "Showing Results {0} - {1} of {2}": "Resultados {0} - {1} de {2}",
    "Page {0} of {1}": "Página {0} de {1}",
    "No record.": "Ningún registro.",
    "Record ID": "ID de registro",
    "Origin": "Origen",
    "built-in (bibliography, read-only)": "integrado (bibliografía, solo lectura)",
    "my records": "mis registros",
    "Location Information": "Información de ubicación",
    "Reference Information": "Información de la referencia",
    "Specimens ({0})": "Probetas ({0})",
    "Delete record": "Eliminar registro",
    "Delete record {0}?": "¿Eliminar el registro {0}?",
    # field labels of core.database (interface; the record values are data)
    "Rock Name": "Nombre de la roca",
    "Rock Name Prefix": "Prefijo del nombre de la roca",
    "Unit Weight (MN/m3)": "Peso específico (MN/m3)",
    "Density (Mg/m3)": "Densidad (Mg/m3)",
    "Porosity (%)": "Porosidad (%)",
    "Fabric": "Fábrica",
    "Notes": "Notas",
    "Region": "Región",
    "Country": "País",
    "Town/City/State": "Localidad/Ciudad/Estado",
    "Latitude": "Latitud",
    "Longitude": "Longitud",
    "Depth (m)": "Profundidad (m)",
    "Reference Type": "Tipo de referencia",
    "Author": "Autor",
    "Publisher": "Editorial",
    "Year Published": "Año de publicación",
    "Pages": "Páginas",
    "Volume": "Volumen",
    "Edition": "Edición",
    "Table / figure": "Tabla / figura",
    "Test Type": "Tipo de ensayo",
    "Core Diameter": "Diámetro del testigo",
    "Core Length": "Longitud del testigo",
    "Confining Stress": "Tensión de confinamiento",
    "Angle to Fabric Normal": "Ángulo con la normal a la fábrica",
    "Compressive Strength range": "Rango de resistencia a compresión",
    "Young's Modulus, Tangent at 50%": "Módulo de Young, tangente al 50%",
    "Young's Modulus": "Módulo de Young",
    "Poisson Ratio": "Coeficiente de Poisson",
    "Number of specimens": "Número de probetas",
    "Information Quality (1-10)": "Calidad de la información (1-10)",
    "Tensile Strength": "Resistencia a tracción",
    "s (intact)": "s (roca intacta)",
    "r² (intact fit)": "r² (ajuste de roca intacta)",
    "r² (residual fit)": "r² (ajuste residual)",
    "Confining stress range of the fit": "Rango de tensión de confinamiento del ajuste",
    "Modulus ratio MR (Ei/sigci)": "Relación de módulos MR (Ei/sigci)",
    "P-wave velocity": "Velocidad de onda P",
    "P-wave velocity (dry)": "Velocidad de onda P (seco)",
    "S-wave velocity": "Velocidad de onda S",
    "Tensile": "Tracción",
    "Velocity": "Velocidad",
    # ("Compression", "Compressive Strength" and "Title" are registry labels: es_registry)
    # ------------------------------------------------ report generator
    "Manage Report View": "Gestionar vistas del informe",
    "Manage Report View…": "Gestionar vistas del informe…",
    "Remove": "Quitar",
    "Views in report order (double-click to rename):": "Vistas en el orden del informe (doble clic para renombrar):",
    "Report Generator": "Generador de informes",
    "Untitled Project": "Proyecto sin título",
    "Section Visibility": "Visibilidad de las secciones",
    "Open in the browser after generating (Save / Print to PDF from there)": (
        "Abrir en el navegador después de generar (desde allí, Guardar / Imprimir a PDF)"
    ),
    "Generate…": "Generar…",
    "Report title": "Título del informe",
    "Empty sections are left out of the report.": "Las secciones vacías no se incluyen en el informe.",
    "{0} graph view in the report": "{0} vista de gráfica en el informe",
    "{0} graph views in the report": "{0} vistas de gráfica en el informe",
    "No graph views yet: use Analysis > Add View To Report.": (
        "Aún no hay vistas de gráficas: use Análisis > Añadir vista al informe."
    ),
    "Generate report": "Generar informe",
    "HTML report (*.html)": "Informe HTML (*.html)",
    "Report": "Informe",
    "Report written to {0}": "Informe guardado en {0}",
    # ------------------------------------------------ spec 025d: empty lists
    "Add": "Añadir",
    "Nothing here yet. Click Add to create the first one.": "Aún no hay nada. Pulse Añadir para crear el primero.",
    "No failure states yet. Click Add, then type or import the test points of the state.": (
        "Aún no hay estados de rotura. Pulse Añadir y escriba o importe los puntos de ensayo del estado."
    ),
    "No stress paths yet. Click Add, then choose the test type and type or import its readings.": (
        "Aún no hay trayectorias de tensiones. Pulse Añadir, elija el tipo de ensayo y escriba o importe sus lecturas."
    ),
    "No test simulations yet. Click Add, choose the test type and run Tests > Compute (F5).": (
        "Aún no hay simulaciones de ensayo. Pulse Añadir, elija el tipo de ensayo y ejecute Ensayos > Calcular (F5)."
    ),
}
