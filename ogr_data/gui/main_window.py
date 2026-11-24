"""Main window of OGR Data: criterion-driven sidebar + two plots."""

from __future__ import annotations

import copy
import io
import math
import os

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTabWidget,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import material_factory as factory
from ..core import material_results as mr
from ..core import criteria_envelopes as ce
from ..core import history as hist
from ..core import project as projects
from ..core import report
from ..core import samplers
from ..core import simulation as sm
from ..core import states as st
from ..core import units
from ..core.graph_options import PlotOptions
from ..core.hoek_brown import HbInput, ModulusMethod, compute
from ..core.models import CRITERIA, Criterion, defaults
from . import i18n
from . import accelerators
from .i18n import tr
from .plots import EnvelopeCanvas, PathCanvas
from .results_panel import ResultsPanel
from .settings import app_settings
from .themes import THEMES, apply_theme


def _t(text: str) -> str:
    """Marks an English text that is translated later, where it is shown (spec 024)."""

    return text


#: Recent Projects kept in the settings (spec 025c).
RECENT_PROJECTS = 8

#: Windows opened by a language switch (spec 024): referenced here so that
#: Python keeps them alive once the window that created them has closed.
_OPEN_WINDOWS: list = []


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OGR Data")
        self.resize(1150, 640)

        self._settings = app_settings()  # spec 025b: never built by hand
        self._theme = str(self._settings.value("theme", "light"))
        if self._theme not in THEMES:
            self._theme = "light"
        # spec 017: display stress unit (registry and clipboard stay in kPa)
        self._stress_unit = str(self._settings.value("stress_unit", units.DEFAULT_STRESS_UNIT))
        if self._stress_unit not in units.STRESS_FACTORS:
            self._stress_unit = units.DEFAULT_STRESS_UNIT
        # Spec 008: sampler / overlay state (created before the menus so the
        # toggled signals fired by setChecked find it in place).
        self._sampler_mode: str | None = None
        self._dragging = False
        self._curves: dict[str, tuple | None] = {"principal": None, "shear": None}
        self._d1_func = None
        self._overlay_inst: samplers.InstantaneousMC | None = None
        # Spec 011: multi-material project. The sidebar form edits the
        # selected material; _loading blocks write-back while a material
        # is being loaded into the form.
        self._project = projects.Project.new()
        self._file_path: str | None = None  # spec 025c: Save writes here
        self._current = 0
        self._loading = True
        self._tree_updating = False
        # spec 015: graph views added to the report (session only) and the
        # section visibility chosen in the Report Generator
        self.report_views = report.ReportViews()
        self.report_visibility = report.default_visibility()
        # spec 013: simulated tests, cached by (model, stiffness, test) inputs
        self._sim_cache: dict[str, object] = {}
        # spec 023: undo / redo. Created once the window is built; _history_hold
        # > 0 while the window itself changes the form (loading a material,
        # restoring a state, switching the display unit): no step then.
        self._history: hist.History | None = None
        self._history_hold = 0
        self.ask_unsaved = None  # tests: callable -> "save" | "discard" | "cancel"
        from PySide6.QtWidgets import QApplication

        apply_theme(QApplication.instance(), self._theme)
        self._create_menus()

        self._criterion_combo = QComboBox()
        for key, crit in CRITERIA.items():
            self._criterion_combo.addItem(tr(crit.label), key)  # i18n: registry
        self._criterion_combo.currentIndexChanged.connect(self._rebuild_form)
        self._criterion_combo.currentIndexChanged.connect(self._update_application)
        self._criterion_combo.currentIndexChanged.connect(self.refresh)

        self._sig3max = QDoubleSpinBox()
        self._sig3max.setRange(0.00001, 1000000000.0)
        self._sig3max.setDecimals(4)
        self._sig3max.setValue(7.5 * self._scale())
        self._sig3max.setSingleStep(0.5 * self._scale())
        self._sig3max.setSuffix(f" {self._stress_unit}")
        self._sig3max.valueChanged.connect(self.refresh)
        self._sig3max.editingFinished.connect(self._close_history_group)

        # spec 009: sigma3max by application (tunnel / slope)
        self._application_combo = QComboBox()
        for label, app_key in ((tr("Custom"), "custom"), (tr("Tunnel"), "tunnel"), (tr("Slope"), "slope")):
            self._application_combo.addItem(label, app_key)
        self._application_combo.currentIndexChanged.connect(self._update_application)
        self._unit_weight = QDoubleSpinBox()
        self._unit_weight.setRange(0.0001, 1.0)
        self._unit_weight.setDecimals(4)
        self._unit_weight.setValue(0.026)
        self._unit_weight.setSingleStep(0.001)
        self._unit_weight.setSuffix(" MN/m3")
        self._unit_weight.valueChanged.connect(self.refresh)
        self._unit_weight.editingFinished.connect(self._close_history_group)
        self._app_depth = QDoubleSpinBox()
        self._app_depth.setRange(0.1, 10000.0)
        self._app_depth.setValue(50.0)
        self._app_depth.setSuffix(" m")
        self._app_depth.valueChanged.connect(self.refresh)
        self._app_depth.editingFinished.connect(self._close_history_group)
        self._app_fields = QWidget()
        app_form = QFormLayout(self._app_fields)
        app_form.setContentsMargins(0, 0, 0, 0)
        self._depth_label = QLabel(tr("Tunnel depth"))
        app_form.addRow(tr("Unit weight"), self._unit_weight)
        app_form.addRow(self._depth_label, self._app_depth)
        self._app_fields.setVisible(False)

        self._form_box = QGroupBox(tr("Parameters"))
        self._form_layout = QFormLayout(self._form_box)
        self._widgets: dict[str, object] = {}

        # spec 013: Stiffness (RSData tab; rows per material model)
        from .stiffness_panel import StiffnessPanel

        self._stiffness_box = StiffnessPanel(self._kpa_scale(), self._stress_unit, self.use_erm_as_young)
        self._stiffness_box.changed.connect(self.refresh)
        for spin in self._stiffness_box.spins.values():
            spin.editingFinished.connect(self._close_history_group)
        self._poisson = self._stiffness_box.spins["poisson"]
        self._young = self._stiffness_box.spins["young"]
        self._use_erm = self._stiffness_box.use_erm

        # spec 025b: the sidebar holds only the material, in titled sections
        # (materials, material, stress range, parameters, stiffness); the
        # results moved to a panel on the right, project and program
        # settings to File > Project Settings and the toolbar.
        sidebar = QVBoxLayout()
        sidebar.addWidget(self._build_material_panel())
        material_box = QGroupBox("Material")  # i18n: ignore (same in Spanish)
        material_layout = QVBoxLayout(material_box)
        material_form = QFormLayout()
        material_form.setContentsMargins(0, 0, 0, 0)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("Material name"))
        self._name_edit.setText(self._project.materials[0].name)
        self._name_edit.textChanged.connect(self._name_edited)
        self._name_edit.editingFinished.connect(self._name_edit_finished)
        self._name_edit.editingFinished.connect(self._close_history_group)
        material_form.addRow(tr("Name"), self._name_edit)
        material_form.addRow(tr("Failure criterion"), self._criterion_combo)
        material_layout.addLayout(material_form)
        self._classifier_button = QPushButton(tr("Soil classifier (USCS)…"))
        self._classifier_button.clicked.connect(self._open_classifier)
        material_layout.addWidget(self._classifier_button)
        self._fit_button = QPushButton(tr("Fit lab data…"))
        self._fit_button.clicked.connect(self._open_fit_dialog)
        material_layout.addWidget(self._fit_button)
        sidebar.addWidget(material_box)
        range_box = QGroupBox(tr("Stress range"))
        range_form = QFormLayout(range_box)
        range_form.addRow(tr("Application (sigma3max range)"), self._application_combo)
        self._sig3max_label = QLabel(tr("sig3max (envelope range)"))
        range_form.addRow(self._sig3max_label, self._sig3max)
        range_form.addRow(self._app_fields)
        sidebar.addWidget(range_box)
        sidebar.addWidget(self._form_box)
        sidebar.addWidget(self._stiffness_box)
        sidebar.addStretch(1)
        # spec 017: display stress unit, now in the toolbar and Project Settings
        self._unit_combo = QComboBox()
        for unit_name in units.STRESS_FACTORS:
            self._unit_combo.addItem(unit_name)
        self._unit_combo.setCurrentText(self._stress_unit)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(360)
        scroll = QScrollArea()
        scroll.setObjectName("sidebar")
        scroll.setWidget(sidebar_widget)
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(380)

        self._principal = EnvelopeCanvas(
            tr("Principal Stresses"), tr("sigma3 ({0})").format(self._stress_unit),
            tr("sigma1 ({0})").format(self._stress_unit), self._theme, space="principal",
        )
        self._shear = EnvelopeCanvas(
            tr("Shear - Normal Stresses"), tr("normal stress ({0})").format(self._stress_unit),
            tr("shear stress ({0})").format(self._stress_unit), self._theme, space="shear",
        )
        for canvas in (self._principal, self._shear):
            canvas.sampler_handler = self._on_plot_event
            canvas.menu_handler = self._on_canvas_menu
            canvas.set_display_scale(self._scale())

        plots = QSplitter(Qt.Orientation.Horizontal)
        plots.addWidget(self._principal)
        plots.addWidget(self._shear)

        # spec 012: Stress Path Graphs tab (RSData's four default graphs; the
        # second shows volumetric strain: path tables hold no pore pressure).
        # Axis labels go in English (_t): the canvas translates them on screen
        # and keeps the English for the CSV headers.
        self._path_canvases = {
            "axial": PathCanvas(tr("Axial Stress vs Axial Strain"), _t("Axial Strain"), _t("Axial Stress"), False, True, self._theme),
            "volumetric": PathCanvas(
                tr("Volumetric Strain vs Axial Strain"), _t("Axial Strain"), _t("Volumetric Strain"), False, False, self._theme
            ),
            "deviatoric": PathCanvas(tr("q vs Deviatoric Strain"), _t("Deviatoric Strain"), "q", False, True, self._theme),
            "pq": PathCanvas(tr("q vs p"), "p", "q", True, True, self._theme),
        }
        path_page = QWidget()
        path_layout = QVBoxLayout(path_page)
        # spec 025d RF-1: with nothing to draw, say so and offer the way in
        self._path_hint = QWidget()
        hint_layout = QHBoxLayout(self._path_hint)
        hint_layout.setContentsMargins(4, 4, 4, 4)
        hint_text = QLabel(
            tr("This material has no stress paths or computed test simulations. Define one to fill these graphs:")
        )
        hint_text.setWordWrap(True)
        hint_layout.addWidget(hint_text, stretch=1)
        self._path_hint_buttons = []
        for label, slot in (
            (tr("Define Stress Paths…"), lambda: self._define_stress_paths()),
            (tr("Define Test Simulations…"), lambda: self._define_test_simulations()),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            hint_layout.addWidget(button)
            self._path_hint_buttons.append(button)
        path_layout.addWidget(self._path_hint)
        path_grid_host = QWidget()
        path_grid = QGridLayout(path_grid_host)
        path_grid.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(path_grid_host, stretch=1)
        for index, canvas in enumerate(self._path_canvases.values()):
            canvas.menu_handler = self._on_path_canvas_menu
            canvas.set_display(self._scale(), self._stress_unit)
            path_grid.addWidget(canvas, index // 2, index % 2)
        # spec 013c: Animation (RSData's Animation tab)
        from .animation_panel import AnimationPanel

        self._animation = AnimationPanel(self)
        path_grid.addWidget(self._animation, 2, 0, 1, 2)
        self._graph_tabs = QTabWidget()
        self._graph_tabs.addTab(plots, tr("Strength Graphs"))
        self._graph_tabs.addTab(path_page, tr("Stress Path Graphs"))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self._graph_tabs)
        splitter.setStretchFactor(1, 1)
        # the sidebar opens at its full width (no clipped buttons)
        splitter.setSizes([380, 770])
        self.setCentralWidget(splitter)
        self.statusBar()
        self._build_results_dock()
        self._build_toolbar()
        self._assign_accelerators()

        self._rebuild_form()
        self._overlay_mc_act.setChecked(True)
        self._unit_combo.currentTextChanged.connect(self._set_stress_unit)
        self._loading = False
        self._populate_tree()
        self.refresh()
        self._history = hist.History(self._state())
        self._update_history_ui()
        # spec 025b RF-4: results panel and toolbar as the user left them
        state = self._settings.value("window_state")
        if state:
            self.restoreState(state)

    # ----------------------------------------------------------------- menus

    def _create_menus(self) -> None:
        """Eight menus (spec 025c), each action under its RSData name.

        RSData spreads Failure States, Tests, Stress Paths, Calibrate and
        Compute over five one-entry menus; here they are one Tests menu in
        the order they are used (define, compute, calibrate). The actions
        the toolbar shares are attributes (spec 025b): one QAction, one
        enabled state.
        """

        bar = QMenuBar(self)
        self.setMenuBar(bar)
        keys = QKeySequence.StandardKey

        file_menu = bar.addMenu(tr("File"))
        self._new_act = file_menu.addAction(tr("New Project"), self._new_project)
        self._new_act.setShortcut(QKeySequence(keys.New))
        self._open_act = file_menu.addAction(tr("Open…"), self._load_project)
        self._open_act.setShortcut(QKeySequence(keys.Open))
        self._recent_menu = file_menu.addMenu(tr("Recent Projects"))
        self._recent_menu.aboutToShow.connect(self._rebuild_recent_menu)
        file_menu.addSeparator()
        self._save_act = file_menu.addAction(tr("Save"), self._save_project)
        self._save_act.setShortcut(QKeySequence(keys.Save))
        self._save_as_act = file_menu.addAction(tr("Save As…"), self._save_project_as)
        self._save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()
        file_menu.addAction(tr("Import .roc…"), self._import_roc)
        self._project_settings_act = file_menu.addAction(tr("Project Settings…"), self._open_project_settings)
        file_menu.addSeparator()
        file_menu.addAction(tr("Exit"), self.close)

        edit_menu = bar.addMenu(tr("Edit"))
        self._edit_menu = edit_menu
        # spec 023
        self._undo_act = QAction(tr("Undo"), self)
        self._undo_act.setShortcut(QKeySequence(keys.Undo))
        self._undo_act.triggered.connect(self.undo)
        self._redo_act = QAction(tr("Redo"), self)
        self._redo_act.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self._redo_act.triggered.connect(self.redo)
        edit_menu.addAction(self._undo_act)
        edit_menu.addAction(self._redo_act)
        edit_menu.addSeparator()
        self._copy_material_act = edit_menu.addAction(tr("Copy material"), self._copy_material)
        self._copy_data_act = edit_menu.addAction(tr("Copy data"), self._copy_data)
        self._copy_plot_act = edit_menu.addAction(tr("Copy plot"), self._copy_plot_image)
        edit_menu.addSeparator()
        # spec 025c RF-7: Supr only while the tree has the focus (the tree
        # adds the action), so the fields keep it for their text
        self._delete_act = edit_menu.addAction(tr("Delete"), lambda: self._delete_selected())
        self._delete_act.setShortcut(QKeySequence(keys.Delete))
        self._delete_act.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)

        view_menu = bar.addMenu(tr("View"))
        theme_menu = view_menu.addMenu(tr("Theme"))
        theme_names = {"light": tr("Light"), "dark": tr("Dark")}
        for name in THEMES:
            theme_menu.addAction(theme_names.get(name, name.capitalize()), lambda _=False, n=name: self._set_theme(n))
        # spec 024: interface language (the window reopens in it, keeping everything)
        language_menu = view_menu.addMenu(tr("Language"))
        language_group = QActionGroup(self)
        for code, native in i18n.LANGUAGES.items():
            act = language_menu.addAction(native, lambda _=False, c=code: self.set_language(c))
            act.setCheckable(True)
            act.setChecked(code == i18n.current_language())
            language_group.addAction(act)
        # spec 017 / 025c: display stress unit
        self._unit_menu = view_menu.addMenu(tr("Stress unit"))
        unit_group = QActionGroup(self)
        self._unit_actions: dict[str, QAction] = {}
        for unit_name in units.STRESS_FACTORS:
            act = self._unit_menu.addAction(unit_name, lambda _=False, u=unit_name: self._set_stress_unit(u))
            act.setCheckable(True)
            act.setChecked(unit_name == self._stress_unit)
            unit_group.addAction(act)
            self._unit_actions[unit_name] = act
        view_menu.addSeparator()
        view_menu.addAction(tr("Graph Editor…"), self._open_graph_editor)
        # spec 025b: View > Results panel / Toolbar (added once they exist)
        self._view_menu = view_menu

        materials_menu = bar.addMenu(tr("Materials"))
        materials_menu.addAction(tr("Add Material"), lambda: self._add_material("material"))
        materials_menu.addAction(tr("Add Rock Template"), lambda: self._add_material("rock"))
        materials_menu.addAction(tr("Add Soil Template"), lambda: self._add_material("soil"))
        materials_menu.addSeparator()
        materials_menu.addAction(tr("Duplicate Material"), self._duplicate_material)
        materials_menu.addAction(tr("Rename Material"), self._rename_material)
        materials_menu.addAction("Color…", self._choose_material_color)  # i18n: ignore (same in Spanish)
        materials_menu.addAction(tr("Automatic color"), lambda: self._set_material_color(""))
        self._symbol_menu = materials_menu.addMenu(tr("Symbol"))
        self._symbol_menu.aboutToShow.connect(self._rebuild_symbol_menu)
        self._rebuild_symbol_menu()
        self._delete_material_act = materials_menu.addAction(tr("Delete Material"), lambda: self._delete_material())
        materials_menu.addSeparator()
        materials_menu.addAction(tr("Material Database…"), self._open_database)  # spec 010 (RSData: Open RocProp)
        materials_menu.addAction(tr("Soil classifier (USCS)…"), self._open_classifier)
        materials_menu.addAction(tr("Fit lab data…"), self._open_fit_dialog)

        # specs 012, 013, 014: RSData's five one-entry menus, in the order of use
        tests_menu = bar.addMenu(tr("Tests"))
        tests_menu.addAction(tr("Define Failure States…"), lambda: self._define_failure_states())
        tests_menu.addAction(tr("Define Stress Paths…"), lambda: self._define_stress_paths())
        tests_menu.addAction(tr("Define Test Simulations…"), lambda: self._define_test_simulations())
        tests_menu.addSeparator()
        self._compute_act = tests_menu.addAction(tr("Compute"), self.compute)
        self._compute_act.setShortcut(QKeySequence("F5"))
        tests_menu.addSeparator()
        tests_menu.addAction(tr("Calibrate…"), self._open_calibration)

        analysis_menu = bar.addMenu(tr("Analysis"))
        self._stress_sampler_act = QAction(tr("Stress Sampler"), self, checkable=True)
        self._mc_sampler_act = QAction(tr("Instantaneous MC Sampler"), self, checkable=True)
        sampler_group = QActionGroup(self)
        sampler_group.setExclusive(True)
        sampler_group.addAction(self._stress_sampler_act)
        sampler_group.addAction(self._mc_sampler_act)
        analysis_menu.addAction(self._stress_sampler_act)
        analysis_menu.addAction(self._mc_sampler_act)
        analysis_menu.addSeparator()
        self._overlay_mc_act = QAction(tr("Overlay MC Envelope"), self, checkable=True)
        self._overlay_mogi_act = QAction(tr("Overlay Mogi Line"), self, checkable=True)
        analysis_menu.addAction(self._overlay_mc_act)
        analysis_menu.addAction(self._overlay_mogi_act)
        self._stress_sampler_act.toggled.connect(self._sampler_mode_changed)
        self._mc_sampler_act.toggled.connect(self._sampler_mode_changed)
        self._overlay_mc_act.toggled.connect(self.refresh)
        self._overlay_mogi_act.toggled.connect(self.refresh)

        # spec 015 (RSData names)
        report_menu = bar.addMenu(tr("Report"))
        report_menu.addAction(tr("Report Generator…"), self._open_report_generator)
        report_menu.addAction(tr("Add View To Report"), self.add_view_to_report)
        report_menu.addAction(tr("Manage Report View…"), self._manage_report_views)

        help_menu = bar.addMenu(tr("Help"))
        self._shortcuts_act = help_menu.addAction(tr("Keyboard Shortcuts"), self._show_shortcuts)
        self._shortcuts_act.setShortcut(QKeySequence("F1"))
        help_menu.addSeparator()
        help_menu.addAction(tr("About OGR Data"), self._about)

    def _rebuild_symbol_menu(self) -> None:
        """Materials > Symbol, checked at the selected material's (as the tree's menu)."""

        self._symbol_menu.clear()
        current = self._current_material().symbol
        for symbol, label in projects.SYMBOLS.items():
            act = self._symbol_menu.addAction(tr(label), lambda _=False, s=symbol: self._set_material_symbol(s))  # i18n: registry
            act.setCheckable(True)
            act.setChecked(symbol == current)
        accelerators.assign(self._symbol_menu)

    def _assign_accelerators(self) -> None:
        """Alt letters for every menu (spec 025c RF-4), once all entries exist."""

        accelerators.assign(self.menuBar())

    # ------------------------------------------------- spec 025c: files, recent projects, delete

    def _ask_save_path(self) -> str:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, tr("Save project"), self._file_path or "", tr("OGR Data project (*.ogrdata)"))
        return path

    def _save_project(self) -> bool:
        """Save (Ctrl+S): to the project's file, or Save As when it has none (RF-5)."""

        if self._file_path:
            return self.save_project_to(self._file_path)
        return self._save_project_as()

    def _save_project_as(self) -> bool:
        path = self._ask_save_path()
        if not path:
            return False
        return self.save_project_to(path)

    def recent_projects(self) -> list[str]:
        raw = self._settings.value("recent_projects", [])
        if isinstance(raw, str):  # QSettings gives a bare string for a one-item list
            raw = [raw]
        return [str(p) for p in (raw or [])]

    def _remember_recent(self, path: str) -> None:
        path = os.path.abspath(path)
        recent = [p for p in self.recent_projects() if os.path.abspath(p) != path]
        self._settings.setValue("recent_projects", [path, *recent][:RECENT_PROJECTS])

    def _forget_recent(self, path: str) -> None:
        path = os.path.abspath(path)
        self._settings.setValue("recent_projects", [p for p in self.recent_projects() if os.path.abspath(p) != path])

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent = self.recent_projects()
        if not recent:
            empty = self._recent_menu.addAction(tr("(none)"))
            empty.setEnabled(False)
            return
        for index, path in enumerate(recent, start=1):
            act = self._recent_menu.addAction(f"&{index} {path}", lambda _=False, p=path: self._open_recent(p))
            act.setStatusTip(path)

    def _open_recent(self, path: str) -> None:
        if self._confirm_discard():
            self.open_project_file(path)

    def open_project_file(self, path: str) -> bool:
        """Open a project file; a vanished one leaves Recent Projects, said in the status bar (RF-6)."""

        if not os.path.exists(path):
            self._forget_recent(path)
            self.statusBar().showMessage(
                tr("{0} no longer exists: removed from Recent Projects.").format(os.path.basename(path)), 8000
            )
            return False
        try:
            loaded = projects.load_project(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, tr("Open failed"), str(exc))
            return False
        self.open_project(loaded)
        self._file_path = os.path.abspath(path)
        self._remember_recent(path)
        self._update_window_title()
        return True

    def _delete_selected(self) -> None:
        """Edit > Delete / Supr in the tree: the selected material, state, path or simulation."""

        item = self._tree.currentItem()
        if item is None:
            return
        if item.parent() is None:
            self._delete_material()
        else:
            kind, index = item.data(0, Qt.ItemDataRole.UserRole)
            self._delete_child(kind, index)

    def _show_shortcuts(self) -> None:
        """F1: the keyboard shortcuts, read from the menus (non-modal, RF-9)."""

        from .shortcuts_dialog import ShortcutsDialog

        self._shortcuts_dialog = ShortcutsDialog(self.menuBar(), self)
        self._shortcuts_dialog.show()

    # ------------------------------------------------- spec 025b: results panel and toolbar

    def _build_results_dock(self) -> None:
        """The results of the selected material, docked on the right (RF-1)."""

        self._results = ResultsPanel(self._copy_material)
        self._results_dock = QDockWidget(tr("Results"), self)
        self._results_dock.setObjectName("results_dock")  # saveState / restoreState
        self._results_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self._results_dock.setWidget(self._results)
        self._results.setMinimumWidth(220)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._results_dock)
        toggle = self._results_dock.toggleViewAction()
        toggle.setText(tr("Results panel"))
        self._view_menu.addSeparator()
        self._view_menu.addAction(toggle)

    def _build_toolbar(self) -> None:
        """The actions of every session, with the same QAction as the menus (RF-7)."""

        bar = QToolBar(tr("Toolbar"), self)
        bar.setObjectName("main_toolbar")  # saveState / restoreState
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        style = self.style()
        icons = {
            self._new_act: QStyle.StandardPixmap.SP_FileIcon,
            self._open_act: QStyle.StandardPixmap.SP_DialogOpenButton,
            self._save_act: QStyle.StandardPixmap.SP_DialogSaveButton,
            self._undo_act: QStyle.StandardPixmap.SP_ArrowBack,
            self._redo_act: QStyle.StandardPixmap.SP_ArrowForward,
            self._copy_material_act: QStyle.StandardPixmap.SP_FileLinkIcon,
            self._copy_data_act: QStyle.StandardPixmap.SP_FileDialogDetailedView,
            self._copy_plot_act: QStyle.StandardPixmap.SP_DesktopIcon,
            self._compute_act: QStyle.StandardPixmap.SP_MediaPlay,
        }
        groups = (
            (self._new_act, self._open_act, self._save_act),
            (self._undo_act, self._redo_act),
            (self._copy_material_act, self._copy_data_act, self._copy_plot_act),
            (self._compute_act,),
        )
        for index, group in enumerate(groups):
            if index:
                bar.addSeparator()
            for action in group:
                action.setIcon(style.standardIcon(icons[action]))
                bar.addAction(action)
        # Undo/Redo name the step they take back ("Undo Change GSI"): as text
        # buttons they would resize the bar at every edit, so icon only
        for action in (self._undo_act, self._redo_act):
            bar.widgetForAction(action).setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        bar.addSeparator()
        unit_label = QLabel(tr("Stress unit") + " ")
        unit_label.setBuddy(self._unit_combo)
        bar.addWidget(unit_label)
        bar.addWidget(self._unit_combo)
        self._toolbar = bar
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, bar)
        toggle = bar.toggleViewAction()
        toggle.setText(tr("Toolbar"))
        self._view_menu.addAction(toggle)

    def _results_heading(self) -> str:
        material = self._current_material()
        return f"{material.name} ({tr(CRITERIA[material.criterion].label)})"  # i18n: registry

    def _show_derived_results(self) -> None:
        """RF-9: the derived results of a criterion other than GHB, or why there are none.

        The rows are the report's (``report.computed_rows``): classic
        Hoek-Brown gives sigcm and the equivalent MC (Hoek 2002), Power Curve
        and Barton-Bandis the best-fit MC over the range (RocData 2004);
        one source for the panel and the report.
        """

        rows = report.computed_rows(self._current_material(), self._stress_unit, tr)
        if not rows:
            self._results.set_message(
                self._results_heading(),
                tr("This criterion has no derived parameters: its strength parameters are the inputs."),
            )
            return
        note = tr("Over the stress range up to sig3max = {0}.").format(
            i18n.localize(units.stress_text(self._sig3max_mpa(), self._stress_unit))
        )
        self._results.set_results(self._results_heading(), [(label, i18n.localize(value)) for label, value in rows], note)

    # ------------------------------------------------- spec 025b: project settings

    def _open_project_settings(self) -> None:
        from .project_settings_dialog import ProjectSettingsDialog

        dialog = ProjectSettingsDialog(self._project.title, self._stress_unit, self)
        if dialog.exec():
            self.apply_project_settings(dialog.title(), dialog.stress_unit())

    def apply_project_settings(self, title: str, stress_unit: str) -> None:
        if stress_unit != self._stress_unit:
            self._unit_combo.setCurrentText(stress_unit)  # -> _set_stress_unit
        self.set_project_title(title)

    def set_project_title(self, title: str) -> None:
        """The project title, as one undo step (spec 023)."""

        self._project.title = title
        self._update_window_title()
        self._checkpoint()
        self._close_history_group()

    # ------------------------------------------------- spec 011: materials

    def _build_material_panel(self) -> QWidget:
        """Materials tree (RSData's Visibility panel) with its buttons."""

        box = QGroupBox(tr("Materials"))
        layout = QVBoxLayout(box)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setMinimumHeight(110)
        self._tree.setMaximumHeight(170)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._tree_menu)
        self._tree.currentItemChanged.connect(self._tree_current_changed)
        self._tree.itemChanged.connect(self._tree_item_changed)
        self._tree.itemDoubleClicked.connect(self._tree_double_clicked)
        self._tree.addAction(self._delete_act)  # spec 025c RF-7: Supr here only
        layout.addWidget(self._tree)

        buttons = QHBoxLayout()
        self._add_button = QToolButton()
        self._add_button.setText(tr("Add Material"))
        self._add_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        add_menu = QMenu(self._add_button)
        add_menu.addAction(tr("Add Rock Template"), lambda: self._add_material("rock"))
        add_menu.addAction(tr("Add Soil Template"), lambda: self._add_material("soil"))
        self._add_button.setMenu(add_menu)
        self._add_button.clicked.connect(lambda: self._add_material("material"))
        self._duplicate_button = QPushButton(tr("Duplicate"))
        self._duplicate_button.clicked.connect(self._duplicate_material)
        self._delete_button = QPushButton(tr("Delete"))
        self._delete_button.clicked.connect(lambda: self._delete_material())
        self._add_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        buttons.addWidget(self._add_button)
        buttons.addWidget(self._duplicate_button)
        buttons.addWidget(self._delete_button)
        layout.addLayout(buttons)
        return box

    def _material_color(self, material: projects.Material) -> str:
        return material.color or self._principal.line_color("envelope")

    def _swatch(self, color: str) -> QIcon:
        pixmap = QPixmap(12, 12)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    def _populate_tree(self) -> None:
        """Rebuild the tree from the project and select the current material."""

        self._tree_updating = True
        try:
            self._tree.clear()
            for material in self._project.materials:
                item = QTreeWidgetItem([material.name])
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsEditable
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                item.setCheckState(0, Qt.CheckState.Checked if material.visible else Qt.CheckState.Unchecked)
                item.setIcon(0, self._swatch(self._material_color(material)))
                item.setToolTip(0, f"{material.name} ({tr(CRITERIA[material.criterion].label)})")  # i18n: registry
                self._tree.addTopLevelItem(item)
                # spec 012: failure states and stress paths of the material
                children = [("state", i, s, st.FAILURE_TEST_TYPES[s.test_type]) for i, s in enumerate(material.failure_states)]
                children += [("test", i, t, sm.TEST_TYPES[t.test_type]) for i, t in enumerate(material.test_simulations)]
                children += [("path", i, p, st.PATH_TEST_TYPES[p.test_type]) for i, p in enumerate(material.stress_paths)]
                for kind, index, obj, test_label in children:
                    child = QTreeWidgetItem([obj.name])
                    child.setFlags(
                        Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )
                    child.setData(0, Qt.ItemDataRole.UserRole, (kind, index))
                    child.setCheckState(0, Qt.CheckState.Checked if obj.visible else Qt.CheckState.Unchecked)
                    child.setIcon(0, self._swatch(obj.color))
                    noun = {"state": tr("Failure state"), "test": tr("Test simulation"), "path": tr("Stress path")}[kind]
                    child.setToolTip(0, f"{noun}: {obj.name} ({tr(test_label)})")  # i18n: registry
                    item.addChild(child)
            self._tree.expandAll()
            self._tree.setCurrentItem(self._tree.topLevelItem(self._current))
        finally:
            self._tree_updating = False
        self._update_action_states()

    def _update_action_states(self) -> None:
        """What cannot run is disabled and says why (spec 025d RF-5)."""

        can_delete = len(self._project.materials) > 1
        reason = "" if can_delete else tr("A project keeps at least one material.")
        for widget in (self._delete_button, getattr(self, "_delete_material_act", None)):
            if widget is not None:
                widget.setEnabled(can_delete)
                widget.setToolTip(reason)

    def _current_material(self) -> projects.Material:
        return self._project.materials[self._current]

    def _store_current(self) -> None:
        """Write the form state back into the selected material."""

        if self._loading or not self._widgets:
            return
        material = self._current_material()
        material.criterion = self._criterion_combo.currentData()
        material.parameters = self._params()
        material.sig3max_mpa = self._sig3max_mpa()
        material.application = projects.Application(
            self._application_combo.currentData(), self._unit_weight.value(), self._app_depth.value()
        )
        material.stiffness = self._stiffness()
        item = self._tree.topLevelItem(self._current)
        if item is not None:
            self._tree_updating = True
            item.setToolTip(0, f"{material.name} ({tr(CRITERIA[material.criterion].label)})")  # i18n: registry
            self._tree_updating = False

    def _load_material(self, index: int) -> None:
        """Show material `index` in the form and plots."""

        self._checkpoint()  # the action that changed the material (add, delete, import...)
        self._history_hold += 1
        try:
            self._show_material(index)
        finally:
            self._history_hold -= 1
        self._absorb()

    def _show_material(self, index: int) -> None:
        self._current = index
        material = self._current_material()
        self._loading = True
        try:
            app = material.application
            for widget, value in ((self._unit_weight, app.unit_weight), (self._app_depth, app.depth)):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
            self._stiffness_box.set_values(material.stiffness)
            self._application_combo.blockSignals(True)
            self._application_combo.setCurrentIndex(max(0, self._application_combo.findData(app.mode)))
            self._application_combo.blockSignals(False)
            self._apply_project(material.criterion, dict(material.parameters), material.sig3max_mpa)
            self._update_application()
            self._name_edit.setText(material.name)
        finally:
            self._loading = False
        self.refresh()

    def _tree_material_index(self, item) -> int:
        """Material index of a tree item (children belong to their material)."""

        parent = item.parent()
        return self._tree.indexOfTopLevelItem(parent if parent is not None else item)

    def _tree_current_changed(self, current, _previous) -> None:
        if self._tree_updating or current is None:
            return
        index = self._tree_material_index(current)
        if index >= 0 and index != self._current:
            self._store_current()
            self._load_material(index)

    def _tree_item_changed(self, item, _column) -> None:
        if self._tree_updating:
            return
        if item.parent() is not None:
            # spec 012: visibility of a failure state / stress path
            kind, sub = item.data(0, Qt.ItemDataRole.UserRole)
            material = self._project.materials[self._tree_material_index(item)]
            self._children(material, kind)[sub].visible = item.checkState(0) == Qt.CheckState.Checked
            self.refresh()
            return
        index = self._tree.indexOfTopLevelItem(item)
        if index < 0:
            return
        material = self._project.materials[index]
        text = item.text(0)
        if text != material.name:
            try:
                name = self._project.rename(index, text)
            except ValueError:
                name = material.name
            self._tree_updating = True
            item.setText(0, name)
            item.setToolTip(0, f"{name} ({tr(CRITERIA[material.criterion].label)})")  # i18n: registry
            self._tree_updating = False
            if index == self._current:
                self._name_edit.setText(name)
        material.visible = item.checkState(0) == Qt.CheckState.Checked
        self.refresh()

    def _name_edited(self, text: str) -> None:
        """The Properties name field renames the selected material live."""

        if self._loading or not text.strip():
            return
        name = self._project.rename(self._current, text)
        item = self._tree.topLevelItem(self._current)
        if item is not None:
            self._tree_updating = True
            item.setText(0, name)
            self._tree_updating = False
        self.refresh()

    def _name_edit_finished(self) -> None:
        # an emptied or clashing name shows the stored (unique) one again
        name = self._current_material().name
        if self._name_edit.text() != name:
            self._name_edit.setText(name)

    def _add_material(self, template: str) -> None:
        self._store_current()
        index = self._project.add(template)
        self._load_material(index)
        self._populate_tree()

    def _duplicate_material(self) -> None:
        self._store_current()
        index = self._project.duplicate(self._current)
        self._load_material(index)
        self._populate_tree()

    def _rename_material(self) -> None:
        item = self._tree.topLevelItem(self._current)
        if item is not None:
            self._tree.editItem(item, 0)

    def _delete_material(self) -> None:
        """Delete the selected material, without asking: Undo brings it back (spec 025d RF-4)."""

        if len(self._project.materials) <= 1:
            return
        name = self._current_material().name
        index = self._project.remove(self._current)
        self._load_material(index)
        self._populate_tree()
        self._say_deleted(name)

    def _say_deleted(self, name: str) -> None:
        self.statusBar().showMessage(tr("Deleted '{0}'. Undo (Ctrl+Z) brings it back.").format(name), 8000)

    def _set_material_color(self, color: str) -> None:
        self._current_material().color = color
        self._populate_tree()
        self.refresh()

    def _choose_material_color(self) -> None:
        initial = QColor(self._material_color(self._current_material()))
        color = QColorDialog.getColor(initial, self, tr("Material color"))
        if color.isValid():
            self._set_material_color(color.name())

    def _set_material_symbol(self, symbol: str) -> None:
        if symbol in projects.SYMBOLS:
            self._current_material().symbol = symbol
            self._checkpoint()

    def _tree_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is not None:
            self._tree.setCurrentItem(item)
        if item is not None and item.parent() is not None:
            self._child_menu(item, pos)
            return
        menu = QMenu(self)
        menu.addAction(tr("Add Material"), lambda: self._add_material("material"))
        menu.addAction(tr("Add Rock Template"), lambda: self._add_material("rock"))
        menu.addAction(tr("Add Soil Template"), lambda: self._add_material("soil"))
        if item is not None:
            menu.addSeparator()
            menu.addAction(tr("Duplicate Material"), self._duplicate_material)
            menu.addAction(tr("Rename"), self._rename_material)
            menu.addAction("Color…", self._choose_material_color)  # i18n: ignore (same in Spanish)
            menu.addAction(tr("Automatic color"), lambda: self._set_material_color(""))
            symbol_menu = menu.addMenu(tr("Symbol"))
            current = self._current_material().symbol
            for symbol, label in projects.SYMBOLS.items():
                act = symbol_menu.addAction(tr(label), lambda s=symbol: self._set_material_symbol(s))  # i18n: registry
                act.setCheckable(True)
                act.setChecked(symbol == current)
            menu.addAction(tr("Copy material"), self._copy_material)
            menu.addSeparator()
            menu.addAction(tr("Define Failure States…"), lambda: self._define_failure_states())
            menu.addAction(tr("Define Test Simulations…"), lambda: self._define_test_simulations())
            menu.addAction(tr("Define Stress Paths…"), lambda: self._define_stress_paths())
            menu.addSeparator()
            delete = menu.addAction(tr("Delete Material"), lambda: self._delete_material())
            delete.setEnabled(len(self._project.materials) > 1)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ------------------------------------- spec 012: failure states and stress paths

    def _child_menu(self, item, pos) -> None:
        kind, sub = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        if kind == "state":
            menu.addAction(tr("Edit Failure State…"), lambda: self._define_failure_states(sub))
        elif kind == "test":
            menu.addAction(tr("Edit Test Simulation…"), lambda: self._define_test_simulations(sub))
        else:
            menu.addAction(tr("Edit Stress Path…"), lambda: self._define_stress_paths(sub))
        menu.addAction(tr("Delete"), lambda: self._delete_child(kind, sub))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _tree_double_clicked(self, item, _column) -> None:
        if item.parent() is None:
            return  # material rows: double click renames in place
        kind, sub = item.data(0, Qt.ItemDataRole.UserRole)
        if kind == "state":
            self._define_failure_states(sub)
        elif kind == "test":
            self._define_test_simulations(sub)
        else:
            self._define_stress_paths(sub)

    def _delete_child(self, kind: str, index: int) -> None:
        objects = self._children(self._current_material(), kind)
        name = None
        if 0 <= index < len(objects):
            name = objects[index].name
            del objects[index]
        self._populate_tree()
        self.refresh()
        if name is not None:
            self._say_deleted(name)

    def _define_failure_states(self, initial: int = 0) -> None:
        from .states_dialog import FailureStatesDialog

        material = self._current_material()
        dialog = FailureStatesDialog(self, material.name, material.failure_states, self._stress_unit, initial)
        if dialog.exec():
            self.set_failure_states(dialog.items)

    def _define_stress_paths(self, initial: int = 0) -> None:
        from .states_dialog import StressPathsDialog

        material = self._current_material()
        dialog = StressPathsDialog(self, material.name, material.stress_paths, self._stress_unit, initial)
        if dialog.exec():
            self.set_stress_paths(dialog.items)

    @staticmethod
    def _children(material: projects.Material, kind: str) -> list:
        return {"state": material.failure_states, "test": material.test_simulations, "path": material.stress_paths}[kind]

    def _define_test_simulations(self, initial: int = 0) -> None:
        from .simulation_dialog import TestSimulationsDialog

        material = self._current_material()
        dialog = TestSimulationsDialog(self, material.name, material.test_simulations, self._stress_unit, initial)
        if dialog.exec():
            self.set_test_simulations(dialog.items)

    def set_test_simulations(self, tests: list) -> None:
        """Replace the selected material's test simulations (dialog OK)."""

        self._current_material().test_simulations = list(tests)
        self._populate_tree()
        self.refresh()

    def set_failure_states(self, failure_states: list) -> None:
        """Replace the selected material's failure states (dialog OK)."""

        self._current_material().failure_states = list(failure_states)
        self._populate_tree()
        self.refresh()

    def set_stress_paths(self, stress_paths: list) -> None:
        """Replace the selected material's stress paths (dialog OK)."""

        self._current_material().stress_paths = list(stress_paths)
        self._populate_tree()
        self.refresh()

    # ------------------------------------------------- spec 010: material database

    database_path = None  # tests set a temporary file

    def _database_file(self):
        from pathlib import Path

        from PySide6.QtCore import QStandardPaths

        if self.database_path is not None:
            return Path(self.database_path)
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
        return Path(base) / "OpenGeoRock" / "OGR-Data" / "materials_db.json"

    def _open_database(self) -> None:
        from ..core.database import MaterialDatabase
        from .database_dialog import DatabaseDialog

        try:
            database = MaterialDatabase(self._database_file())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, tr("Material Database"), str(exc))
            return
        DatabaseDialog(database, self, on_use=self.use_database_record, on_use_state=self.use_database_specimens).exec()

    def use_database_specimens(self, record: dict) -> None:
        """Failure state of the selected material from the record's specimens (sigma3, sigma1)."""

        material = self._current_material()
        state = factory.state_from_record(record, material.failure_states)
        self.set_failure_states(material.failure_states + [state])
        self.statusBar().showMessage(
            tr("Failure state '{0}' added to {1} ({2} points from record {3}).").format(
                state.name, material.name, len(state.points), record.get("record_id")
            )
        )

    def use_database_record(self, record: dict) -> int:
        """New Generalized Hoek-Brown material from a database record (sigci, mi)."""

        material = factory.from_record(record, self._current_material().sig3max_mpa)
        self._store_current()
        index = self._project.append(material)
        self._load_material(index)
        self._populate_tree()
        self.statusBar().showMessage(
            tr("Material created from database record {0}: GSI and D keep their defaults; set them for the rock mass.").format(
                record.get("record_id")
            )
        )
        return index

    # ------------------------------------------------- spec 014: calibration

    def _open_calibration(self) -> None:
        from .calibration_dialog import CalibrationDialog

        self._store_current()
        dialog = CalibrationDialog(self, self._project, self._current, self._stress_unit)
        if dialog.exec() and dialog.result is not None:
            self.add_calibrated_material(dialog.name.text(), dialog.result)
        elif dialog.wants_failure_states:  # spec 025a (B4)
            self._define_failure_states()

    def add_calibrated_material(self, name: str, result) -> int:
        """New material from a calibration (the source material is not changed)."""

        material = factory.from_calibration(name, result, self._current_material().sig3max_mpa)
        self._store_current()
        index = self._project.append(material)
        self._load_material(index)
        self._populate_tree()
        return index

    def _draw_test_data(self) -> None:
        """Failure-state points, Mohr circles and stress paths of visible materials.

        As RSData 1.009 (capture 71) and the RocData 3.0 guide (pp. 13, 47-48):
        triaxial and general states as filled points in sigma1-sigma3 and Mohr
        circles in tau-sigma; direct shear states as points in tau-sigma.
        Excluded points are not drawn (RSData removes them from the plots).
        """

        principal, shear = [], []
        multi = len(self._project.materials) > 1
        for material in self._project.materials:
            if not material.visible:
                continue
            prefix = f"{material.name}: " if multi else ""
            for state in material.failure_states:
                if not state.visible:
                    continue
                label = f"{prefix}{state.name}"
                layer = {"color": state.color, "marker": state.symbol, "legend": label}
                direct = state.shear_points()
                if direct is not None:
                    if len(direct[0]):
                        shear.append({**layer, "x": direct[0] / 1000.0, "y": direct[1] / 1000.0,
                                      "export": (f"{label} SigmaN", f"{label} Tau")})
                    continue
                sig3, sig1 = state.principal_points()
                if not len(sig3):
                    continue
                x, y = sig3 / 1000.0, sig1 / 1000.0  # kPa -> MPa
                principal.append({**layer, "x": x, "y": y, "export": (f"{label} Sigma3", f"{label} Sigma1")})
                for s3, s1 in zip(x, y):
                    normal, tau = st.mohr_circle(float(s3), float(s1))
                    shear.append({"x": normal, "y": tau, "color": state.color, "linestyle": "-", "linewidth": 0.9})
            for path in material.stress_paths:
                if not path.visible:
                    continue
                curve = path.principal_path()
                if curve is None:
                    continue
                label = f"{prefix}{path.name}"
                # stress points (Mohr circle tops) on the tau-sigma plane
                s_t = path.shear_path()
                shear.append(
                    {
                        "x": s_t[0] / 1000.0,
                        "y": s_t[1] / 1000.0,
                        "color": path.color,
                        "marker": ".",
                        "linestyle": "-",
                        "linewidth": 1.4,
                        "markersize": 5.0,
                        "legend": label,
                        "export": (f"{label} s", f"{label} t"),
                    }
                )
                principal.append(
                    {
                        "x": curve[0] / 1000.0,
                        "y": curve[1] / 1000.0,
                        "color": path.color,
                        "marker": ".",
                        "linestyle": "-",
                        "linewidth": 1.4,
                        "markersize": 5.0,
                        "legend": label,
                        "export": (f"{label} sigma3", f"{label} sigma1"),
                    }
                )
            # spec 013: effective stress path of the simulated tests (sigma'3, sigma'1)
            for test in material.test_simulations:
                result = self.simulation_result(material, test) if test.visible else None
                if not isinstance(result, sm.SimulationResult):
                    continue
                label = f"{prefix}{test.name}"
                principal.append(
                    {
                        "x": result.sigma3 / 1000.0,
                        "y": result.sigma1 / 1000.0,
                        "color": test.color,
                        "linestyle": "--",
                        "linewidth": 1.3,
                        "legend": label,
                        "export": (f"{label} sigma'3", f"{label} sigma'1"),
                    }
                )
        self._principal.set_layers(principal)
        self._shear.set_layers(shear)
        self._draw_path_graphs()

    def _draw_path_graphs(self) -> None:
        """The four Stress Path Graphs for the visible paths of visible materials."""

        series = {key: [] for key in self._path_canvases}
        multi = len(self._project.materials) > 1
        for material in self._project.materials:
            if not material.visible:
                continue
            for path in material.stress_paths:
                inv = path.invariants() if path.visible else None
                if inv is None:
                    continue
                label = f"{material.name}: {path.name}" if multi else path.name
                kpa = 1000.0  # kPa -> internal MPa
                series["axial"].append((label, inv.eps_a, inv.sigma_a / kpa, path.color))
                series["volumetric"].append((label, inv.eps_a, inv.eps_v, path.color))
                series["deviatoric"].append((label, inv.eps_q, inv.q / kpa, path.color))
                series["pq"].append((label, inv.p / kpa, inv.q / kpa, path.color))
            # spec 013: simulated tests as plain lines
            for test in material.test_simulations:
                result = self.simulation_result(material, test) if test.visible else None
                if not isinstance(result, sm.SimulationResult):
                    continue
                label = f"{material.name}: {test.name}" if multi else test.name
                style = {"marker": "None", "linewidth": 1.6}
                kpa = 1000.0
                series["axial"].append((label, result.axial_strain, result.axial_stress / kpa, test.color, style))
                series["volumetric"].append((label, result.axial_strain, result.eps_v, test.color, style))
                series["deviatoric"].append((label, result.eps_q, result.q / kpa, test.color, style))
                series["pq"].append((label, result.p / kpa, result.q / kpa, test.color, style))
        for key, canvas in self._path_canvases.items():
            canvas.set_series(series[key])
        if hasattr(self, "_path_hint"):
            self._path_hint.setVisible(not any(series.values()))
        if hasattr(self, "_animation"):
            self._animation.refresh_items()

    def _on_path_canvas_menu(self, canvas, kind: str) -> None:
        from PySide6.QtWidgets import QApplication, QFileDialog

        from ..core import export as series_export

        if kind == "copy":
            QApplication.clipboard().setPixmap(canvas.grab())
        elif kind == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, tr("Save graph as image"), "", tr("PNG image (*.png);;JPEG image (*.jpg);;BMP image (*.bmp)")
            )
            if path:
                canvas.save_image(path)
        elif kind == "export":
            path, _ = QFileDialog.getSaveFileName(self, tr("Export graph to CSV"), "", "CSV (*.csv)")  # i18n: ignore (filter)
            if not path:
                return
            if not path.endswith(".csv"):
                path += ".csv"
            self.export_path_graph(canvas, path)

    def export_path_graph(self, canvas, path: str) -> None:
        """CSV of a Stress Path Graph: two columns per path, stresses in the display unit."""

        from ..core import export as series_export

        x_name, y_name = canvas.export_labels()  # English: CSV headers do not follow the language
        kx = canvas.display_scale if canvas._stress_axes[0] else 1.0
        ky = canvas.display_scale if canvas._stress_axes[1] else 1.0
        columns = [(f"{label} {x_name}", f"{label} {y_name}", x * kx, y * ky) for label, x, y in canvas.series_data()]
        if columns:
            series_export.write_series_csv(path, columns, unit="")

    def _draw_other_materials(self) -> None:
        """The other visible materials, in their colors, on both plots."""

        principal, shear = [], []
        for index, material in enumerate(self._project.materials):
            if index == self._current or not material.visible:
                continue
            p_curve, s_curve = ce.envelopes(material.criterion, material.parameters, material.sig3max_mpa)
            color = self._material_color(material)
            if p_curve is not None:
                principal.append((material.name, p_curve[0], p_curve[1], color))
            if s_curve is not None:
                shear.append((material.name, s_curve[0], s_curve[1], color))
        self._principal.set_others(principal)
        self._shear.set_others(shear)

    def _set_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication

        self._theme = name
        self._settings.setValue("theme", name)
        apply_theme(QApplication.instance(), name)
        for canvas in (self._principal, self._shear):
            canvas.apply_theme(name)
        for canvas in self._path_canvases.values():
            canvas.apply_theme(name)
        self._populate_tree()  # automatic-color swatches follow the theme
        self.refresh()

    # ---------------------------------------------------------- spec 017: display units

    def _scale(self) -> float:
        """Display factor for MPa-internal values: display = MPa * scale."""

        return units.stress_factor(self._stress_unit)

    def _kpa_scale(self) -> float:
        """Display factor for registry (kPa) values: display = kPa * scale."""

        return units.stress_factor(self._stress_unit) / 1000.0

    def _sig3max_mpa(self) -> float:
        """Envelope range in internal MPa."""

        return units.from_display(self._sig3max.value(), self._stress_unit)

    def _update_window_title(self) -> None:
        """Document first, as Windows does (spec 025c RF-8): «slope.ogrdata[*] (title) - OGR Data»."""

        name = os.path.basename(self._file_path) if getattr(self, "_file_path", None) else tr("Untitled")
        title = self._project.title.strip()
        # [*]: Qt shows "*" there while the project has unsaved changes (spec 023)
        label = f"{name}[*] ({title})" if title else f"{name}[*]"
        self.setWindowTitle(f"{label} - OGR Data")

    def _set_plot_labels(self) -> None:
        u = self._stress_unit
        self._principal.set_axes_labels(tr("sigma3 ({0})").format(u), tr("sigma1 ({0})").format(u))
        self._shear.set_axes_labels(tr("normal stress ({0})").format(u), tr("shear stress ({0})").format(u))
        for canvas in (self._principal, self._shear):
            canvas.set_display_scale(self._scale())
        for canvas in getattr(self, "_path_canvases", {}).values():
            canvas.set_display(self._scale(), u)

    def _set_stress_unit(self, unit: str) -> None:
        """Switch the display unit, rescaling widgets in place (spec 017).

        Internal values are untouched: the registry stays in kPa and
        sigma3max in MPa; only the displayed numbers and labels change.
        """

        if unit == self._stress_unit or unit not in units.STRESS_FACTORS:
            return
        self._history_hold += 1
        try:
            self._rescale_to(unit)
        finally:
            self._history_hold -= 1
        self._absorb()

    def _rescale_to(self, unit: str) -> None:
        old_scale = self._scale()
        self._stress_unit = unit
        if unit in getattr(self, "_unit_actions", {}):
            self._unit_actions[unit].setChecked(True)
        if hasattr(self, "_unit_combo") and self._unit_combo.currentText() != unit:
            self._unit_combo.blockSignals(True)
            self._unit_combo.setCurrentText(unit)
            self._unit_combo.blockSignals(False)
        self._settings.setValue("stress_unit", unit)
        ratio = self._scale() / old_scale
        for field in self._criterion().fields:
            widget = self._widgets.get(field.key)
            if field.kind == "float" and field.unit == "kPa" and isinstance(widget, QDoubleSpinBox):
                widget.blockSignals(True)
                widget.setValue(widget.value() * ratio)
                widget.setSuffix(f" {unit}")
                widget.blockSignals(False)
        self._sig3max.blockSignals(True)
        self._sig3max.setValue(self._sig3max.value() * ratio)
        self._sig3max.setSuffix(f" {unit}")
        self._sig3max.blockSignals(False)
        self._stiffness_box.rescale(self._kpa_scale(), unit)
        self._set_plot_labels()
        self.refresh()

    # ---------------------------------------------------------- spec 016: graph options and export

    def _open_graph_editor(self) -> None:
        from .graph_editor import GraphEditorDialog

        GraphEditorDialog(self).exec()
        self._checkpoint()

    def _on_canvas_menu(self, canvas, kind: str) -> None:
        from PySide6.QtWidgets import QApplication, QFileDialog

        if kind == "copy":
            QApplication.clipboard().setPixmap(canvas.grab())
        elif kind == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, tr("Save graph as image"), "", tr("PNG image (*.png);;JPEG image (*.jpg);;BMP image (*.bmp)")
            )
            if path:
                canvas.save_image(path)
        elif kind == "export":
            self._export_canvas_csv(canvas)
        elif kind == "zoom":
            canvas.zoom_extents()
        elif kind == "editor":
            self._open_graph_editor()

    def _export_canvas_csv(self, canvas) -> None:
        """Export the plot series to CSV, ready to open in Excel (spec 016)."""

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from ..core import export as series_export

        path, _ = QFileDialog.getSaveFileName(self, tr("Export graph to CSV"), "", "CSV (*.csv)")  # i18n: ignore (filter)
        if not path:
            return
        if not path.endswith(".csv"):
            path += ".csv"
        series = canvas.series_data()
        if canvas.space == "principal":
            labels = {
                "envelope": ("sigma3", "sigma1"),
                "mc": ("MC sigma3", "MC sigma1"),
                "mogi": ("Mogi sigma3", "Mogi sigma1"),
            }
        else:
            labels = {
                "envelope": ("sigma_n", "tau"),
                "mc": ("MC sigma_n", "MC tau"),
            }
        scale = self._scale()
        columns = []
        for key, (x_label, y_label) in labels.items():
            data = series.get(key)
            if data is not None:
                columns.append((x_label, y_label, data[0] * scale, data[1] * scale))
        # spec 011: the other visible materials, labelled by name
        x_name, y_name = labels["envelope"]
        for name, x, y in canvas.other_series():
            columns.append((f"{name} {x_name}", f"{name} {y_name}", x * scale, y * scale))
        # spec 012: failure-state points and stress paths
        for x_col, y_col, x, y in canvas.layer_series():
            columns.append((x_col, y_col, x * scale, y * scale))
        if not columns:
            self.statusBar().showMessage(tr("There is no series to export on this plot."), 6000)
            return
        series_export.write_series_csv(path, columns, unit=self._stress_unit)

    # ---------------------------------------------------------- spec 013: test simulations

    def _stiffness(self) -> dict:
        return self._stiffness_box.values()

    def animation_targets(self):
        """(label, result, color) of the visible simulated tests (spec 013c)."""

        for material in self._project.materials:
            if not material.visible:
                continue
            for test in material.test_simulations:
                if not test.visible:
                    continue
                result = self.simulation_result(material, test)
                if isinstance(result, sm.SimulationResult):
                    yield f"{material.name} - {test.name}", result, test.color

    def show_animation_step(self, result, step: int) -> None:
        """Mark a step of an animated test on the Stress Path Graphs (+ yield surface in q-p)."""

        canvases = self._path_canvases
        if result is None:
            for canvas in canvases.values():
                canvas.show_animation()
            return
        kpa = 1000.0
        i = step
        canvases["axial"].show_animation((result.axial_strain[i], result.axial_stress[i] / kpa))
        canvases["volumetric"].show_animation((result.axial_strain[i], result.eps_v[i]))
        canvases["deviatoric"].show_animation((result.eps_q[i], result.q[i] / kpa))
        p_s, q_s = sm.yield_surface_pq(result, i)
        surface = (p_s / kpa, q_s / kpa) if len(p_s) else None
        canvases["pq"].show_animation((result.p[i] / kpa, result.q[i] / kpa), surface)

    def use_erm_as_young(self) -> None:
        """Young's modulus = Erm of the Generalized Hoek-Brown material (as RSData fills it)."""

        computed = self._ghb_computed()
        if not computed:
            QMessageBox.information(self, tr("Stiffness"), tr("Erm is computed for Generalized Hoek-Brown materials only."))
            return
        self._young.setValue(units.to_display(computed["erm_mpa"], self._stress_unit))

    @staticmethod
    def _simulation_key(material: projects.Material, test) -> str:
        import json

        return json.dumps(
            [material.criterion, material.parameters, material.stiffness, test.to_dict()], sort_keys=True, default=str
        )

    def simulation_result(self, material: projects.Material, test):
        """SimulationResult of a test (cached), or the error message (str)."""

        key = self._simulation_key(material, test)
        if key not in self._sim_cache:
            try:
                self._sim_cache[key] = sm.simulate_material(material, test)
            except sm.SimulationError as exc:
                self._sim_cache[key] = str(exc)
            if len(self._sim_cache) > 256:
                self._sim_cache.pop(next(iter(self._sim_cache)))
        return self._sim_cache[key]

    def compute(self, report_problems: bool = True) -> list[str]:
        """Compute (RSData menu): re-run every test simulation; returns the problems."""

        self._store_current()
        self._sim_cache.clear()
        problems, done = [], 0
        for material in self._project.materials:
            for test in material.test_simulations:
                result = self.simulation_result(material, test)
                if isinstance(result, str):
                    problems.append(f"{material.name} / {test.name}: {result}")
                else:
                    done += 1
        self.refresh()
        if done == 1:
            message = tr("Compute: 1 test simulation computed")
        else:
            message = tr("Compute: {0} test simulations computed").format(done)
        if problems:
            message += tr(", {0} not simulated").format(len(problems))
            if report_problems:
                QMessageBox.information(self, tr("Compute"), "\n".join(problems))
        self.statusBar().showMessage(message, 8000)
        return problems

    # ---------------------------------------------------------- spec 015: report

    def report_project(self) -> projects.Project:
        """The project as it stands, for the report."""

        return self._project_for_save()

    def _canvas_png(self, canvas) -> bytes:
        """PNG of a canvas, drawn with the light theme (the report is for print)."""

        buffer = io.BytesIO()
        themed = self._theme != "light"
        if themed:
            canvas.apply_theme("light")
        try:
            canvas.figure.savefig(buffer, format="png", dpi=110, facecolor="white")
        finally:
            if themed:
                canvas.apply_theme(self._theme)
        return buffer.getvalue()

    def add_view_to_report(self) -> report.ReportView:
        """Add View To Report: the active graph tab of the selected material."""

        self._store_current()
        material = self._current_material()
        if self._graph_tabs.currentIndex() == 0:
            kind = tr("Strength Graphs")
            canvases = [(c.axes.get_title(), c) for c in (self._principal, self._shear)]
        else:
            kind = tr("Stress Path Graphs")
            canvases = [(c.title, c) for c in self._path_canvases.values()]
        sample = self.statusBar().currentMessage() if self._sampler_mode else ""
        view = report.ReportView(
            title=f"{material.name} - {kind}",
            material=material.name,
            criterion=CRITERIA[material.criterion].label,
            stress_unit=self._stress_unit,
            parameters=report.parameter_rows(material, self._stress_unit),
            results=report.computed_rows(material, self._stress_unit),
            images=[(caption, self._canvas_png(canvas)) for caption, canvas in canvases],
            sample=sample,
        )
        self.report_views.add(view)
        n = len(self.report_views)
        message = tr("View added to the report (1 view)") if n == 1 else tr("View added to the report ({0} views)").format(n)
        self.statusBar().showMessage(message, 5000)
        return view

    def _manage_report_views(self) -> None:
        from .report_dialog import ManageReportViewsDialog

        ManageReportViewsDialog(self.report_views, self).exec()

    def _open_report_generator(self) -> None:
        from .report_dialog import ReportGeneratorDialog

        ReportGeneratorDialog(self).exec()

    def _about(self) -> None:
        from .. import __version__

        QMessageBox.about(
            self,
            tr("About OGR Data"),
            tr(
                "<b>OGR Data</b> {0}<br/>"
                "Rock and soil material properties for the OpenGeoRock suite.<br/>"
                "Design language: OGR-Slip2D (QGIS-inspired)."
            ).format(__version__),
        )


    def _open_classifier(self) -> None:
        from .soil_classifier import SoilClassifierDialog

        SoilClassifierDialog(self, on_create=self.add_soil_material).exec()

    def add_soil_material(self, symbol: str, parameters: dict) -> int:
        """New Mohr-Coulomb material from a USCS group (spec 018, UFC 3-220-01N)."""

        material = factory.from_uscs(symbol, parameters, self._current_material().sig3max_mpa)
        self._store_current()
        index = self._project.append(material)
        self._load_material(index)
        self._populate_tree()
        return index

    def _open_fit_dialog(self) -> None:
        from .fit_dialog import FitDialog

        FitDialog(self).exec()

    def apply_fit_parameters(self, result) -> None:
        """Fill the parameter form from a FitResult (spec 006).

        The mapping is core.material_results.fit_to_parameters (shared with
        the API); values are registry kPa/deg, shown in the display unit.
        """

        target, values = mr.fit_to_parameters(result)
        idx = self._criterion_combo.findData(target)
        if idx >= 0:
            self._criterion_combo.setCurrentIndex(idx)
        self._rebuild_form()
        field_units = {f.key: f.unit for f in CRITERIA[target].fields}
        for key, value in values.items():
            if key in self._widgets:
                scale = self._kpa_scale() if field_units.get(key) == "kPa" else 1.0
                self._widgets[key].setValue(value * scale)

    # ------------------------------------------------------------- clipboard

    def _material_name(self) -> str:
        name = self._current_material().name.strip()
        return name or self._criterion().label

    def _ghb_computed(self) -> dict[str, float]:
        return mr.ghb_computed(self._criterion_combo.currentData(), self._params(), self._sig3max_mpa())

    def _copy_material(self) -> None:
        from PySide6.QtWidgets import QApplication

        from ..core import clipboard

        key = self._criterion_combo.currentData()
        text = clipboard.material_text(
            self._material_name(), key, self._params(), self._ghb_computed()
        )
        QApplication.clipboard().setText(text)

    def _copy_data(self) -> None:
        from PySide6.QtWidgets import QApplication

        from ..core import clipboard

        key = self._criterion_combo.currentData()
        QApplication.clipboard().setText(
            clipboard.tabular_data(key, self._params(), self._ghb_computed())
        )

    def _copy_plot_image(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setPixmap(self._principal.grab())

    # ------------------------------------------------------------ projects

    def _project_for_save(self) -> projects.Project:
        """The project with the form state and window settings stored."""

        self._store_current()
        self._project.selected = self._current
        self._project.stress_unit = self._stress_unit
        self._project.graph_options = {
            "principal": self._principal.options.to_dict(),
            "shear": self._shear.options.to_dict(),
        }
        return self._project

    def save_project_to(self, path: str) -> bool:
        """Write the project; marks the saved point of the undo history (spec 023)."""

        if not path.endswith(".ogrdata"):
            path += ".ogrdata"
        self._checkpoint()
        try:
            projects.save_project(path, self._project_for_save())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, tr("Save failed"), str(exc))
            return False
        self._file_path = os.path.abspath(path)
        self._remember_recent(path)
        if self._history is not None:
            self._history.mark_saved()
            self._update_history_ui()
        self._update_window_title()
        self.statusBar().showMessage(tr("Saved {0}").format(path), 5000)
        return True

    def _load_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Open project"), "", tr("OGR Data project (*.ogrdata)"))
        if path:
            self.open_project_file(path)

    def open_project(self, loaded: projects.Project) -> None:
        """Replace the window's project (spec 011; v1 files arrive migrated).

        A new undo history starts here, saved at this state (spec 023).
        """

        self._history_hold += 1
        try:
            self._load_settings_into_window({"stress_unit": loaded.stress_unit})
            self.report_views.clear()  # views belong to the project they were taken from
            self._show_project(loaded)
        finally:
            self._history_hold -= 1
        if self._history is not None:
            self._history.reset(self._state())
            self._update_history_ui()

    def _show_project(self, project: projects.Project) -> None:
        self._project = project
        self._update_window_title()
        for name, canvas in (("principal", self._principal), ("shear", self._shear)):
            raw = project.graph_options.get(name)
            canvas.apply_options(PlotOptions.from_dict(raw) if raw else PlotOptions())
        self._load_material(project.selected)
        self._populate_tree()

    def _new_project(self, confirm: bool = True) -> None:
        if confirm and not self._confirm_discard():
            return
        fresh = projects.Project.new()
        fresh.stress_unit = self._stress_unit  # the display unit is a user setting
        self.open_project(fresh)
        self._file_path = None
        self._update_window_title()

    def _load_settings_into_window(self, data: dict) -> None:
        """Apply the display unit saved in the project (spec 017)."""

        stress_unit = data.get("stress_unit", units.DEFAULT_STRESS_UNIT)
        if stress_unit in units.STRESS_FACTORS:
            self._unit_combo.blockSignals(True)
            self._unit_combo.setCurrentText(stress_unit)
            self._unit_combo.blockSignals(False)
            self._set_stress_unit(stress_unit)

    def _import_roc(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from ..core import roc_import

        path, _ = QFileDialog.getOpenFileName(self, tr("Import RocData file"), "", "RocData (*.roc)")  # i18n: ignore (filter)
        if not path:
            return
        try:
            roc = roc_import.parse_roc(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, tr("Import failed"), str(exc))
            return
        self.import_material(roc.title, roc.criterion, roc.parameters, roc.sig3max_mpa)

    def import_material(self, name: str, criterion: str, parameters: dict, sig3max_mpa: float | None) -> None:
        """Add an imported material (.roc) to the project and select it (spec 011)."""

        self._store_current()
        material = projects.Material(
            name=name or "Imported",
            criterion=criterion,
            parameters=dict(parameters),
            sig3max_mpa=sig3max_mpa if sig3max_mpa is not None else projects.DEFAULT_SIG3MAX_MPA,
        )
        index = self._project.append(material)
        self._load_material(index)
        self._populate_tree()

    def _apply_project(self, criterion: str, parameters: dict, sig3max_mpa: float | None) -> None:
        idx = self._criterion_combo.findData(criterion)
        if idx >= 0:
            self._criterion_combo.setCurrentIndex(idx)
        self._rebuild_form()
        field_units = {f.key: f.unit for f in CRITERIA[criterion].fields}
        for key, value in parameters.items():
            widget = self._widgets.get(key)
            if isinstance(widget, QDoubleSpinBox):
                scale = self._kpa_scale() if field_units.get(key) == "kPa" else 1.0
                widget.setValue(float(value) * scale)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                index = widget.findData(str(value))  # enum options: English value in itemData
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif hasattr(widget, "value") and isinstance(value, (list, tuple)):
                widget.setValue(value)  # table field
        if sig3max_mpa is not None:
            self._sig3max.setValue(float(sig3max_mpa) * self._scale())

    # ------------------------------------------------------------ spec 023: undo / redo

    def _state(self) -> dict:
        """The project as the undo history sees it (title and graph options of the window included)."""

        self._project.selected = self._current
        self._project.graph_options = {
            "principal": self._principal.options.to_dict(),
            "shear": self._shear.options.to_dict(),
        }
        return hist.snapshot(self._project)

    def _checkpoint(self) -> None:
        """Record the project as one step if an edit changed it."""

        if self._history is None or self._history_hold or self._loading:
            return
        self._history.record(self._state())
        self._update_history_ui()

    def _absorb(self) -> None:
        """Take the current project as the history's state without a step."""

        if self._history is not None and not self._history_hold:
            self._history.rebase(self._state())
            self._update_history_ui()

    def _close_history_group(self) -> None:
        if self._history is not None:
            self._history.close_group()

    def _update_history_ui(self) -> None:
        h = self._history
        if h is None:
            return
        self._undo_act.setEnabled(h.can_undo)
        self._redo_act.setEnabled(h.can_redo)
        self._undo_act.setText(tr("Undo {0}").format(h.undo_text_in(tr)) if h.can_undo else tr("Undo"))
        self._redo_act.setText(tr("Redo {0}").format(h.redo_text_in(tr)) if h.can_redo else tr("Redo"))
        accelerators.assign(self._edit_menu)  # the new texts get their Alt letter again (spec 025c)
        self._update_window_title()
        self.setWindowModified(h.modified)

    def undo(self) -> None:
        if self._history is None:
            return
        self._checkpoint()  # an edit not recorded yet (title being typed) comes first
        state = self._history.undo()
        if state is not None:
            self._restore(state)

    def redo(self) -> None:
        if self._history is None:
            return
        self._checkpoint()
        state = self._history.redo()
        if state is not None:
            self._restore(state)

    def _restore(self, state: dict) -> None:
        """Show a state of the history; the display unit is a preference and stays."""

        project = projects.Project.from_dict(state)
        project.stress_unit = self._stress_unit
        self._history_hold += 1
        try:
            self._show_project(project)
        finally:
            self._history_hold -= 1
        self._absorb()

    def _confirm_discard(self) -> bool:
        """True to go on (nothing unsaved, saved, or discarded); False to stay."""

        self._checkpoint()
        if self._history is None or not self._history.modified:
            return True
        if self.ask_unsaved is not None:
            choice = self.ask_unsaved()
        else:
            buttons = QMessageBox.StandardButton
            answer = QMessageBox.question(
                self, tr("Unsaved changes"), tr("The project has unsaved changes. Save them?"),
                buttons.Save | buttons.Discard | buttons.Cancel, buttons.Save,
            )
            choice = {buttons.Save: "save", buttons.Discard: "discard"}.get(answer, "cancel")
        if choice == "save":
            return self._save_project()
        return choice == "discard"

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt)
        if getattr(self, "_replaced", False) or self._confirm_discard():
            event.accept()
            if not getattr(self, "_replaced", False):  # the new window saves its own
                self.save_window_state()
            if self in _OPEN_WINDOWS:
                _OPEN_WINDOWS.remove(self)
        else:
            event.ignore()

    def save_window_state(self) -> None:
        """Remember the results panel and the toolbar (spec 025b RF-4)."""

        self._settings.setValue("window_state", self.saveState())

    # ------------------------------------------------------------ spec 024: language

    def set_language(self, code: str) -> "MainWindow":
        """Switch the interface language: a new window in it takes over this one's
        project, selection, undo history, report views and view options; this one closes.
        The choice is saved for the next start."""

        if code == i18n.current_language():
            return self
        from PySide6.QtWidgets import QApplication

        self._checkpoint()
        self._settings.setValue("language", code)
        i18n.set_language(code)
        i18n.install_qt_translator(QApplication.instance(), code)
        window = MainWindow()
        window.adopt(self)
        window.setGeometry(self.geometry())
        if self.isVisible():
            window.show()
        _OPEN_WINDOWS.append(window)
        self._replaced = True
        self.close()
        return window

    def adopt(self, old: "MainWindow") -> None:
        """Take over the state of another window (language switch)."""

        old._store_current()
        old._project.selected = old._current
        project = old._project
        self.report_views = old.report_views
        self.report_visibility = old.report_visibility
        self._overlay_mc_act.setChecked(old._overlay_mc_act.isChecked())
        self._overlay_mogi_act.setChecked(old._overlay_mogi_act.isChecked())
        self.database_path = old.database_path
        self._history_hold += 1
        try:
            self._show_project(project)
            for name, canvas in (("principal", self._principal), ("shear", self._shear)):
                canvas.apply_options(copy.deepcopy(getattr(old, f"_{name}").options))
        finally:
            self._history_hold -= 1
        self._history = old._history
        self._absorb()
        self._graph_tabs.setCurrentIndex(old._graph_tabs.currentIndex())
        self.restoreState(old.saveState())  # spec 025b: panel and toolbar as they were
        self._file_path = old._file_path  # spec 025c: Save keeps writing to the same file
        self._update_window_title()

    # ------------------------------------------------------------------ form

    def _criterion(self) -> Criterion:
        return CRITERIA[self._criterion_combo.currentData()]

    def _rebuild_form(self) -> None:
        self._stiffness_box.set_criterion(self._criterion_combo.currentData())
        while self._form_layout.rowCount():
            self._form_layout.removeRow(0)
        self._widgets = {}
        for field in self._criterion().fields:
            if field.kind == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(field.default))
                widget.toggled.connect(self.refresh)
            elif field.kind == "enum":
                widget = QComboBox()
                for option in field.options:
                    widget.addItem(tr(option), option)  # i18n: registry
                widget.currentIndexChanged.connect(self.refresh)
            elif field.kind == "table":  # spec 013b: tabular hardening laws
                from .table_field import TableField

                widget = TableField(
                    tr(field.label), field.options, field.stress_columns, field.default,  # i18n: registry
                    lambda: (self._kpa_scale(), self._stress_unit),
                )
                widget.changed.connect(self.refresh)
            else:
                widget = QDoubleSpinBox()
                widget.setDecimals(6)
                widget.setRange(-1e9, 1e12)
                if field.unit == "kPa":
                    widget.setValue(float(field.default) * self._kpa_scale())
                else:
                    widget.setValue(float(field.default))
                if field.unit == "deg":
                    widget.setSuffix(" deg")
                elif field.unit == "kPa":
                    widget.setSuffix(f" {self._stress_unit}")
                widget.valueChanged.connect(self.refresh)
                widget.editingFinished.connect(self._close_history_group)
            self._widgets[field.key] = widget

            editor: QWidget = widget
            if field.pick:
                editor = QWidget()
                row = QHBoxLayout(editor)
                row.setContentsMargins(0, 0, 0, 0)
                row.addWidget(widget, stretch=1)
                pick_button = QPushButton(tr("Pick…"))
                pick_button.clicked.connect(lambda _=False, f=field, w=widget: self._pick(f, w))
                row.addWidget(pick_button)
            self._form_layout.addRow(tr(field.label), editor)  # i18n: registry

    def pick_value(self, key: str) -> float | None:
        """Open the selector of a pick key; the value in registry units (kPa for stresses)."""

        from . import estimation, pickers

        if key == "sigci_grades":
            return pickers.sigci_picker(self)
        if key == "mi_values":
            return estimation.mi_picker(self)
        if key == "gsi_chart":
            return estimation.gsi_dialog(self, self._theme)
        if key == "disturbance":
            return estimation.disturbance_picker(self)
        if key == "modulus_ratio":
            params = self._params()
            sigci = params.get("sigci", params.get("compressive_strength", 0.0))
            return estimation.modulus_ratio_picker(float(sigci), self._stress_unit, self)
        # spec 018
        dialogs = {
            "barton_phi": lambda: estimation.PhiRDialog(self),
            "barton_jrc": lambda: estimation.JrcDialog(float(self._params().get("jrc", 10.0)), self),
            "barton_jcs": lambda: estimation.JcsDialog(float(self._params().get("jrc", 10.0)), self._stress_unit, self),
            "compacted_soil": lambda: estimation.CompactedSoilDialog("", self),
        }
        if key in dialogs:
            dialog = dialogs[key]()
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            try:
                return dialog.value()
            except ValueError as exc:
                QMessageBox.warning(self, tr("Pick"), str(exc))
                return None
        return None

    def _pick(self, field, widget: QDoubleSpinBox) -> None:
        """One-click selectors (spec 022); stresses come in kPa, shown in the display unit."""

        value = self.pick_value(field.pick)
        if isinstance(value, dict):  # several fields at once (e.g. c and phi of a soil)
            self.set_form_values(value)
        elif value is not None:
            if field.unit == "kPa":
                value *= self._kpa_scale()
            widget.setValue(value)

    def set_form_values(self, values: dict) -> None:
        """Set form fields from registry values (kPa for stresses)."""

        units_by_key = {f.key: f.unit for f in self._criterion().fields}
        for key, value in values.items():
            widget = self._widgets.get(key)
            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value) * (self._kpa_scale() if units_by_key.get(key) == "kPa" else 1.0))

    def _params(self) -> dict:
        params = defaults(self._criterion_combo.currentData())
        for field in self._criterion().fields:
            widget = self._widgets[field.key]
            if field.kind == "bool":
                params[field.key] = widget.isChecked()
            elif field.kind == "enum":
                params[field.key] = widget.currentData()
            elif field.kind == "table":
                params[field.key] = widget.value()
            elif field.unit == "kPa":
                # spinbox shows the display unit; the registry stays in kPa
                params[field.key] = widget.value() / self._kpa_scale()
            else:
                params[field.key] = widget.value()
        return params

    # ---------------------------------------------------------- spec 022: Ei and Erm method

    @staticmethod
    def _ghb_input(params: dict, sig3max_mpa: float) -> HbInput:
        """Generalized Hoek-Brown input (MPa) from the registry parameters (kPa)."""

        return mr.ghb_input(params, sig3max_mpa)

    @staticmethod
    def _modulus_method(params: dict) -> ModulusMethod:
        return mr.modulus_method(params)

    # ---------------------------------------------------------- spec 009: sig3max by application

    def _rock_mass_strength_mpa(self, key: str, params: dict) -> float | None:
        """Global rock mass strength sigcm (MPa), for HB-family criteria only."""

        return mr.rock_mass_strength_mpa(key, params, self._sig3max_mpa())

    def _application_sig3max(self) -> float | None:
        """sigma3max from the application mode, or None for manual (custom)."""

        return mr.application_sig3max(
            self._criterion_combo.currentData(), self._params(), self._application_combo.currentData(),
            self._unit_weight.value(), self._app_depth.value(), self._sig3max_mpa(),
        )

    def _update_application(self) -> None:
        key = self._criterion_combo.currentData()
        mode = self._application_combo.currentData()
        if mode != "custom" and key not in ("generalized_hoek_brown", "hoek_brown"):
            # sig3max by application needs sigcm (HB family only, as ORMAS)
            self._application_combo.blockSignals(True)
            self._application_combo.setCurrentIndex(0)
            self._application_combo.blockSignals(False)
            mode = "custom"
        custom = mode == "custom"
        self._sig3max.setEnabled(custom)
        self._sig3max_label.setVisible(custom)
        self._app_fields.setVisible(not custom)
        self._depth_label.setText(tr("Tunnel depth") if mode == "tunnel" else tr("Slope height"))
        self._apply_application()
        self.refresh()

    def _apply_application(self) -> None:
        value = self._application_sig3max()
        if value is None:
            return
        if abs(value - self._sig3max_mpa()) > 1e-12:
            self._sig3max.blockSignals(True)
            self._sig3max.setValue(units.to_display(value, self._stress_unit))
            self._sig3max.blockSignals(False)

    # ---------------------------------------------------------- spec 008: overlays and samplers

    def _hb_terms(self, key: str, params: dict, sig3max: float) -> tuple[float, float, float, float]:
        """(sigci_mpa, mb, s, a) of a Hoek-Brown criterion for the current inputs."""

        return mr.hb_terms(key, params, sig3max)

    def _overlay_mc_params(self, key: str, params: dict, sig3max: float, normal, shear) -> samplers.InstantaneousMC | None:
        """Equivalent / best-fit MC overlay for curved criteria (RocData 2004 p. 10)."""

        if not self._overlay_mc_act.isChecked():
            return None
        if key in mr.HB_FAMILY:
            return mr.overlay_mc(key, params, sig3max)
        if key in ("power_curve", "barton_bandis") and normal is not None:
            return mr.overlay_mc(key, params, sig3max, (normal, shear))
        return None

    def _sampler_mode_changed(self) -> None:
        if self._stress_sampler_act.isChecked():
            self._sampler_mode = "stress"
        elif self._mc_sampler_act.isChecked():
            self._sampler_mode = "mc"
        else:
            self._sampler_mode = None
        if self._sampler_mode is None:
            self._clear_sampler_marks()
            self.statusBar().clearMessage()
            self._results.set_sampler_text("")

    def _clear_sampler_marks(self) -> None:
        self._principal.clear_sample()
        self._shear.clear_sample()

    def _on_plot_event(self, space: str, kind: str, x: float) -> None:
        if self._sampler_mode is None:
            return
        if kind == "press":
            self._dragging = True
        elif kind == "release":
            self._dragging = False
            return
        elif kind == "move" and not self._dragging:
            return
        self._sample_at(space, x)

    @staticmethod
    def _mc_line_value(inst: samplers.InstantaneousMC, x: float) -> float:
        return inst.cohesion_mpa + x * math.tan(math.radians(inst.friction_deg))

    def _sample_at(self, space: str, x: float) -> None:
        sig3max = self._sig3max_mpa()
        xr = np.linspace(0.0, sig3max, 2)
        if space == "principal":
            curve = self._curves["principal"]
            if curve is None:
                return
            sig3, sig1 = curve
            if self._sampler_mode == "stress":
                s = samplers.sample(sig3, sig1, x)
                text = f"sigma3 = {units.stress_text(s.x, self._stress_unit)}   sigma1 = {units.stress_text(s.y, self._stress_unit)}"
                if self._overlay_inst is not None:
                    text += f"   [MC] sigma1 = {units.stress_text(self._mc_line_value(self._overlay_inst, s.x), self._stress_unit)}"
                self._principal.show_sample(s.x)
                self._shear.show_sample(s.x)
            else:
                slope = self._d1_func(x) if self._d1_func is not None else None
                inst = samplers.instantaneous_mc(sig3, sig1, x, slope=slope)
                t_principal = samplers.mc_tangent_principal(inst, xr)
                t_shear = samplers.mc_tangent_shear(inst, xr)
                # tangency point of the tangent Mohr circle on the shear plot
                sin_phi = math.sin(math.radians(inst.friction_deg))
                centre = (inst.point_y + inst.point_x) / 2.0
                radius = (inst.point_y - inst.point_x) / 2.0
                n_t = centre - radius * sin_phi
                t_t = radius * math.cos(math.radians(inst.friction_deg))
                self._principal.show_sample(inst.point_x, tangent=t_principal, marker=(inst.point_x, inst.point_y))
                self._shear.show_sample(n_t, tangent=t_shear, marker=(n_t, t_t))
                text = (
                    f"c = {units.stress_text(inst.cohesion_mpa, self._stress_unit)}   phi = {inst.friction_deg:.2f} deg   "
                    f"sigma3 = {units.stress_text(inst.point_x, self._stress_unit)}   sigma1 = {units.stress_text(inst.point_y, self._stress_unit)}   "
                    f"sigma_n = {units.stress_text(n_t, self._stress_unit)}   tau = {units.stress_text(t_t, self._stress_unit)}"
                )
            self._show_sample_text(i18n.localize(text))
            return

        # shear-space click
        curve = self._curves["shear"]
        if curve is None:
            return
        normal, shear = curve
        if self._sampler_mode == "stress":
            s = samplers.sample(normal, shear, x)
            text = f"sigma_n = {units.stress_text(s.x, self._stress_unit)}   tau = {units.stress_text(s.y, self._stress_unit)}"
            if self._overlay_inst is not None:
                text += f"   [MC] tau = {units.stress_text(self._mc_line_value(self._overlay_inst, s.x), self._stress_unit)}"
            self._shear.show_sample(s.x)
            if self._curves["principal"] is not None:
                self._principal.show_sample(s.x)
        else:
            inst = samplers.instantaneous_mc_shear(normal, shear, x)
            t_shear = samplers.mc_tangent_shear(inst, xr)
            self._shear.show_sample(inst.point_x, tangent=t_shear, marker=(inst.point_x, inst.point_y))
            # converted MC line in principal space (also for shear-space criteria)
            t_principal = samplers.mc_tangent_principal(inst, xr)
            self._principal.show_sample(None, tangent=t_principal)
            text = (
                f"c = {units.stress_text(inst.cohesion_mpa, self._stress_unit)}   phi = {inst.friction_deg:.2f} deg   "
                f"sigma_n = {units.stress_text(inst.point_x, self._stress_unit)}   tau = {units.stress_text(inst.point_y, self._stress_unit)}"
            )
        self._show_sample_text(i18n.localize(text))

    def _show_sample_text(self, text: str) -> None:
        """The sampler's reading, in the status bar and the results panel (spec 025b RF-8)."""

        self.statusBar().showMessage(text)
        self._results.set_sampler_text(text)

    # --------------------------------------------------------------- refresh

    def refresh(self) -> None:
        """Redraw from the form and record the edit that led here (spec 023)."""

        self._redraw()
        self._checkpoint()

    def _redraw(self) -> None:
        key = self._criterion_combo.currentData()
        if key is None or not self._widgets:
            return
        params = self._params()
        self._apply_application()
        sig3max = self._sig3max_mpa()
        crit = CRITERIA[key]
        self._store_current()

        self._clear_sampler_marks()
        self._curves = {"principal": None, "shear": None}
        self._d1_func = None
        self._overlay_inst = None
        # spec 011: selected material's color/visibility, other materials
        material = self._current_material()
        for canvas in (self._principal, self._shear):
            canvas.set_primary(material.color, material.visible, material.name)
        self._draw_other_materials()
        self._draw_test_data()

        if crit.envelope == "none":
            self._principal.redraw([], [])
            self._shear.redraw([], [])
            self._results.set_message(self._results_heading(), tr("envelope not available for this criterion yet"))
            return

        if crit.envelope == "principal":
            curve = ce.principal_curve(key, params, sig3max)
            if curve is None:
                self._results.set_message(self._results_heading(), tr("No envelope for these parameters."))
                return
            sig3, sig1 = curve
            normal, shear = ce.tangent_shear(sig3, sig1)
            self._curves["principal"] = (sig3, sig1)
            self._curves["shear"] = (normal, shear)
            if key in ("generalized_hoek_brown", "hoek_brown"):
                sigci_mpa, mb, s, a = self._hb_terms(key, params, sig3max)
                self._d1_func = lambda v, sc=sigci_mpa, m=mb, sv=s, av=a: samplers.hb_derivative(v, sc, m, sv, av)

            self._overlay_inst = self._overlay_mc_params(key, params, sig3max, normal, shear)
            if self._overlay_inst is not None:
                (p3, p1), (n_mc, s_mc) = ce.mc_line(
                    self._overlay_inst.cohesion_mpa, self._overlay_inst.friction_deg, sig3max
                )
                self._principal.redraw(sig3, sig1, p3, p1)
                self._shear.redraw(normal, shear, n_mc, s_mc)
            else:
                self._principal.redraw(sig3, sig1)
                self._shear.redraw(normal, shear)

            if key == "generalized_hoek_brown":
                inp = self._ghb_input(params, sig3max)
                result = compute(inp, self._modulus_method(params))
                unit = self._stress_unit
                rows = [
                    ("mb", f"{result.mb:.4f}"),
                    ("s", f"{result.s:.4f}"),
                    ("a", f"{result.a:.4f}"),
                    ("sigt", units.stress_text(result.sigt, unit)),
                    ("sigc", units.stress_text(result.sigc, unit)),
                    ("sigcm", units.stress_text(result.sigcm, unit)),
                    ("c", units.stress_text(result.mc.cohesion, unit)),
                    ("phi", f"{result.mc.friction_deg:.2f} deg"),
                    ("Erm", units.stress_text(result.erm, unit, decimals=2)),
                ]
                self._results.set_results(self._results_heading(), [(k, i18n.localize(v)) for k, v in rows])
            else:
                self._show_derived_results()
        else:
            # shear-space criteria
            curve = ce.shear_curve(key, params, sig3max)
            if curve is None:
                self._results.set_message(self._results_heading(), tr("No envelope for these parameters."))
                return
            normal, shear = curve
            self._curves["shear"] = (normal, shear)
            self._overlay_inst = self._overlay_mc_params(key, params, sig3max, normal, shear)
            if self._overlay_inst is not None:
                (p3, p1), (n_mc, s_mc) = ce.mc_line(
                    self._overlay_inst.cohesion_mpa, self._overlay_inst.friction_deg, sig3max
                )
                # the equivalent MC line is shown in both spaces
                self._principal.redraw([], [], p3, p1)
                self._shear.redraw(normal, shear, n_mc, s_mc)
            else:
                self._principal.redraw([], [])
                self._shear.redraw(normal, shear)
            self._show_derived_results()

        if self._overlay_mogi_act.isChecked() and self._curves["principal"] is not None:
            self._principal.show_mogi(*samplers.mogi_line(sig3max))
        else:
            self._principal.clear_mogi()
        if not material.visible:
            # a hidden material is still edited, but neither drawn nor sampled
            self._curves = {"principal": None, "shear": None}
            self._overlay_inst = None
