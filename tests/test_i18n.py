"""Spec 024: the interface in English and Spanish.

Static checks over ``ogr_data/gui`` (AST), dictionary checks, and live
checks of the window in Spanish. ``report(path)`` lists what is left in one
file (used while converting a file):

    python -c "import sys; sys.path.insert(0, 'tests'); import test_i18n as t; t.report('ogr_data/gui/fit_dialog.py')"
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUI = ROOT / "ogr_data" / "gui"
SKIP_FILES = {"themes.py"}  # style sheets, no user text
IGNORE_MARK = "i18n: ignore"

# call name -> indices of the positional arguments that are user-visible text
TEXT_CALLS: dict[str, tuple[int, ...]] = {
    "QLabel": (0,), "QPushButton": (0,), "QCheckBox": (0,), "QRadioButton": (0,), "QGroupBox": (0,),
    "QAction": (0,), "setText": (0,), "setWindowTitle": (0,), "addMenu": (0,), "addTab": (1,), "setTabText": (1,),
    "addItem": (0,), "insertItem": (1,), "addRow": (0,), "setPlaceholderText": (0,), "setToolTip": (0,),
    "showMessage": (0,), "setTitle": (0,), "question": (1, 2), "warning": (1, 2), "information": (1, 2),
    "critical": (1, 2), "getText": (1, 2), "getItem": (1, 2), "getDouble": (1, 2), "getInt": (1, 2),
    "getSaveFileName": (1, 3), "getOpenFileName": (1, 3), "getExistingDirectory": (1,), "getColor": (2,),
    "set_xlabel": (0,), "set_ylabel": (0,), "set_title": (0,), "suptitle": (0,), "setStatusTip": (0,),
    "setSuffix": (), "addAction": (0,), "setWhatsThis": (0,), "setHeaderLabels": (0,),
    "setHorizontalHeaderLabels": (0,), "setVerticalHeaderLabels": (0,), "addItems": (0,),
}
# words that are the same in both languages (symbols, units, acronyms, proper names)
SAME_WORDS = {
    "GSI", "RQD", "USCS", "OGR", "MPa", "kPa", "GPa", "deg", "psi", "psf", "ksf", "tsf", "Pa", "kN", "MN",
    "CSV", "PNG", "SVG", "PDF", "HTML", "JCond", "JCond89", "JCond76", "Jv", "Jr", "Ja", "RMR", "ORMAS",
    "RSData", "RocData", "RocProp", "Hoek", "Brown", "Marinos", "Mohr", "Coulomb", "Barton", "Bandis",
    "Drucker", "Prager", "Cam", "Clay", "NorSand", "Mogi", "Deere", "Carter", "Diederichs", "Priest",
    "Hudson", "Palmstrom", "Choubey", "UFC", "ASTM", "NRCS", "FHWA", "CANMET", "MnDOT", "Excel", "sigma",
    "sigma1", "sigma3", "sig3max", "sigci", "sigcm", "sigt", "sigc", "phi", "tau", "JRC", "JCS", "Erm",
    "Ei", "mb", "mi", "PRE", "ARMA", "Rocscience", "RSData's", "Data", "Copy", "Linear",
    # the same in Spanish (registry labels): directions, Cam-Clay symbols, solver names, authors
    "Axial", "Lateral", "Vertical", "Kappa", "Lambda", "OCR", "Phi", "Simplex", "Levenberg", "Marquardt",
    "Carranza", "Torres", "Corkum",
}
WORD = re.compile(r"[A-Za-z][A-Za-z']{2,}")


def _needs_translation(text: str) -> bool:
    return any(w not in SAME_WORDS for w in WORD.findall(text))


def _call_name(node: ast.Call) -> str | None:
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _is_tr(node) -> bool:
    if isinstance(node, ast.Call) and _call_name(node) == "tr":
        return True
    # tr("...").format(...)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return _is_tr(node.func.value)
    return False


def _literal_texts(node) -> list[str]:
    """User text inside an argument that is NOT already translated."""

    if node is None or _is_tr(node):
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return ["".join(v.value for v in node.values if isinstance(v, ast.Constant))]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [t for e in node.elts for t in _literal_texts(e)]
    if isinstance(node, ast.BinOp):
        return _literal_texts(node.left) + _literal_texts(node.right)
    if isinstance(node, ast.IfExp):
        return _literal_texts(node.body) + _literal_texts(node.orelse)
    return []


def untranslated(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    out = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in TEXT_CALLS:
            continue
        line = lines[node.lineno - 1]
        if IGNORE_MARK in line:
            continue
        args = [node.args[i] for i in TEXT_CALLS[name] if i < len(node.args)]
        args += [k.value for k in node.keywords if k.arg in ("text", "title", "label")]
        for arg in args:
            for text in _literal_texts(arg):
                if _needs_translation(text):
                    out.append((node.lineno, text))
    return out


def bad_tr_calls(path: Path) -> list[tuple[int, str]]:
    """tr() with something other than a string literal (an f-string never matches a key)."""

    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and _call_name(node) == "tr" and isinstance(node.func, ast.Name):
            if not node.args or not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                if IGNORE_MARK not in lines[node.lineno - 1] and "i18n: registry" not in lines[node.lineno - 1]:
                    out.append((node.lineno, ast.unparse(node)))
    return out


def tr_keys(path: Path) -> set[str]:
    keys = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and _call_name(node) in ("tr", "_t") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                keys.add(arg.value)
    return keys


def _gui_files() -> list[Path]:
    return sorted(p for p in GUI.glob("*.py") if p.name not in SKIP_FILES)


def registry_labels() -> set[str]:
    """English labels the core defines and the interface shows (translated by label)."""

    from ogr_data.core import calibration as cal
    from ogr_data.core import fitting
    from ogr_data.core import report as rpt
    from ogr_data.core import simulation as sm
    from ogr_data.core import states as st
    from ogr_data.core.models import CRITERIA
    from ogr_data.core.project import SYMBOLS

    labels = set()
    for crit in CRITERIA.values():
        labels.add(crit.label)
        for f in crit.fields:
            labels.add(f.label)
            if f.kind == "enum":
                labels.update(f.options)
            elif f.kind == "table":
                labels.update(f.options)
    for table in (st.FAILURE_TEST_TYPES, st.PATH_TEST_TYPES, sm.TEST_TYPES, cal.STRENGTH_TYPES, cal.ALGORITHMS, SYMBOLS,
                  dict(rpt.SECTIONS)):
        labels.update(table.values())
    for seq in (cal.ERROR_TYPES, cal.DATA_TYPES, sm.SEEPAGE, sm.LOADING, st.SEEPAGE_CONDITIONS, st.LOADING_DIRECTIONS,
                st.STRAIN_TYPES, sm.STIFFNESS_TYPES, sm.CAM_CLAY_ELASTIC, sm.CONE_DILATION_TYPES):
        labels.update(seq)
    labels.update({fitting.TRIAXIAL, fitting.DIRECT} - {"triaxial", "direct"})
    return {x for x in labels if _needs_translation(x)}


def history_labels() -> set[str]:
    """The undo step templates of core.history (their Spanish is in es_history.py)."""

    from ogr_data.core.history import STEP_TEMPLATES

    return set(STEP_TEMPLATES)


def report(path: str) -> None:
    p = ROOT / path
    from ogr_data.gui.i18n import spanish

    es = spanish()
    for line, text in untranslated(p):
        print(f"{path}:{line}: not wrapped in tr(): {text!r}")
    for line, text in bad_tr_calls(p):
        print(f"{path}:{line}: tr() needs a literal: {text}")
    for key in sorted(tr_keys(p) - set(es)):
        print(f"{path}: no Spanish for {key!r}")


# ------------------------------------------------------------------ tests


def test_every_gui_text_goes_through_tr() -> None:
    problems = [f"{p.name}:{line}: {text!r}" for p in _gui_files() for line, text in untranslated(p)]
    problems += [f"{p.name}:{line}: {text}" for p in _gui_files() for line, text in bad_tr_calls(p)]
    assert not problems, "\n".join(problems[:60]) + (f"\n... {len(problems)} in all" if len(problems) > 60 else "")


def test_every_text_has_spanish_and_no_key_is_dead() -> None:
    from ogr_data.gui.i18n import spanish

    es = spanish()
    used = set().union(*(tr_keys(p) for p in _gui_files())) | tr_keys(ROOT / "ogr_data" / "core" / "report.py")
    labels = registry_labels() | history_labels()
    missing = sorted((used | labels) - set(es))
    assert not missing, f"{len(missing)} texts without Spanish: {missing[:40]}"
    dead = sorted(set(es) - used - labels)
    assert not dead, f"{len(dead)} unused keys: {dead[:40]}"
    same = sorted(k for k, v in es.items() if k == v and _needs_translation(k))
    assert not same, f"translated to themselves (remove them or translate): {same[:40]}"


def test_language_switch_basics() -> None:
    from ogr_data.gui import i18n

    try:
        i18n.set_language("es")
        assert i18n.tr("Undo") == "Deshacer" and i18n.tr("no such text") == "no such text"
        assert i18n.translator("en")("Undo") == "Undo"
    finally:
        i18n.set_language("en")
    assert i18n.tr("Undo") == "Undo"


# ------------------------------------------------------------------ live, in Spanish


def _visible_texts(root) -> list[str]:
    """Texts a user reads in a widget tree: labels, buttons, titles, tabs, combo items, menus, headers, tooltips."""

    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit, QMenu, QTableWidget,
                                   QTabWidget, QTreeWidget, QWidget)

    texts = [root.windowTitle()]
    widgets = [root, *root.findChildren(QWidget)]
    for w in widgets:
        texts.append(w.toolTip())
        if isinstance(w, QLabel):
            texts.append(w.text())
        elif isinstance(w, QAbstractButton):
            texts.append(w.text())
        elif isinstance(w, QGroupBox):
            texts.append(w.title())
        elif isinstance(w, QLineEdit):
            texts.append(w.placeholderText())
        elif isinstance(w, QComboBox):
            texts += [w.itemText(i) for i in range(w.count())]
        elif isinstance(w, QTabWidget):
            texts += [w.tabText(i) for i in range(w.count())]
        elif isinstance(w, QTableWidget):
            texts += [w.horizontalHeaderItem(i).text() for i in range(w.columnCount()) if w.horizontalHeaderItem(i)]
        elif isinstance(w, QTreeWidget) and w.headerItem() is not None:
            texts += [w.headerItem().text(i) for i in range(w.columnCount())]
        for act in w.actions():
            texts += [act.text(), act.toolTip()]
            menu = act.menu()
            if isinstance(menu, QMenu):
                texts += [a.text() for a in menu.actions()]
                for sub in menu.actions():
                    if sub.menu() is not None:
                        texts += [a.text() for a in sub.menu().actions()]
    return [t for t in texts if t]


def _english_left(texts: list[str], es: dict) -> list[str]:
    """Texts that are an English key of the dictionary shown untranslated."""

    return sorted({t for t in texts if t in es and es[t] != t})


def test_spanish_window_and_dialogs_show_no_english_text() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui import i18n

    app = QApplication.instance() or QApplication([])
    i18n.set_language("es")
    try:
        from ogr_data.core.database import MaterialDatabase
        from ogr_data.gui import calibration_dialog, database_dialog, estimation, fit_dialog, graph_editor, pickers
        from ogr_data.gui import report_dialog, simulation_dialog, soil_classifier, states_dialog
        from ogr_data.gui.main_window import MainWindow

        es = i18n.spanish()
        w = MainWindow()
        w._add_material("rock")  # a GHB form, a failure state in the tree
        w._add_material("soil")
        app.processEvents()
        m = w._current_material()
        main_texts = _visible_texts(w)  # before the dialogs, which are its children
        windows = {
            "failure states": states_dialog.FailureStatesDialog(w, m.name, m.failure_states, "kPa", 0),
            "stress paths": states_dialog.StressPathsDialog(w, m.name, m.stress_paths, "kPa", 0),
            "test simulations": simulation_dialog.TestSimulationsDialog(w, m.name, m.test_simulations, "kPa", 0),
            "calibration": calibration_dialog.CalibrationDialog(w, w._project, w._current, "kPa"),
            "fit": fit_dialog.FitDialog(w),
            "database": database_dialog.DatabaseDialog(MaterialDatabase(None), w),
            "report generator": report_dialog.ReportGeneratorDialog(w),
            "report views": report_dialog.ManageReportViewsDialog(w.report_views, w),
            "graph editor": graph_editor.GraphEditorDialog(w),
            "soil classifier": soil_classifier.SoilClassifierDialog(w),
            "GSI": estimation.GsiDialog(w),
            "mi": estimation.mi_dialog(w),
            "D": estimation.disturbance_dialog(w),
            "MR": estimation.ModulusRatioDialog(100000.0, "kPa", w),
            "phi r": estimation.PhiRDialog(w),
            "JRC": estimation.JrcDialog(10.0, w),
            "JCS": estimation.JcsDialog(10.0, "kPa", w),
            "compacted soil": estimation.CompactedSoilDialog("", w),
            "GSI selector": pickers.GsiPickerDialog(w),
        }
        # data of the source tables, cited in their language (spec 024, point 3)
        data = {"D": {"Tunnel", "Slope"}}
        problems = {name: [t for t in _english_left(_visible_texts(win), es) if t not in data.get(name, ())]
                    for name, win in windows.items()}
        problems["main window"] = _english_left(main_texts, es)
        problems = {k: v for k, v in problems.items() if v}
        assert not problems, problems
        # the menus are Spanish and the stored values stay English
        assert [a.text() for a in w.menuBar().actions()][:2] == ["Archivo", "Editar"]
        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
        assert w._params()["modulus_method"] == "Generalized Hoek & Diederichs (2006)"
        for win in windows.values():
            win.deleteLater()
    finally:
        i18n.set_language("en")


def test_language_switch_keeps_the_project_and_history() -> None:
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from ogr_data.core import history as hist
    from ogr_data.gui import i18n
    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    settings = QSettings("OpenGeoRock", "OGR-Data")
    saved = settings.value("language", None)
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        w._add_material("rock")
        w._widgets["gsi"].setValue(42.0)
        w._title_edit.setText("Switch")
        w._title_edit.editingFinished.emit()
        w._overlay_mogi_act.setChecked(True)
        before = hist.comparable(w._state())
        steps = len(w._history.undo_steps)
        w2 = w.set_language("es")
        app.processEvents()
        assert w2 is not w and i18n.current_language() == "es"
        assert hist.comparable(w2._state()) == before and w2._current == 1 and w2._title_edit.text() == "Switch"
        assert len(w2._history.undo_steps) == steps and w2._undo_act.text().startswith("Deshacer ")
        assert w2._overlay_mogi_act.isChecked() and w2.menuBar().actions()[0].text() == "Archivo"
        w2.undo()
        assert w2._title_edit.text() == ""
        w3 = w2.set_language("en")
        assert w3.menuBar().actions()[0].text() == "File" and w3._undo_act.text().startswith("Undo")
        w3.deleteLater()
    finally:
        i18n.set_language("en")
        if saved is None:
            settings.remove("language")
        else:
            settings.setValue("language", saved)


def test_decimal_separator_follows_the_language() -> None:
    """Spec 024: "," in Spanish and "." in English, whatever the Windows locale."""

    from PySide6.QtCore import QLocale
    from PySide6.QtWidgets import QApplication, QDoubleSpinBox

    from ogr_data.gui import i18n

    app = QApplication.instance() or QApplication([])
    try:
        i18n.set_language("es")
        assert i18n.decimal_point() == "," and QLocale().decimalPoint() == ","
        assert i18n.localize("c = 1.4941 MPa, phi 30.52 deg (eq. 7, 2026)") == "c = 1,4941 MPa, phi 30,52 deg (eq. 7, 2026)"
        assert i18n.parse_number(" 1,5 ") == 1.5 and i18n.parse_number("2.25") == 2.25
        spin = QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setValue(7.5)
        assert spin.text() == "7,50"
        from ogr_data.gui.estimation import GsiDialog

        dlg = GsiDialog(None, lang="es")
        dlg._tabs.setCurrentIndex(dlg._tabs.count() - 1)  # calculator
        dlg._rqd.setValue(30.0)
        dlg._j89.setValue(10.0)
        assert "30,00" in dlg._result.text() and dlg.value == 30.0
        dlg.deleteLater()
        i18n.set_language("en")
        assert QLocale().decimalPoint() == "." and i18n.localize("1.5") == "1.5"
        spin2 = QDoubleSpinBox()
        spin2.setDecimals(2)
        spin2.setValue(7.5)
        assert spin2.text() == "7.50"
        app.processEvents()
    finally:
        i18n.set_language("en")
