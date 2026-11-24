"""Pick dialogs: bibliographic tables (spec 003)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..core import tables
from .i18n import localize, tr
from .number_spin import NumberSpinBox


class TablePickerDialog(QDialog):
    """Searchable table dialog; exec returns the picked value (MPa for sigci).

    ``columns[0]`` names the hidden value column; the others are the headers shown
    (translated by the caller, spec 024).
    """

    def __init__(self, title: str, columns: list[str], rows: list[list[str]], source: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 480)
        self._rows = rows
        self._values: list[float] = [float(r[0]) for r in rows]

        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Filter…"))
        self._search.textChanged.connect(self._filter)
        self._table = QTableWidget(len(rows), len(columns) - 1)
        self._table.setHorizontalHeaderLabels(columns[1:])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self.accept)
        for i, r in enumerate(rows):
            for j in range(1, len(columns)):
                self._table.setItem(i, j - 1, QTableWidgetItem(localize(str(r[j]))))
        self._table.resizeColumnsToContents()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._table)
        layout.addWidget(QLabel(tr("Source: {0}").format(source)))
        layout.addWidget(buttons)
        self._filter("")

    def _filter(self, text: str) -> None:
        text = text.lower()
        for i, r in enumerate(self._rows):
            visible = all(t in str(c).lower() for t in text.split()) if text else True
            self._table.setRowHidden(i, not visible)

    def value(self) -> float | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._values[row]


def sigci_picker(parent=None) -> float | None:
    """Pick dialog for intact UCS from Hoek Table 2 (value in kPa)."""

    data = tables.rock_strength_grades()
    rows = [
        [g["ucs_pick_mpa"] * 1000.0, g["grade"], g["term"], f'{g["ucs_lo_mpa"]}–{g["ucs_hi_mpa"] if g["ucs_hi_mpa"] else ">" + str(g["ucs_lo_mpa"])} MPa', g["examples"]]
        for g in data["grades"]
    ]
    dlg = TablePickerDialog(
        tr("Pick sigci — field estimates of UCS (Hoek, Table 2)"),
        ["value_kpa", tr("Grade"), tr("Term"), tr("UCS range"), tr("Examples")],
        rows,
        data["source"],
        parent,
    )
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.value()
    return None


def mi_picker(parent=None) -> float | None:
    """Pick dialog for mi from Hoek Table 3."""

    data = tables.mi_values()
    rows = [
        [
            v["mi"],
            v["rock"],
            v["rock_type"],
            v["class"] or "",
            v["group"] or "",
            v["texture"] or "",
            f'{v["mi"]} ± {v["std"]}' + (" (est.)" if v["estimated"] else ""),
        ]
        for v in data["values"]
    ]
    dlg = TablePickerDialog(
        tr("Pick mi — Hoek-Brown constant for intact rock (Hoek, Table 3)"),
        ["value", tr("Rock"), tr("Type"), tr("Class"), tr("Group"), tr("Texture"), "mi ± std"],
        rows,
        data["source"],
        parent,
    )
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.value()
    return None


class GsiPickerDialog(QDialog):
    """Structure x surface selector over the Hoek & Marinos (2000) chart."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Pick GSI — Hoek & Marinos (2000) chart"))
        self.resize(560, 320)
        data = tables.gsi_chart()

        self._structure = QComboBox()
        for s in data["structures"]:
            self._structure.addItem(s["label"], s["key"])
        self._surface = QComboBox()
        for s in data["surfaces"]:
            self._surface.addItem(s["label"], s["key"])

        self._structure_desc = QLabel()
        self._structure_desc.setWordWrap(True)
        self._surface_desc = QLabel()
        self._surface_desc.setWordWrap(True)
        self._range_label = QLabel()
        self._value = NumberSpinBox()
        self._value.setRange(1.0, 100.0)

        self._structure.currentIndexChanged.connect(self._update)
        self._surface.currentIndexChanged.connect(self._update)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Structure of the rock mass")))
        layout.addWidget(self._structure)
        layout.addWidget(self._structure_desc)
        layout.addWidget(QLabel(tr("Surface condition of discontinuities")))
        layout.addWidget(self._surface)
        layout.addWidget(self._surface_desc)
        layout.addWidget(self._range_label)
        row = QHBoxLayout()
        row.addWidget(QLabel("GSI"))
        row.addWidget(self._value)
        layout.addLayout(row)
        layout.addWidget(QLabel(tr("Source: {0}").format(data["source"]) + "\n" + data["note"]))
        layout.addWidget(buttons)
        self._update()

    def _update(self) -> None:
        data = tables.gsi_chart()
        s_key = self._structure.currentData()
        f_key = self._surface.currentData()
        s = next(x for x in data["structures"] if x["key"] == s_key)
        f = next(x for x in data["surfaces"] if x["key"] == f_key)
        self._structure_desc.setText(s["description"])
        self._surface_desc.setText(f["description"])
        rng = tables.gsi_range(s_key, f_key)
        if rng is None:
            self._range_label.setText(tr("Combination not present on the published chart (N/A)."))
            self._value.setEnabled(False)
        else:
            self._range_label.setText(tr("Indicative GSI range on the chart: {0:.0f}–{1:.0f}").format(rng[0], rng[1]))
            self._value.setEnabled(True)
            self._value.setRange(rng[0], rng[1])
            self._value.setValue((rng[0] + rng[1]) / 2.0)

    def gsi(self) -> float | None:
        if not self._value.isEnabled():
            return None
        return self._value.value()


def gsi_picker(parent=None) -> float | None:
    dlg = GsiPickerDialog(parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.gsi()
    return None
