# SPDX-License-Identifier: AGPL-3.0-or-later
"""One sentence per menu action, shown in the status bar (spec 025f RF-2).

Keyed by the English text of the action (the translation key), so the menu
code stays as it is; :func:`apply` walks the menu bar once it is built.
"""

from __future__ import annotations

from .accelerators import plain
from .i18n import tr


def _t(text: str) -> str:
    """Marks an English text that is translated where it is shown (spec 024)."""

    return text


TIPS = {
    _t("New Project"): _t("Start a new project with one default material."),
    _t("Open…"): _t("Open an OGR Data project (.ogrdata)."),
    _t("Recent Projects"): _t("Open one of the last projects opened or saved."),
    _t("Save"): _t("Save the project to its file, or choose one if it has none."),
    _t("Save As…"): _t("Save the project to a new file."),
    _t("Import .roc…"): _t("Add the material of a .roc file to the project."),
    _t("Project Settings…"): _t("Project title and display stress unit."),
    _t("Exit"): _t("Close OGR Data (asks to save unsaved changes)."),
    _t("Undo"): _t("Undo the last change to the project."),
    _t("Redo"): _t("Redo the last change undone."),
    _t("Copy material"): _t("Copy the selected material for OGR Slip2D and OGR FEM2D (all decimals)."),
    _t("Copy data"): _t("Copy the material's parameters and results as a table, for a spreadsheet."),
    _t("Copy plot"): _t("Copy the principal stress graph as an image."),
    _t("Delete"): _t("Delete the material, failure state, stress path or simulation selected in the tree."),
    _t("Theme"): _t("Light or dark colours for the window and the graphs."),
    _t("Language"): _t("Interface language; the window reopens in it, keeping the project."),
    _t("Stress unit"): _t("Unit in which stresses are shown; files and clipboard stay in kPa."),
    _t("Graph Editor…"): _t("Axes, grid, lines and legend of the strength graphs."),
    _t("Results panel"): _t("Show or hide the panel with the computed parameters."),
    _t("Toolbar"): _t("Show or hide the toolbar."),
    _t("Add Material"): _t("Add a material with the default parameters."),
    _t("Add Rock Template"): _t("Add a Generalized Hoek-Brown rock material."),
    _t("Add Soil Template"): _t("Add a Mohr-Coulomb soil material."),
    _t("Duplicate Material"): _t("Add a copy of the selected material."),
    _t("Rename Material"): _t("Rename the selected material."),
    "Color…": _t("Choose the colour of the selected material in the graphs."),
    _t("Automatic color"): _t("Give the selected material the colour of the theme."),
    _t("Symbol"): _t("Marker of the selected material's failure-state points."),
    _t("Delete Material"): _t("Delete the selected material (Undo brings it back)."),
    _t("Material Database…"): _t("Search the database of measured rock and soil properties and use a record."),
    _t("Soil classifier (USCS)…"): _t("Classify a soil from its grading and Atterberg limits and create its material."),
    _t("Fit lab data…"): _t("Fit the selected criterion to triaxial or direct shear test data."),
    _t("Define Failure States…"): _t("Test points at failure of the selected material."),
    _t("Define Stress Paths…"): _t("Laboratory stress paths of the selected material."),
    _t("Define Test Simulations…"): _t("Laboratory tests to simulate with the selected material's model."),
    _t("Compute"): _t("Run every test simulation of the project."),
    _t("Calibrate…"): _t("Fit a new material to the selected failure states."),
    _t("Stress Sampler"): _t("Click a graph to read the stresses on the envelope."),
    _t("Instantaneous MC Sampler"): _t("Click a graph to read the tangent Mohr-Coulomb c and phi at that point."),
    _t("Overlay MC Envelope"): _t("Draw the equivalent Mohr-Coulomb envelope over the stress range."),
    _t("Overlay Mogi Line"): _t("Draw Mogi's line sigma1 = 3.4 sigma3 (brittle-ductile transition)."),
    _t("Report Generator…"): _t("Write the project report as a self-contained HTML file."),
    _t("Add View To Report"): _t("Add the graphs on screen, with their parameters, to the report."),
    _t("Manage Report View…"): _t("Rename, reorder or remove the views added to the report."),
    _t("Keyboard Shortcuts"): _t("List of the keyboard shortcuts."),
    _t("About OGR Data"): _t("Version and licence of OGR Data."),
}


def apply(menu_bar) -> None:
    """Set the status tip of every menu action whose text has one."""

    from ..core.numbers import symbols

    tips = {tr(key): tip for key, tip in TIPS.items()}  # i18n: registry (keys marked with _t)

    def walk(container) -> None:
        for action in container.actions():
            tip = tips.get(plain(action.text()))
            if tip:
                action.setStatusTip(symbols(tr(tip)))  # i18n: registry (texts marked with _t)
            if action.menu() is not None:
                walk(action.menu())

    walk(menu_bar)
