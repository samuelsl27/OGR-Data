"""Define Failure States / Define Stress Paths dialogs (spec 012).

Modelled on RSData's dialogs (captures 31_* and 32_*): list of objects on
the left (add, delete, duplicate, move up/down), editor on the right
(name and color, test settings) and point tables with cut / copy / paste
/ insert row / delete rows / import / export. The dialogs edit copies;
OK hands the edited list back, Cancel discards it.

Stress columns show the display unit (spec 017); storage stays in kPa.
"""

from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import states as st
from ..core import units
from ..core.project import SYMBOLS
from .i18n import localize, tr


def _header_text(name: str) -> str:
    """A column name on screen: RSData's symbol-like names stay, words are translated.

    The English name is kept for the CSV files (they do not change with the language).
    """

    words = {"Pore Water Pressure": tr("Pore Water Pressure"), "Exclude": tr("Exclude")}
    for english, shown in words.items():
        if name == english or name.startswith(english + " ("):
            return shown + name[len(english):]
    return name


def _swatch(color: str) -> QIcon:
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class PointTable(QWidget):
    """Numeric table with an optional trailing check column (Exclude).

    column_scales converts stored values to displayed ones
    (shown = stored * scale) per numeric column.
    """

    def __init__(self, headers: list[str], column_scales: list[float], flag_header: str = "", parent=None) -> None:
        super().__init__(parent)
        self._numeric = len(column_scales)
        self._scales = list(column_scales)
        self._flag = bool(flag_header)
        self._headers = list(headers) + ([flag_header] if self._flag else [])  # English (CSV)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        for label, slot in (
            (tr("Cut"), self.cut),
            (tr("Copy"), self.copy),
            (tr("Paste"), self.paste),
            (tr("Insert Row"), self.insert_row),
            (tr("Delete Rows"), self.delete_rows),
            (tr("Import…"), self.import_csv),
            (tr("Export…"), self.export_csv),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, f=slot: f())
            tools.addWidget(button)
        tools.addStretch(1)
        layout.addLayout(tools)
        self.table = QTableWidget(0, self._numeric + (1 if self._flag else 0))
        self.table.setHorizontalHeaderLabels([_header_text(h) for h in self._headers])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def reconfigure(self, headers: list[str], column_scales: list[float], flag_header: str = "") -> None:
        """Change the columns (test type / direction), keeping the values by position."""

        kept = []
        for r in range(self.table.rowCount()):
            row = []
            for c in range(self._numeric):
                item = self.table.item(r, c)
                try:
                    row.append(float(item.text().replace(",", ".")) / self._scales[c] if item and item.text().strip() else 0.0)
                except ValueError:
                    row.append(0.0)
            if self._flag:
                item = self.table.item(r, self._numeric)
                row.append(item is not None and item.checkState() == Qt.CheckState.Checked)
            kept.append(row)
        self._numeric = len(column_scales)
        self._scales = list(column_scales)
        flag_values = [row[-1] for row in kept] if self._flag else [False] * len(kept)
        self._flag = bool(flag_header)
        self.table.setRowCount(0)
        self.table.setColumnCount(self._numeric + (1 if self._flag else 0))
        self._headers = list(headers) + ([flag_header] if self._flag else [])
        self.table.setHorizontalHeaderLabels([_header_text(h) for h in self._headers])
        for row, flag in zip(kept, flag_values):
            numbers = [v for v in row if not isinstance(v, bool)][: self._numeric]
            numbers += [0.0] * (self._numeric - len(numbers))
            self._append(numbers + ([flag] if self._flag else []))

    # ------------------------------------------------------------- values

    def set_rows(self, rows) -> None:
        """Fill from stored rows: tuples of numbers (+ flag)."""

        self.table.setRowCount(0)
        for row in rows:
            self._append(row)

    def _append(self, row, at: int | None = None) -> None:
        r = self.table.rowCount() if at is None else at
        if at is None or at >= self.table.rowCount():
            self.table.insertRow(r)
        for c in range(self._numeric):
            value = float(row[c]) * self._scales[c]
            self.table.setItem(r, c, QTableWidgetItem(localize(f"{value:.10g}")))
        if self._flag:
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            flag = bool(row[self._numeric]) if len(row) > self._numeric else False
            item.setCheckState(Qt.CheckState.Checked if flag else Qt.CheckState.Unchecked)
            self.table.setItem(r, self._numeric, item)

    def rows(self) -> list[tuple]:
        """Stored rows; blank rows are skipped, invalid numbers raise ValueError."""

        out = []
        for r in range(self.table.rowCount()):
            texts = [(self.table.item(r, c).text().strip() if self.table.item(r, c) else "") for c in range(self._numeric)]
            if not any(texts):
                continue
            try:
                values = [float(t.replace(",", ".")) / self._scales[c] for c, t in enumerate(texts)]
            except ValueError:
                raise ValueError(tr("row {0}: enter a number in every column").format(r + 1)) from None
            if self._flag:
                item = self.table.item(r, self._numeric)
                values.append(item is not None and item.checkState() == Qt.CheckState.Checked)
            out.append(tuple(values))
        return out

    def _displayed_rows(self, only_selected: bool) -> list[list[str]]:
        selected = sorted({i.row() for i in self.table.selectedIndexes()})
        indices = selected if (only_selected and selected) else range(self.table.rowCount())
        lines = []
        for r in indices:
            cells = [(self.table.item(r, c).text() if self.table.item(r, c) else "") for c in range(self._numeric)]
            if self._flag:
                item = self.table.item(r, self._numeric)
                cells.append("1" if item is not None and item.checkState() == Qt.CheckState.Checked else "0")
            lines.append(cells)
        return lines

    # ------------------------------------------------------------ actions

    def copy(self) -> None:
        text = "\n".join("\t".join(cells) for cells in self._displayed_rows(only_selected=True))
        QApplication.clipboard().setText(text)

    def cut(self) -> None:
        self.copy()
        self.delete_rows()

    def paste(self) -> None:
        self.paste_text(QApplication.clipboard().text())

    def paste_text(self, text: str) -> int:
        """Excel-like paste: rows overwrite from the current row down."""

        rows = st.parse_rows(text, self._numeric, self._flag)
        start = self.table.currentRow()
        if start < 0:
            start = self.table.rowCount()
        for i, row in enumerate(rows):
            # pasted values are in the displayed unit
            stored = [row[c] / self._scales[c] for c in range(self._numeric)] + list(row[self._numeric:])
            self._append(stored, at=start + i)
        return len(rows)

    def insert_row(self) -> None:
        r = self.table.currentRow()
        r = self.table.rowCount() if r < 0 else r
        self.table.insertRow(r)
        if self._flag:
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(r, self._numeric, item)

    def delete_rows(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows and self.table.currentRow() >= 0:
            rows = [self.table.currentRow()]
        for r in rows:
            self.table.removeRow(r)

    def import_csv(self, path: str | None = None) -> int:
        """Append rows from a CSV/text file (values in the displayed unit)."""

        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, tr("Import points"), "", tr("CSV / text (*.csv *.txt);;All files (*)"))
            if not path:
                return 0
        try:
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read()
        except OSError as exc:
            QMessageBox.warning(self, tr("Import failed"), str(exc))
            return 0
        self.table.setCurrentCell(-1, -1)
        return self.paste_text(text)

    def export_csv(self, path: str | None = None) -> None:
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr("Export points"), "", "CSV (*.csv)")  # i18n: ignore
            if not path:
                return
            if not path.endswith(".csv"):
                path += ".csv"
        headers = list(self._headers)  # English: files do not change with the language
        shown = [
            tuple(row[c] * self._scales[c] for c in range(self._numeric)) + tuple(row[self._numeric:])
            for row in self.rows()
        ]
        st.write_rows_csv(path, headers, shown)


class _ItemsDialog(QDialog):
    """List of objects + editor; subclasses provide the editor."""

    noun = "Item"

    def __init__(self, parent, title: str, items: list, unit: str, initial: int = 0) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(780, 470)
        self.items = [copy.deepcopy(i) for i in items]
        self._unit = unit
        self._kpa_scale = units.stress_factor(unit) / 1000.0  # shown = kPa * scale
        self._row = -1
        self._loading = False

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._row_changed)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._list)
        buttons = QHBoxLayout()
        self._list_buttons: list[QPushButton] = []
        for label, slot in (
            (tr("Add"), self.add_item),  # spec 025d RF-3: a word, not "+"
            (tr("Delete"), self.delete_item),
            (tr("Duplicate"), self.duplicate_item),
            (tr("Up"), lambda: self.move_item(-1)),
            (tr("Down"), lambda: self.move_item(1)),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, f=slot: f())
            buttons.addWidget(button)
            self._list_buttons.append(button)
        left_layout.addLayout(buttons)

        self._editor = QWidget()
        editor_layout = QVBoxLayout(self._editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.addWidget(QLabel(tr("Name")))
        self._name = QLineEdit()
        self._name.textEdited.connect(self._name_edited)
        header.addWidget(self._name, stretch=1)
        self._color = QPushButton()
        self._color.setFixedWidth(64)
        self._color.clicked.connect(self._pick_color)
        header.addWidget(self._color)
        editor_layout.addLayout(header)
        self._build_editor(editor_layout)

        # spec 025d RF-3: an empty list shows its first step, not a disabled editor
        self._empty = QLabel(self.empty_hint())
        self._empty.setWordWrap(True)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._empty, stretch=1)
        right_layout.addWidget(self._editor, stretch=1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([220, 560])
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(box)

        self._refresh_list()
        if self.items:
            self._list.setCurrentRow(max(0, min(initial, len(self.items) - 1)))
        self._editor.setEnabled(bool(self.items))
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        self._empty.setVisible(not self.items)
        self._editor.setVisible(bool(self.items))
        # Delete, Duplicate, Up, Down act on an item: off while there is none
        for button in self._list_buttons[1:]:
            button.setEnabled(bool(self.items))

    # ------------------------------------------------ subclass interface

    def empty_hint(self) -> str:
        return tr("Nothing here yet. Click Add to create the first one.")

    def _build_editor(self, layout: QVBoxLayout) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _new_item(self, name: str, color: str):  # pragma: no cover - abstract
        raise NotImplementedError

    def _load(self, item) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _store(self, item) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # ------------------------------------------------------------ list

    def _refresh_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for item in self.items:
            entry = QListWidgetItem(_swatch(item.color), item.name)
            self._list.addItem(entry)
        self._list.setCurrentRow(self._row)
        self._list.blockSignals(False)

    def _try_store(self) -> bool:
        try:
            self.store_current()
        except ValueError as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return False
        return True

    def _row_changed(self, row: int) -> None:
        if self._loading:
            return
        if not self._try_store():
            # keep the item with the invalid table selected
            self._list.blockSignals(True)
            self._list.setCurrentRow(self._row)
            self._list.blockSignals(False)
            return
        self._row = row
        self._editor.setEnabled(0 <= row < len(self.items))
        self._show_empty_state()
        if 0 <= row < len(self.items):
            self._loading = True
            try:
                item = self.items[row]
                self._name.setText(item.name)
                self._set_color(item.color)
                self._load(item)
            finally:
                self._loading = False

    def store_current(self) -> None:
        """Write the editor back into the current item (raises on bad tables)."""

        if 0 <= self._row < len(self.items) and not self._loading:
            self._store(self.items[self._row])

    def _select(self, row: int) -> None:
        self._row = -1  # nothing to store: the list changed under the editor
        self._refresh_list()
        self._list.blockSignals(True)
        self._list.setCurrentRow(row)
        self._list.blockSignals(False)
        self._row_changed(row)

    def add_item(self) -> None:
        if not self._try_store():
            return
        taken = {i.name for i in self.items}
        n = 1
        while f"{self.noun} {n}" in taken:
            n += 1
        self.items.append(self._new_item(f"{self.noun} {n}", st.next_color(i.color for i in self.items)))
        self._select(len(self.items) - 1)

    def delete_item(self) -> None:
        if not (0 <= self._row < len(self.items)):
            return
        del self.items[self._row]
        self._select(min(self._row, len(self.items) - 1))

    def duplicate_item(self) -> None:
        if not (0 <= self._row < len(self.items)) or not self._try_store():
            return
        item = copy.deepcopy(self.items[self._row])
        item.name = st.unique_name(f"{item.name} - Copy", (i.name for i in self.items))
        item.color = st.next_color(i.color for i in self.items)
        self.items.insert(self._row + 1, item)
        self._select(self._row + 1)

    def move_item(self, step: int) -> None:
        row, target = self._row, self._row + step
        if not (0 <= row < len(self.items) and 0 <= target < len(self.items)) or not self._try_store():
            return
        self.items[row], self.items[target] = self.items[target], self.items[row]
        self._select(target)

    def _name_edited(self, text: str) -> None:
        if 0 <= self._row < len(self.items) and text.strip():
            self.items[self._row].name = text.strip()
            self._list.item(self._row).setText(text.strip())

    def _set_color(self, color: str) -> None:
        self._color.setStyleSheet(f"background-color: {color};")
        self._color.setProperty("color_value", color)

    def _pick_color(self) -> None:
        if not (0 <= self._row < len(self.items)):
            return
        chosen = QColorDialog.getColor(QColor(self._color.property("color_value") or st.DEFAULT_COLOR), self, "Color")  # i18n: ignore
        if chosen.isValid():
            self._set_color(chosen.name())
            self.items[self._row].color = chosen.name()
            self._list.item(self._row).setIcon(_swatch(chosen.name()))

    def accept(self) -> None:
        if self._try_store():
            super().accept()


class FailureStatesDialog(_ItemsDialog):
    """One point table per state, columns per Test Type (RSData 1.009)."""

    noun = "State"

    def empty_hint(self) -> str:
        return tr("No failure states yet. Click Add, then type or import the test points of the state.")

    def __init__(self, parent, material_name: str, failure_states: list, unit: str, initial: int = 0) -> None:
        super().__init__(parent, tr("Define Failure States - {0}").format(material_name), failure_states, unit, initial)

    def _build_editor(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self._symbol = QComboBox()
        for key, label in SYMBOLS.items():
            self._symbol.addItem(tr(label), key)  # i18n: registry
        form.addRow(tr("Symbol:"), self._symbol)
        self._test_type = QComboBox()
        for key, label in st.FAILURE_TEST_TYPES.items():
            self._test_type.addItem(tr(label), key)  # i18n: registry
        self._test_type.currentIndexChanged.connect(self._test_type_changed)
        form.addRow(tr("Test Type:"), self._test_type)
        layout.addLayout(form)
        self._points = PointTable([], [self._kpa_scale, self._kpa_scale], "Exclude")
        layout.addWidget(self._points, stretch=1)
        self._configure("triaxial")

    def _configure(self, test_type: str) -> None:
        columns = st.FailureState(test_type=test_type).columns
        headers = [f"{c} ({self._unit})" for c in columns]
        flag = "" if test_type == "general" else "Exclude"
        self._points.reconfigure(headers, [self._kpa_scale] * len(columns), flag)

    def _test_type_changed(self) -> None:
        self._configure(self._test_type.currentData())

    def _new_item(self, name: str, color: str):
        return st.FailureState(name=name, color=color)

    def _load(self, item: st.FailureState) -> None:
        self._symbol.setCurrentIndex(max(0, self._symbol.findData(item.symbol)))
        self._test_type.blockSignals(True)
        self._test_type.setCurrentIndex(max(0, self._test_type.findData(item.test_type)))
        self._test_type.blockSignals(False)
        self._configure(item.test_type)
        if item.test_type == "general":
            self._points.set_rows(item.tensors)
        else:
            self._points.set_rows([p.to_list() for p in item.points])

    def _store(self, item: st.FailureState) -> None:
        item.symbol = self._symbol.currentData()
        item.test_type = self._test_type.currentData()
        rows = self._points.rows()
        if item.test_type == "general":
            item.tensors = [tuple(row[:6]) for row in rows]
        else:
            item.points = [st.TestPoint(*row) for row in rows]


class StressPathsDialog(_ItemsDialog):
    """Fields and columns per configuration, as verified in RSData 1.009."""

    noun = "Path"

    def empty_hint(self) -> str:
        return tr("No stress paths yet. Click Add, then choose the test type and type or import its readings.")

    def __init__(self, parent, material_name: str, stress_paths: list, unit: str, initial: int = 0) -> None:
        super().__init__(parent, tr("Define Stress Paths - {0}").format(material_name), stress_paths, unit, initial)

    def _build_editor(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()

        def combo(options: dict[str, str] | tuple[str, ...]) -> QComboBox:
            widget = QComboBox()
            if isinstance(options, dict):
                for key, label in options.items():
                    widget.addItem(tr(label), key)  # i18n: registry
            else:
                for value in options:
                    widget.addItem(tr(value), value)  # i18n: registry
            return widget

        self._test_type = combo(st.PATH_TEST_TYPES)
        self._seepage = combo(st.SEEPAGE_CONDITIONS)
        self._loading_dir = combo(st.LOADING_DIRECTIONS)
        self._lateral = QDoubleSpinBox()
        self._lateral.setRange(-1e12, 1e12)
        self._lateral.setDecimals(4)
        self._lateral.setSuffix(f" {self._unit}")
        self._k0 = QDoubleSpinBox()
        self._k0.setRange(0.0, 100.0)
        self._k0.setDecimals(4)
        self._strain_type = combo(st.STRAIN_TYPES)
        for widget in (self._test_type, self._seepage, self._loading_dir, self._strain_type):
            widget.currentIndexChanged.connect(self._config_changed)
        form.addRow(tr("Test Type:"), self._test_type)
        form.addRow(tr("Seepage Condition:"), self._seepage)
        form.addRow(tr("Loading Direction:"), self._loading_dir)
        form.addRow(tr("Initial Effective Lateral Stress:"), self._lateral)
        form.addRow(tr("Initial Effective K0:"), self._k0)
        form.addRow(tr("Strain Type:"), self._strain_type)
        self._form = form
        layout.addLayout(form)
        self._note = QLabel()
        self._note.setWordWrap(True)
        layout.addWidget(self._note)
        self._steps = PointTable([], [1.0, 1.0, 1.0])
        layout.addWidget(self._steps, stretch=1)
        self._config_changed()

    def _config(self) -> st.StressPath:
        return st.StressPath(
            test_type=self._test_type.currentData(),
            seepage=self._seepage.currentData(),
            loading=self._loading_dir.currentData(),
            strain_type=self._strain_type.currentData(),
        )

    def _config_changed(self) -> None:
        config = self._config()
        test_type = config.test_type
        # RSData 1.009: seepage and loading direction for triaxial/biaxial;
        # sigma'h0 and K0 also for simple shear; strain type for uniaxial.
        triaxial_like = test_type in ("triaxial", "biaxial")
        visible = {
            self._seepage: triaxial_like,
            self._loading_dir: triaxial_like,
            self._lateral: triaxial_like or test_type == "simple_shear",
            self._k0: triaxial_like or test_type == "simple_shear",
            self._strain_type: test_type == "uniaxial",
        }
        for widget, shown in visible.items():
            widget.setEnabled(shown)
            self._form.setRowVisible(widget, shown)
        # stress columns in the display unit (RSData shows no units here)
        headers = [
            f"{name} ({self._unit})" if is_stress else name
            for name, is_stress in zip(config.columns(), config.stress_columns())
        ]
        scales = [self._kpa_scale if is_stress else 1.0 for is_stress in config.stress_columns()]
        self._steps.reconfigure(headers, scales)
        if config.drawable:
            note = ""
            if test_type == "uniaxial":
                note = tr("Uniaxial: the radial stress is zero (RSData 1.009 plots p and q with a hidden 100 kPa).")
        elif triaxial_like and config.loading == "Lateral":
            note = tr(
                "Loading Direction Lateral: RSData 1.009 overwrites SigmaXX with the initial lateral stress and "
                "plots no axial stress; the path is kept but not drawn (spec 021)."
            )
        else:
            note = tr("Kept but not drawn: the stress invariants of this configuration are not verified (spec 021).")
        self._note.setText(note)

    def _new_item(self, name: str, color: str):
        return st.StressPath(name=name, color=color)

    def _load(self, item: st.StressPath) -> None:
        widgets = (self._test_type, self._seepage, self._loading_dir, self._strain_type)
        for widget in widgets:
            widget.blockSignals(True)
        self._test_type.setCurrentIndex(max(0, self._test_type.findData(item.test_type)))
        self._seepage.setCurrentIndex(max(0, self._seepage.findData(item.seepage)))
        self._loading_dir.setCurrentIndex(max(0, self._loading_dir.findData(item.loading)))
        self._strain_type.setCurrentIndex(max(0, self._strain_type.findData(item.strain_type)))
        for widget in widgets:
            widget.blockSignals(False)
        self._lateral.setValue(item.lateral_stress * self._kpa_scale)
        self._k0.setValue(item.k0)
        self._config_changed()
        self._steps.set_rows(item.steps)

    def _store(self, item: st.StressPath) -> None:
        item.test_type = self._test_type.currentData()
        item.seepage = self._seepage.currentData()
        item.loading = self._loading_dir.currentData()
        item.lateral_stress = self._lateral.value() / self._kpa_scale
        item.k0 = self._k0.value()
        item.strain_type = self._strain_type.currentData()
        item.steps = [list(row) for row in self._steps.rows()]
