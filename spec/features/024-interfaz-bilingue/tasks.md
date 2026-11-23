# Tasks 024 — Interfaz en inglés y español

- [x] Spec y plan (convenciones y glosario)
- [x] `ogr_data/gui/i18n`: `tr()`, diccionarios por zona, catálogo de Qt, idioma del sistema en el primer arranque
- [x] Ventana principal, gráficas, rigidez, tablas y editor de gráficas (`es_main.py`)
- [x] Diálogos de datos: estados, trayectorias, simulación, calibración, ajuste, base de datos, informe (`es_dialogs.py`)
- [x] Diálogos de estimación y cartas GSI (`es_estimation.py`); la carta GSI toma el idioma de la interfaz
- [x] Registro del núcleo (`es_registry.py`) e informe HTML bilingüe (`core/report.py` con `translate`/`lang`, `es_report.py`)
- [x] Textos de deshacer (`core/history.py` con plantillas, `es_history.py`)
- [x] Desplegables con valor guardado: texto traducido, valor en `itemData`
- [x] View > Language: la ventana se reabre en el idioma conservando proyecto, selección, historial y vistas
- [x] Tests: `test_i18n.py` (estático, diccionario, ventana y diálogos en español, cambio de idioma) e informe en español
- [x] Commit y push
- [x] Separador decimal según el idioma (QLocale por idioma, `localize`/`parse_number`, gráficas, resultados, tablas, informe)
- [x] Commit y push del separador
