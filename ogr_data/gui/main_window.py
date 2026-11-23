"""Main window of OGR Data: criterion-driven sidebar + two plots."""

from __future__ import annotations

import io
import math

import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
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
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import application
from ..core import criteria_envelopes as ce
from ..core import project as projects
from ..core import report
from ..core import samplers
from ..core import states as st
from ..core import units
from ..core.graph_options import PlotOptions
from ..core.hoek_brown import HbInput, ModulusMethod, compute, equivalent_mc, global_strength, hoek_brown_constants
from ..core.models import CRITERIA, MODULUS_METHODS, Criterion, defaults
from .plots import EnvelopeCanvas, PathCanvas
from .themes import THEMES, apply_theme


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OGR Data")
        self.resize(1150, 640)

        self._settings = QSettings("OpenGeoRock", "OGR-Data")
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
        self._current = 0
        self._loading = True
        self._tree_updating = False
        # spec 015: graph views added to the report (session only) and the
        # section visibility chosen in the Report Generator
        self.report_views = report.ReportViews()
        self.report_visibility = report.default_visibility()
        from PySide6.QtWidgets import QApplication

        apply_theme(QApplication.instance(), self._theme)
        self._create_menus()

        self._criterion_combo = QComboBox()
        for key, crit in CRITERIA.items():
            self._criterion_combo.addItem(crit.label, key)
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

        # spec 009: sigma3max by application (tunnel / slope)
        self._application_combo = QComboBox()
        for label, app_key in (("Custom", "custom"), ("Tunnel", "tunnel"), ("Slope", "slope")):
            self._application_combo.addItem(label, app_key)
        self._application_combo.currentIndexChanged.connect(self._update_application)
        self._unit_weight = QDoubleSpinBox()
        self._unit_weight.setRange(0.0001, 1.0)
        self._unit_weight.setDecimals(4)
        self._unit_weight.setValue(0.026)
        self._unit_weight.setSingleStep(0.001)
        self._unit_weight.setSuffix(" MN/m3")
        self._unit_weight.valueChanged.connect(self.refresh)
        self._app_depth = QDoubleSpinBox()
        self._app_depth.setRange(0.1, 10000.0)
        self._app_depth.setValue(50.0)
        self._app_depth.setSuffix(" m")
        self._app_depth.valueChanged.connect(self.refresh)
        self._app_fields = QWidget()
        app_form = QFormLayout(self._app_fields)
        app_form.setContentsMargins(0, 0, 0, 0)
        self._depth_label = QLabel("Tunnel depth")
        app_form.addRow("Unit weight", self._unit_weight)
        app_form.addRow(self._depth_label, self._app_depth)
        self._app_fields.setVisible(False)

        self._form_box = QGroupBox("Parameters")
        self._form_layout = QFormLayout(self._form_box)
        self._widgets: dict[str, object] = {}

        self._outputs = QLabel()
        self._outputs.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._outputs.setMinimumWidth(280)
        self._outputs.setStyleSheet("font-family: Consolas, monospace;")

        sidebar = QVBoxLayout()
        sidebar.addWidget(self._build_material_panel())
        sidebar.addWidget(QLabel("Failure criterion"))
        sidebar.addWidget(self._criterion_combo)
        self._classifier_button = QPushButton("Soil classifier (USCS)…")
        self._classifier_button.clicked.connect(self._open_classifier)
        sidebar.addWidget(self._classifier_button)
        self._fit_button = QPushButton("Fit lab data…")
        self._fit_button.clicked.connect(self._open_fit_dialog)
        sidebar.addWidget(self._fit_button)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Material name")
        self._name_edit.setText(self._project.materials[0].name)
        self._name_edit.textChanged.connect(self._name_edited)
        self._name_edit.editingFinished.connect(self._name_edit_finished)
        sidebar.addWidget(self._name_edit)
        # spec 017: display stress unit and project title
        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel("Stress unit"))
        self._unit_combo = QComboBox()
        for unit_name in units.STRESS_FACTORS:
            self._unit_combo.addItem(unit_name)
        self._unit_combo.setCurrentText(self._stress_unit)
        unit_row.addWidget(self._unit_combo)
        sidebar.addLayout(unit_row)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Project title")
        self._title_edit.textChanged.connect(self._update_window_title)
        sidebar.addWidget(self._title_edit)
        copy_row = QHBoxLayout()
        copy_material = QPushButton("Copy material")
        copy_material.clicked.connect(self._copy_material)
        copy_data = QPushButton("Copy data")
        copy_data.clicked.connect(self._copy_data)
        copy_image = QPushButton("Copy plot")
        copy_image.clicked.connect(self._copy_plot_image)
        copy_row.addWidget(copy_material)
        copy_row.addWidget(copy_data)
        copy_row.addWidget(copy_image)
        sidebar.addLayout(copy_row)
        file_row = QHBoxLayout()
        save_button = QPushButton("Save…")
        save_button.clicked.connect(self._save_project)
        load_button = QPushButton("Load…")
        load_button.clicked.connect(self._load_project)
        import_button = QPushButton("Import .roc…")
        import_button.clicked.connect(self._import_roc)
        file_row.addWidget(save_button)
        file_row.addWidget(load_button)
        file_row.addWidget(import_button)
        sidebar.addLayout(file_row)
        sidebar.addWidget(QLabel("Application (sigma3max range)"))
        sidebar.addWidget(self._application_combo)
        self._sig3max_label = QLabel("sig3max (envelope range)")
        sidebar.addWidget(self._sig3max_label)
        sidebar.addWidget(self._sig3max)
        sidebar.addWidget(self._app_fields)
        sidebar.addWidget(self._form_box)
        sidebar.addWidget(QLabel("Computed"))
        sidebar.addWidget(self._outputs, stretch=1)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setMaximumWidth(360)
        scroll = QScrollArea()
        scroll.setWidget(sidebar_widget)
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(380)

        self._principal = EnvelopeCanvas("Principal Stresses", f"sigma3 ({self._stress_unit})", f"sigma1 ({self._stress_unit})", self._theme, space="principal")
        self._shear = EnvelopeCanvas("Shear - Normal Stresses", f"normal stress ({self._stress_unit})", f"shear stress ({self._stress_unit})", self._theme, space="shear")
        for canvas in (self._principal, self._shear):
            canvas.sampler_handler = self._on_plot_event
            canvas.menu_handler = self._on_canvas_menu
            canvas.set_display_scale(self._scale())

        plots = QSplitter(Qt.Orientation.Horizontal)
        plots.addWidget(self._principal)
        plots.addWidget(self._shear)

        # spec 012: Stress Path Graphs tab (RSData's four default graphs; the
        # second shows volumetric strain: path tables hold no pore pressure)
        self._path_canvases = {
            "axial": PathCanvas("Axial Stress vs Axial Strain", "Axial Strain", "Axial Stress", False, True, self._theme),
            "volumetric": PathCanvas("Volumetric Strain vs Axial Strain", "Axial Strain", "Volumetric Strain", False, False, self._theme),
            "deviatoric": PathCanvas("q vs Deviatoric Strain", "Deviatoric Strain", "q", False, True, self._theme),
            "pq": PathCanvas("q vs p", "p", "q", True, True, self._theme),
        }
        path_page = QWidget()
        path_grid = QGridLayout(path_page)
        for index, canvas in enumerate(self._path_canvases.values()):
            canvas.menu_handler = self._on_path_canvas_menu
            canvas.set_display(self._scale(), self._stress_unit)
            path_grid.addWidget(canvas, index // 2, index % 2)
        self._graph_tabs = QTabWidget()
        self._graph_tabs.addTab(plots, "Strength Graphs")
        self._graph_tabs.addTab(path_page, "Stress Path Graphs")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self._graph_tabs)
        splitter.setStretchFactor(1, 1)
        # the sidebar opens at its full width (no clipped buttons)
        splitter.setSizes([380, 770])
        self.setCentralWidget(splitter)
        self.statusBar()

        self._rebuild_form()
        self._overlay_mc_act.setChecked(True)
        self._unit_combo.currentTextChanged.connect(self._set_stress_unit)
        self._loading = False
        self._populate_tree()
        self.refresh()

    # ----------------------------------------------------------------- menus

    def _create_menus(self) -> None:
        bar = QMenuBar(self)
        self.setMenuBar(bar)

        file_menu = bar.addMenu("File")
        file_menu.addAction("New Project", self._new_project)
        file_menu.addAction("Save…", self._save_project)
        file_menu.addAction("Load…", self._load_project)
        file_menu.addAction("Import .roc…", self._import_roc)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        edit_menu = bar.addMenu("Edit")
        edit_menu.addAction("Copy material", self._copy_material)
        edit_menu.addAction("Copy data", self._copy_data)

        materials_menu = bar.addMenu("Materials")
        materials_menu.addAction("Add Material", lambda: self._add_material("material"))
        materials_menu.addAction("Add Rock Template", lambda: self._add_material("rock"))
        materials_menu.addAction("Add Soil Template", lambda: self._add_material("soil"))
        materials_menu.addSeparator()
        materials_menu.addAction("Duplicate Material", self._duplicate_material)
        materials_menu.addAction("Rename Material", self._rename_material)
        materials_menu.addAction("Delete Material", self._delete_material)

        # spec 012
        states_menu = bar.addMenu("Failure States")
        states_menu.addAction("Define Failure States…", lambda: self._define_failure_states())
        paths_menu = bar.addMenu("Stress Paths")
        paths_menu.addAction("Define Stress Paths…", lambda: self._define_stress_paths())
        # spec 014
        calibrate_menu = bar.addMenu("Calibrate")
        calibrate_menu.addAction("Calibrate…", self._open_calibration)

        analysis_menu = bar.addMenu("Analysis")
        self._stress_sampler_act = QAction("Stress Sampler", self, checkable=True)
        self._mc_sampler_act = QAction("Instantaneous MC Sampler", self, checkable=True)
        sampler_group = QActionGroup(self)
        sampler_group.setExclusive(True)
        sampler_group.addAction(self._stress_sampler_act)
        sampler_group.addAction(self._mc_sampler_act)
        analysis_menu.addAction(self._stress_sampler_act)
        analysis_menu.addAction(self._mc_sampler_act)
        analysis_menu.addSeparator()
        self._overlay_mc_act = QAction("Overlay MC Envelope", self, checkable=True)
        self._overlay_mogi_act = QAction("Overlay Mogi Line", self, checkable=True)
        analysis_menu.addAction(self._overlay_mc_act)
        analysis_menu.addAction(self._overlay_mogi_act)
        analysis_menu.addSeparator()
        analysis_menu.addAction("Material Database…", self._open_database)  # spec 010 (RSData: Open RocProp)
        analysis_menu.addSeparator()
        # spec 015 (RSData names)
        analysis_menu.addAction("Report Generator…", self._open_report_generator)
        analysis_menu.addAction("Add View To Report", self.add_view_to_report)
        analysis_menu.addAction("Manage Report View…", self._manage_report_views)
        self._stress_sampler_act.toggled.connect(self._sampler_mode_changed)
        self._mc_sampler_act.toggled.connect(self._sampler_mode_changed)
        self._overlay_mc_act.toggled.connect(self.refresh)
        self._overlay_mogi_act.toggled.connect(self.refresh)

        view_menu = bar.addMenu("View")
        theme_menu = view_menu.addMenu("Theme")
        for name in THEMES:
            theme_menu.addAction(name.capitalize(), lambda _=False, n=name: self._set_theme(n))
        view_menu.addSeparator()
        view_menu.addAction("Graph Editor…", self._open_graph_editor)

        help_menu = bar.addMenu("Help")
        help_menu.addAction("About OGR Data", self._about)

    # ------------------------------------------------- spec 011: materials

    def _build_material_panel(self) -> QWidget:
        """Materials tree (RSData's Visibility panel) with its buttons."""

        box = QGroupBox("Materials")
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
        layout.addWidget(self._tree)

        buttons = QHBoxLayout()
        self._add_button = QToolButton()
        self._add_button.setText("Add Material")
        self._add_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        add_menu = QMenu(self._add_button)
        add_menu.addAction("Add Rock Template", lambda: self._add_material("rock"))
        add_menu.addAction("Add Soil Template", lambda: self._add_material("soil"))
        self._add_button.setMenu(add_menu)
        self._add_button.clicked.connect(lambda: self._add_material("material"))
        self._duplicate_button = QPushButton("Duplicate")
        self._duplicate_button.clicked.connect(self._duplicate_material)
        self._delete_button = QPushButton("Delete")
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
                item.setToolTip(0, f"{material.name} ({CRITERIA[material.criterion].label})")
                self._tree.addTopLevelItem(item)
                # spec 012: failure states and stress paths of the material
                children = [("state", i, s, st.FAILURE_TEST_TYPES[s.test_type]) for i, s in enumerate(material.failure_states)]
                children += [("path", i, p, st.PATH_TEST_TYPES[p.test_type]) for i, p in enumerate(material.stress_paths)]
                for kind, index, obj, test_label in children:
                    child = QTreeWidgetItem([obj.name])
                    child.setFlags(
                        Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )
                    child.setData(0, Qt.ItemDataRole.UserRole, (kind, index))
                    child.setCheckState(0, Qt.CheckState.Checked if obj.visible else Qt.CheckState.Unchecked)
                    child.setIcon(0, self._swatch(obj.color))
                    noun = "Failure state" if kind == "state" else "Stress path"
                    child.setToolTip(0, f"{noun}: {obj.name} ({test_label})")
                    item.addChild(child)
            self._tree.expandAll()
            self._tree.setCurrentItem(self._tree.topLevelItem(self._current))
        finally:
            self._tree_updating = False
        self._delete_button.setEnabled(len(self._project.materials) > 1)

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
        item = self._tree.topLevelItem(self._current)
        if item is not None:
            self._tree_updating = True
            item.setToolTip(0, f"{material.name} ({CRITERIA[material.criterion].label})")
            self._tree_updating = False

    def _load_material(self, index: int) -> None:
        """Show material `index` in the form and plots."""

        self._current = index
        material = self._current_material()
        self._loading = True
        try:
            app = material.application
            for widget, value in ((self._unit_weight, app.unit_weight), (self._app_depth, app.depth)):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
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
            objects = material.failure_states if kind == "state" else material.stress_paths
            objects[sub].visible = item.checkState(0) == Qt.CheckState.Checked
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
            item.setToolTip(0, f"{name} ({CRITERIA[material.criterion].label})")
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

    def _delete_material(self, confirm: bool = True) -> None:
        if len(self._project.materials) <= 1:
            return
        name = self._current_material().name
        if confirm:
            answer = QMessageBox.question(self, "Delete material", f"Delete material '{name}'?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        index = self._project.remove(self._current)
        self._load_material(index)
        self._populate_tree()

    def _set_material_color(self, color: str) -> None:
        self._current_material().color = color
        self._populate_tree()
        self.refresh()

    def _choose_material_color(self) -> None:
        initial = QColor(self._material_color(self._current_material()))
        color = QColorDialog.getColor(initial, self, "Material color")
        if color.isValid():
            self._set_material_color(color.name())

    def _set_material_symbol(self, symbol: str) -> None:
        if symbol in projects.SYMBOLS:
            self._current_material().symbol = symbol

    def _tree_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        if item is not None:
            self._tree.setCurrentItem(item)
        if item is not None and item.parent() is not None:
            self._child_menu(item, pos)
            return
        menu = QMenu(self)
        menu.addAction("Add Material", lambda: self._add_material("material"))
        menu.addAction("Add Rock Template", lambda: self._add_material("rock"))
        menu.addAction("Add Soil Template", lambda: self._add_material("soil"))
        if item is not None:
            menu.addSeparator()
            menu.addAction("Duplicate Material", self._duplicate_material)
            menu.addAction("Rename", self._rename_material)
            menu.addAction("Color…", self._choose_material_color)
            menu.addAction("Automatic color", lambda: self._set_material_color(""))
            symbol_menu = menu.addMenu("Symbol")
            current = self._current_material().symbol
            for symbol, label in projects.SYMBOLS.items():
                act = symbol_menu.addAction(label, lambda s=symbol: self._set_material_symbol(s))
                act.setCheckable(True)
                act.setChecked(symbol == current)
            menu.addAction("Copy material", self._copy_material)
            menu.addSeparator()
            menu.addAction("Define Failure States…", lambda: self._define_failure_states())
            menu.addAction("Define Stress Paths…", lambda: self._define_stress_paths())
            menu.addSeparator()
            delete = menu.addAction("Delete Material", lambda: self._delete_material())
            delete.setEnabled(len(self._project.materials) > 1)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ------------------------------------- spec 012: failure states and stress paths

    def _child_menu(self, item, pos) -> None:
        kind, sub = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        if kind == "state":
            menu.addAction("Edit Failure State…", lambda: self._define_failure_states(sub))
        else:
            menu.addAction("Edit Stress Path…", lambda: self._define_stress_paths(sub))
        menu.addAction("Delete", lambda: self._delete_child(kind, sub))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _tree_double_clicked(self, item, _column) -> None:
        if item.parent() is None:
            return  # material rows: double click renames in place
        kind, sub = item.data(0, Qt.ItemDataRole.UserRole)
        if kind == "state":
            self._define_failure_states(sub)
        else:
            self._define_stress_paths(sub)

    def _delete_child(self, kind: str, index: int) -> None:
        material = self._current_material()
        objects = material.failure_states if kind == "state" else material.stress_paths
        if 0 <= index < len(objects):
            del objects[index]
        self._populate_tree()
        self.refresh()

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
            QMessageBox.warning(self, "Material Database", str(exc))
            return
        DatabaseDialog(database, self, on_use=self.use_database_record, on_use_state=self.use_database_specimens).exec()

    def use_database_specimens(self, record: dict) -> None:
        """Failure state of the selected material from the record's specimens (sigma3, sigma1)."""

        from ..core import database as mdb

        points = mdb.specimen_points(record)
        if not points:
            raise ValueError("the record has no specimens with sigma3 and sigma1")
        material = self._current_material()
        name = st.unique_name(mdb.title(record) or "Database", (s.name for s in material.failure_states))
        state = st.FailureState(
            name=name,
            color=st.next_color(s.color for s in material.failure_states),
            points=[st.TestPoint(s3, s1, exclude) for s3, s1, exclude in points],
        )
        self.set_failure_states(material.failure_states + [state])
        self.statusBar().showMessage(f"Failure state '{name}' added to {material.name} ({len(points)} points from record {record.get('record_id')}).")

    def use_database_record(self, record: dict) -> int:
        """New Generalized Hoek-Brown material from a database record (sigci, mi)."""

        from ..core import database as mdb

        params = defaults("generalized_hoek_brown")
        params.update(mdb.to_material_parameters(record))
        material = projects.Material(
            name=mdb.title(record) or "Material",
            criterion="generalized_hoek_brown",
            parameters=params,
            sig3max_mpa=self._current_material().sig3max_mpa,
        )
        self._store_current()
        index = self._project.append(material)
        self._load_material(index)
        self._populate_tree()
        self.statusBar().showMessage(
            f"Material created from database record {record.get('record_id')}: GSI and D keep their defaults; set them for the rock mass."
        )
        return index

    # ------------------------------------------------- spec 014: calibration

    def _open_calibration(self) -> None:
        from .calibration_dialog import CalibrationDialog

        self._store_current()
        dialog = CalibrationDialog(self, self._project, self._current, self._stress_unit)
        if dialog.exec() and dialog.result is not None:
            self.add_calibrated_material(dialog.name.text(), dialog.result)

    def add_calibrated_material(self, name: str, result) -> int:
        """New material from a calibration (the source material is not changed)."""

        material = projects.Material(
            name=name.strip() or "Calibrated Material",
            criterion=result.criterion,
            parameters=dict(result.parameters),
            sig3max_mpa=self._current_material().sig3max_mpa,
        )
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
        for key, canvas in self._path_canvases.items():
            canvas.set_series(series[key])

    def _on_path_canvas_menu(self, canvas, kind: str) -> None:
        from PySide6.QtWidgets import QApplication, QFileDialog

        from ..core import export as series_export

        if kind == "copy":
            QApplication.clipboard().setPixmap(canvas.grab())
        elif kind == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save graph as image", "", "PNG image (*.png);;JPEG image (*.jpg);;BMP image (*.bmp)"
            )
            if path:
                canvas.save_image(path)
        elif kind == "export":
            path, _ = QFileDialog.getSaveFileName(self, "Export graph to CSV", "", "CSV (*.csv)")
            if not path:
                return
            if not path.endswith(".csv"):
                path += ".csv"
            self.export_path_graph(canvas, path)

    def export_path_graph(self, canvas, path: str) -> None:
        """CSV of a Stress Path Graph: two columns per path, stresses in the display unit."""

        from ..core import export as series_export

        x_name, y_name = canvas.axes.get_xlabel(), canvas.axes.get_ylabel()
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
        title = self._title_edit.text().strip()
        self.setWindowTitle(f"OGR Data - {title}" if title else "OGR Data")

    def _set_plot_labels(self) -> None:
        u = self._stress_unit
        self._principal.set_axes_labels(f"sigma3 ({u})", f"sigma1 ({u})")
        self._shear.set_axes_labels(f"normal stress ({u})", f"shear stress ({u})")
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
        old_scale = self._scale()
        self._stress_unit = unit
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
        self._set_plot_labels()
        self.refresh()

    # ---------------------------------------------------------- spec 016: graph options and export

    def _open_graph_editor(self) -> None:
        from .graph_editor import GraphEditorDialog

        GraphEditorDialog(self).exec()

    def _on_canvas_menu(self, canvas, kind: str) -> None:
        from PySide6.QtWidgets import QApplication, QFileDialog

        if kind == "copy":
            QApplication.clipboard().setPixmap(canvas.grab())
        elif kind == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save graph as image", "", "PNG image (*.png);;JPEG image (*.jpg);;BMP image (*.bmp)"
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

        path, _ = QFileDialog.getSaveFileName(self, "Export graph to CSV", "", "CSV (*.csv)")
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
            QMessageBox.information(self, "Export", "There is no series to export on this plot.")
            return
        series_export.write_series_csv(path, columns, unit=self._stress_unit)

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
            kind = "Strength Graphs"
            canvases = [(c.axes.get_title(), c) for c in (self._principal, self._shear)]
        else:
            kind = "Stress Path Graphs"
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
        self.statusBar().showMessage(f"View added to the report ({n} view{'s' if n != 1 else ''})", 5000)
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
            "About OGR Data",
            f"<b>OGR Data</b> {__version__}<br/>"
            "Rock and soil material properties for the OpenGeoRock suite.<br/>"
            "Design language: OGR-Slip2D (QGIS-inspired).",
        )


    def _open_classifier(self) -> None:
        from .soil_classifier import SoilClassifierDialog

        SoilClassifierDialog(self, on_create=self.add_soil_material).exec()

    def add_soil_material(self, symbol: str, parameters: dict) -> int:
        """New Mohr-Coulomb material from a USCS group (spec 018, UFC 3-220-01N)."""

        params = defaults("mohr_coulomb")
        params.update(parameters)
        params["residual_cohesion"] = params["peak_cohesion"]
        params["residual_friction"] = params["peak_friction"]
        material = projects.Material(
            name=f"{symbol} (typical compacted, UFC 3-220-01N)",
            criterion="mohr_coulomb",
            parameters=params,
            sig3max_mpa=self._current_material().sig3max_mpa,
        )
        self._store_current()
        index = self._project.append(material)
        self._load_material(index)
        self._populate_tree()
        return index

    def _open_fit_dialog(self) -> None:
        from .fit_dialog import FitDialog

        FitDialog(self).exec()

    def apply_fit_parameters(self, result) -> None:
        """Fill the parameter form from a FitResult (spec 006)."""

        from ..core.fitting import DIRECT, TRIAXIAL

        mapping: dict[str, tuple[str, dict[str, float]]] = {
            # criterion to select -> {fit parameter: form field}
            "mohr_coulomb": (
                "mohr_coulomb",
                {"cohesion_mpa": ("peak_cohesion", 1000.0), "friction_deg": ("peak_friction", 1.0)},
            ),
            "hoek_brown": (
                "hoek_brown",
                {"sigci_mpa": ("compressive_strength", 1000.0), "mi": ("mb", 1.0)},
            ),
            "generalized_hoek_brown": (
                "hoek_brown",
                {"mb": ("mb", 1.0), "s": ("s", 1.0)},
            ),
            "barton_bandis": (
                "barton_bandis",
                {"jrc": ("jrc", 1.0), "jcs_mpa": ("jcs", 1000.0)},
            ),
            "power_curve": (
                "power_curve",
                {"a": ("a", 1.0), "b": ("b", 1.0), "d_mpa": ("d", 1000.0)},
            ),
        }
        target, fields = mapping[result.criterion]
        idx = self._criterion_combo.findData(target)
        if idx >= 0:
            self._criterion_combo.setCurrentIndex(idx)
        self._rebuild_form()
        for fit_key, (field_key, scale) in fields.items():
            if fit_key in result.parameters and field_key in self._widgets:
                self._widgets[field_key].setValue(result.parameters[fit_key] * scale)
        if target == "hoek_brown" and result.criterion == "hoek_brown":
            if "s" in self._widgets:
                self._widgets["s"].setValue(1.0)
        if target == "barton_bandis" and "phi_r" in self._widgets and result.fixed:
            if "phi_b_deg" in result.fixed:
                self._widgets["phi_r"].setValue(result.fixed["phi_b_deg"])

    # ------------------------------------------------------------- clipboard

    def _material_name(self) -> str:
        name = self._current_material().name.strip()
        return name or self._criterion().label

    def _ghb_computed(self) -> dict[str, float]:
        key = self._criterion_combo.currentData()
        if key != "generalized_hoek_brown":
            return {}
        params = self._params()
        inp = self._ghb_input(params, self._sig3max_mpa())
        result = compute(inp, self._modulus_method(params))
        return {
            "mb": result.mb,
            "s": result.s,
            "a": result.a,
            "sigt_mpa": result.sigt,
            "sigc_mpa": result.sigc,
            "sigcm_mpa": result.sigcm,
            "c_mpa": result.mc.cohesion,
            "phi_deg": result.mc.friction_deg,
            "erm_mpa": result.erm,
        }

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
        self._project.title = self._title_edit.text()
        self._project.stress_unit = self._stress_unit
        self._project.graph_options = {
            "principal": self._principal.options.to_dict(),
            "shear": self._shear.options.to_dict(),
        }
        return self._project

    def _save_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Save project", "", "OGR Data project (*.ogrdata)")
        if not path:
            return
        if not path.endswith(".ogrdata"):
            path += ".ogrdata"
        try:
            projects.save_project(path, self._project_for_save())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def _load_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Load project", "", "OGR Data project (*.ogrdata)")
        if not path:
            return
        try:
            loaded = projects.load_project(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Load failed", str(exc))
            return
        self.open_project(loaded)

    def open_project(self, loaded: projects.Project) -> None:
        """Replace the window's project (spec 011; v1 files arrive migrated)."""

        self._load_settings_into_window({"stress_unit": loaded.stress_unit})
        self._project = loaded
        self.report_views.clear()  # views belong to the project they were taken from
        self._title_edit.setText(loaded.title)
        for name, canvas in (("principal", self._principal), ("shear", self._shear)):
            raw = loaded.graph_options.get(name)
            canvas.apply_options(PlotOptions.from_dict(raw) if raw else PlotOptions())
        self._load_material(loaded.selected)
        self._populate_tree()

    def _new_project(self, confirm: bool = True) -> None:
        if confirm:
            answer = QMessageBox.question(self, "New project", "Discard the current project and start a new one?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        fresh = projects.Project.new()
        fresh.stress_unit = self._stress_unit  # the display unit is a user setting
        self.open_project(fresh)

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

        path, _ = QFileDialog.getOpenFileName(self, "Import RocData file", "", "RocData (*.roc)")
        if not path:
            return
        try:
            roc = roc_import.parse_roc(path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
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
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
        if sig3max_mpa is not None:
            self._sig3max.setValue(float(sig3max_mpa) * self._scale())

    # ------------------------------------------------------------------ form

    def _criterion(self) -> Criterion:
        return CRITERIA[self._criterion_combo.currentData()]

    def _rebuild_form(self) -> None:
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
                widget.addItems(field.options)
                widget.currentIndexChanged.connect(self.refresh)
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
            self._widgets[field.key] = widget

            editor: QWidget = widget
            if field.pick:
                editor = QWidget()
                row = QHBoxLayout(editor)
                row.setContentsMargins(0, 0, 0, 0)
                row.addWidget(widget, stretch=1)
                pick_button = QPushButton("Pick…")
                pick_button.clicked.connect(lambda _=False, f=field, w=widget: self._pick(f, w))
                row.addWidget(pick_button)
            self._form_layout.addRow(field.label, editor)

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
                QMessageBox.warning(self, "Pick", str(exc))
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
                params[field.key] = widget.currentText()
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

        return HbInput(
            sigci=float(params["sigci"]) / 1000.0,
            gsi=float(params["gsi"]),
            mi=float(params["mi"]),
            disturbance=float(params["d"]),
            ei=float(params.get("ei", 12000000.0)) / 1000.0,
            sig3max=sig3max_mpa,
        )

    @staticmethod
    def _modulus_method(params: dict) -> ModulusMethod:
        label = params.get("modulus_method", MODULUS_METHODS[0])
        index = MODULUS_METHODS.index(label) if label in MODULUS_METHODS else 0
        return list(ModulusMethod)[index]

    # ---------------------------------------------------------- spec 009: sig3max by application

    def _rock_mass_strength_mpa(self, key: str, params: dict) -> float | None:
        """Global rock mass strength sigcm (MPa), for HB-family criteria only."""

        if key == "generalized_hoek_brown":
            inp = self._ghb_input(params, self._sig3max_mpa())
            return compute(inp, self._modulus_method(params)).sigcm
        if key == "hoek_brown":
            sigci_mpa, mb, s, a = self._hb_terms(key, params, self._sig3max_mpa())
            inp = HbInput(sigci=sigci_mpa, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=self._sig3max_mpa())
            return global_strength(inp, mb, s, a)
        return None

    def _application_sig3max(self) -> float | None:
        """sigma3max from the application mode, or None for manual (custom)."""

        mode = self._application_combo.currentData()
        if mode == "custom":
            return None
        key = self._criterion_combo.currentData()
        sigcm = self._rock_mass_strength_mpa(key, self._params())
        if sigcm is None or sigcm <= 0.0:
            return None
        if mode == "tunnel":
            return application.sig3max_tunnel(sigcm, self._unit_weight.value(), self._app_depth.value())
        return application.sig3max_slope(sigcm, self._unit_weight.value(), self._app_depth.value())

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
        self._depth_label.setText("Tunnel depth" if mode == "tunnel" else "Slope height")
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

        if key == "generalized_hoek_brown":
            inp = self._ghb_input(params, sig3max)
            mb, s, a = hoek_brown_constants(inp)
            return inp.sigci, mb, s, a
        # classic Hoek-Brown is the 2002 criterion with a = 0.5
        return float(params["compressive_strength"]) / 1000.0, float(params["mb"]), float(params["s"]), 0.5

    def _overlay_mc_params(self, key: str, params: dict, sig3max: float, normal, shear) -> samplers.InstantaneousMC | None:
        """Equivalent / best-fit MC overlay for curved criteria (RocData 2004 p. 10)."""

        if not self._overlay_mc_act.isChecked():
            return None
        if key in ("generalized_hoek_brown", "hoek_brown"):
            sigci_mpa, mb, s, a = self._hb_terms(key, params, sig3max)
            # Hoek (2002) closed form (eqs. 12-13) over sigt < sigma3 < sig3max;
            # only sigci and sig3max of inp are used by the formulation.
            inp = HbInput(sigci=sigci_mpa, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max)
            mc = equivalent_mc(inp, mb, s, a)
            return samplers.InstantaneousMC(mc.cohesion, mc.friction_deg, 0.0, 0.0, 0.0)
        if key in ("power_curve", "barton_bandis") and normal is not None:
            return samplers.best_fit_mc(normal, shear)
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
            self.statusBar().showMessage(text)
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
        self.statusBar().showMessage(text)

    # --------------------------------------------------------------- refresh

    def refresh(self) -> None:
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
            self._outputs.setText("envelope not available for this criterion yet")
            return

        if crit.envelope == "principal":
            curve = ce.principal_curve(key, params, sig3max)
            if curve is None:
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
                self._outputs.setText(
                    f"mb   = {result.mb:.4f}\n"
                    f"s    = {result.s:.4f}\n"
                    f"a    = {result.a:.4f}\n"
                    f"sigt = {units.stress_text(result.sigt, self._stress_unit)}\n"
                    f"sigc = {units.stress_text(result.sigc, self._stress_unit)}\n"
                    f"sigcm= {units.stress_text(result.sigcm, self._stress_unit)}\n"
                    f"c    = {units.stress_text(result.mc.cohesion, self._stress_unit)}\n"
                    f"phi  = {result.mc.friction_deg:.2f} deg\n"
                    f"Erm  = {units.stress_text(result.erm, self._stress_unit, decimals=2)}"
                )
            else:
                self._outputs.setText("")
        else:
            # shear-space criteria
            curve = ce.shear_curve(key, params, sig3max)
            if curve is None:
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
            self._outputs.setText("")

        if self._overlay_mogi_act.isChecked() and self._curves["principal"] is not None:
            self._principal.show_mogi(*samplers.mogi_line(sig3max))
        else:
            self._principal.clear_mogi()
        if not material.visible:
            # a hidden material is still edited, but neither drawn nor sampled
            self._curves = {"principal": None, "shear": None}
            self._overlay_inst = None
