"""Material Database dialog (spec 010), modelled on RocProp (captures 36-37).

Search panel (key words, * wildcards, "exact phrases") · paged results
("Showing Results a - b of n") · record view · New / Copy to New / Edit /
Delete (user records only) · Copy to Clipboard · Use as Material.
"""

from __future__ import annotations

import copy
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..core import database as mdb
from .i18n import localize, tr


def _help() -> str:
    return tr(
        "Enter your search key words below. You can use wildcards * to match partial words, "
        'or include words in double quotes " to match an exact phrase.'
    )


def _field_label(label: str) -> str:
    """A field label of core.database on screen (interface); record values are data."""

    labels = {
        # record
        "Rock Name": tr("Rock Name"),
        "Rock Name Prefix": tr("Rock Name Prefix"),
        "Unit Weight (MN/m3)": tr("Unit Weight (MN/m3)"),
        "Density (Mg/m3)": tr("Density (Mg/m3)"),
        "Porosity (%)": tr("Porosity (%)"),
        "Fabric": tr("Fabric"),
        "Notes": tr("Notes"),
        # location
        "Region": tr("Region"),
        "Country": tr("Country"),
        "Town/City/State": tr("Town/City/State"),
        "Latitude": tr("Latitude"),
        "Longitude": tr("Longitude"),
        "Depth (m)": tr("Depth (m)"),
        # reference
        "Reference Type": tr("Reference Type"),
        "Title": tr("Title"),
        "Author": tr("Author"),
        "Publisher": tr("Publisher"),
        "Year Published": tr("Year Published"),
        "Pages": tr("Pages"),
        "Volume": tr("Volume"),
        "Edition": tr("Edition"),
        "Table / figure": tr("Table / figure"),
        # test blocks
        "Test Type": tr("Test Type"),
        "Core Diameter": tr("Core Diameter"),
        "Core Length": tr("Core Length"),
        "Confining Stress": tr("Confining Stress"),
        "Angle to Fabric Normal": tr("Angle to Fabric Normal"),
        "Compressive Strength": tr("Compressive Strength"),
        "Compressive Strength range": tr("Compressive Strength range"),
        "Young's Modulus, Tangent at 50%": tr("Young's Modulus, Tangent at 50%"),
        "Young's Modulus": tr("Young's Modulus"),
        "Poisson Ratio": tr("Poisson Ratio"),
        "Number of specimens": tr("Number of specimens"),
        "Information Quality (1-10)": tr("Information Quality (1-10)"),
        "Tensile Strength": tr("Tensile Strength"),
        "s (intact)": tr("s (intact)"),
        "r² (intact fit)": tr("r² (intact fit)"),
        "r² (residual fit)": tr("r² (residual fit)"),
        "Confining stress range of the fit": tr("Confining stress range of the fit"),
        "Modulus ratio MR (Ei/sigci)": tr("Modulus ratio MR (Ei/sigci)"),
        "P-wave velocity": tr("P-wave velocity"),
        "P-wave velocity (dry)": tr("P-wave velocity (dry)"),
        "S-wave velocity": tr("S-wave velocity"),
        # test block names (core.database.TEST_LABELS)
        "Compression": tr("Compression"),
        "Tensile": tr("Tensile"),
        "Velocity": tr("Velocity"),
    }
    return labels.get(label, label)  # symbols (sigci, mi, m residual...) stay


def _block_title(block: str) -> str:
    """Tab / heading of a test block: "Compression Data"..."""

    titles = {
        "compression": tr("Compression Data"),
        "tensile": tr("Tensile Data"),
        "hoek_brown": tr("Hoek-Brown Data"),
        "velocity": tr("Velocity Data"),
    }
    return titles.get(block, f"{mdb.TEST_LABELS[block]} Data")


class RecordEditDialog(QDialog):
    """Edit a user record; Save validates (a record without source is not saved)."""

    def __init__(self, record: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Material record"))
        self.resize(640, 640)
        self.record = copy.deepcopy(record)
        self._edits: dict[tuple, QLineEdit] = {}
        tabs = QTabWidget()

        def page(rows, path) -> QWidget:
            widget = QWidget()
            form = QFormLayout(widget)
            for key, label, *unit in rows:
                edit = QLineEdit()
                value = self._get(path + (key,))
                edit.setText("" if value in (None, "") else str(value))
                self._edits[path + (key,)] = edit
                form.addRow(f"{_field_label(label)}{f' ({unit[0]})' if unit and unit[0] else ''}", edit)
            return widget

        tabs.addTab(page(mdb.RECORD_FIELDS, ()), tr("Record"))
        tabs.addTab(page(mdb.LOCATION_FIELDS, ("location",)), tr("Location"))
        tabs.addTab(page(mdb.REFERENCE_FIELDS, ("reference",)), tr("Reference *"))
        for block in mdb.TEST_BLOCKS:
            tabs.addTab(page(mdb.BLOCK_FIELDS[block], ("tests", block)), _block_title(block))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(QLabel(tr("* Reference title and author are required: a record without source is not saved.")))
        layout.addWidget(buttons)

    def _get(self, path: tuple):
        node = self.record
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    @staticmethod
    def _value(text: str):
        text = text.strip()
        if not text:
            return ""
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return text

    def collect(self) -> dict:
        record = copy.deepcopy(self.record)
        for path, edit in self._edits.items():
            node = record
            for key in path[:-1]:
                node = node.setdefault(key, {})
            value = self._value(edit.text())
            # text fields stay text even if they look numeric (pages, ISBN, year ranges)
            if path[-1] in ("rock_name", "rock_name_prefix", "fabric", "notes", "title", "author", "publisher", "pages", "isbn",
                            "edition", "type", "location_in_source", "region", "country", "place", "test_type",
                            "confining_stress_mpa", "ucs_range_mpa", "modulus_ratio"):
                value = edit.text().strip()
            node[path[-1]] = value
        record["tests"] = {k: v for k, v in record.get("tests", {}).items() if any(x not in (None, "") for x in v.values())}
        return record

    def accept(self) -> None:
        record = self.collect()
        try:
            mdb.validate(record)
        except ValueError as exc:
            QMessageBox.warning(self, tr("Material record"), str(exc))
            return
        self.record = record
        super().accept()


class DatabaseDialog(QDialog):
    def __init__(self, database: mdb.MaterialDatabase, parent=None, on_use=None, on_use_state=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Material Database"))
        self.resize(1100, 700)
        self.db = database
        self.on_use = on_use  # callback(record): new material
        self.on_use_state = on_use_state  # callback(record): failure state from the specimens
        self.results: list[dict] = []
        self.page = 0
        self.current: dict | None = None

        # search panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        title = QLabel("<h2>{0}</h2>".format(tr("Search")))
        help_label = QLabel(_help())
        help_label.setWordWrap(True)
        self.query = QLineEdit()
        self.query.returnPressed.connect(self.search)
        self.origin = QComboBox()
        # by index (search): All / Built-in / My records / Favourites
        self.origin.addItems([tr("All records"), tr("Built-in (bibliography)"), tr("My records"), tr("Favourites")])
        self.origin.currentIndexChanged.connect(self.search)
        reset = QPushButton(tr("Reset"))
        reset.clicked.connect(self.reset)
        go = QPushButton(tr("Search"))
        go.clicked.connect(self.search)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addWidget(go)
        for widget in (title, help_label, self.query, self.origin):
            left_layout.addWidget(widget)
        left_layout.addLayout(row)
        new = QPushButton(tr("New Record…"))
        new.clicked.connect(self.new_record)
        left_layout.addWidget(new)
        export = QPushButton(tr("Export Results to Excel (CSV)…"))
        export.clicked.connect(lambda: self.export_results())
        left_layout.addWidget(export)
        left_layout.addStretch(1)

        # results
        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        self.summary = QLabel()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._row_changed)
        pager = QHBoxLayout()
        self.prev = QPushButton("<")
        self.prev.clicked.connect(lambda: self.go_page(self.page - 1))
        self.next = QPushButton(">")
        self.next.clicked.connect(lambda: self.go_page(self.page + 1))
        self.page_label = QLabel()
        pager.addWidget(self.prev)
        pager.addWidget(self.page_label, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        pager.addWidget(self.next)
        middle_layout.addWidget(self.summary)
        middle_layout.addWidget(self.list, stretch=1)
        middle_layout.addLayout(pager)

        # record view
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.view = QTextBrowser()
        right_layout.addWidget(self.view, stretch=1)
        buttons = QHBoxLayout()
        self.copy_new = QPushButton(tr("Copy to New Record…"))
        self.copy_new.clicked.connect(self.copy_to_new)
        self.edit = QPushButton(tr("Edit this Record…"))
        self.edit.clicked.connect(self.edit_record)
        self.delete = QPushButton(tr("Delete this Record"))
        self.delete.clicked.connect(lambda: self.delete_record())
        self.copy = QPushButton(tr("Copy to Clipboard"))
        self.copy.clicked.connect(self.copy_to_clipboard)
        self.use = QPushButton(tr("Use as Material"))
        self.use.clicked.connect(self.use_record)
        self.use_state = QPushButton(tr("Use as Failure State"))
        self.use_state.clicked.connect(self.use_record_state)
        self.favourite = QPushButton(tr("☆ Favourite"))
        self.favourite.clicked.connect(self.toggle_favourite)
        self.print_button = QPushButton(tr("Print / PDF…"))
        self.print_button.clicked.connect(lambda: self.print_record())
        for b in (self.favourite, self.copy_new, self.edit, self.delete):
            buttons.addWidget(b)
        right_layout.addLayout(buttons)
        buttons2 = QHBoxLayout()
        for b in (self.copy, self.print_button, self.use_state, self.use):
            buttons2.addWidget(b)
        right_layout.addLayout(buttons2)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        for w in (left, middle, right):
            splitter.addWidget(w)
        splitter.setSizes([230, 400, 470])
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(close)
        self.search()

    # -------------------------------------------------------------- search

    def reset(self) -> None:
        self.query.clear()
        self.origin.setCurrentIndex(0)
        self.search()

    def search(self) -> None:
        results = self.db.search(self.query.text())
        origin = {1: "builtin", 2: "user"}.get(self.origin.currentIndex())
        if origin:
            results = [r for r in results if r.get("origin") == origin]
        if self.origin.currentIndex() == 3:
            results = [r for r in results if r.get("record_id") in self.db.favourites]
        self.results = results
        self.go_page(0)

    def go_page(self, page: int) -> None:
        pages = mdb.MaterialDatabase.page_count(self.results)
        self.page = max(0, min(page, pages - 1))
        items = mdb.MaterialDatabase.page(self.results, self.page)
        self.list.blockSignals(True)
        self.list.clear()
        for record in items:
            tests = ", ".join(_field_label(t) for t in mdb.available_tests(record)) or tr("none")
            star = "★ " if record["record_id"] in self.db.favourites else ""
            details = tr("Record ID {0},  Available test data: {1}").format(record["record_id"], tests)
            item = QListWidgetItem(f"{star}{mdb.title(record)}\n   {details}")
            item.setData(Qt.ItemDataRole.UserRole, record["record_id"])
            self.list.addItem(item)
        self.list.blockSignals(False)
        first = self.page * mdb.PAGE_SIZE + 1 if self.results else 0
        last = self.page * mdb.PAGE_SIZE + len(items)
        q = self.query.text().strip()
        shown = html.escape(q if q.startswith('"') else f'"{q}"')
        heading = tr("Search Records for {0}").format(shown) if q else tr("Search Records")
        showing = tr("Showing Results {0} - {1} of {2}").format(first, last, len(self.results))
        self.summary.setText(f"<b>{heading}</b> — {showing}")
        self.page_label.setText(tr("Page {0} of {1}").format(self.page + 1, pages))
        self.prev.setEnabled(self.page > 0)
        self.next.setEnabled(self.page < pages - 1)
        if items:
            self.list.setCurrentRow(0)
        else:
            self.show_record(None)

    def _row_changed(self, row: int) -> None:
        item = self.list.item(row) if row >= 0 else None
        self.show_record(self.db.get(item.data(Qt.ItemDataRole.UserRole)) if item else None)

    # -------------------------------------------------------------- record

    def show_record(self, record: dict | None) -> None:
        self.current = record
        for b in (self.copy_new, self.copy, self.use, self.favourite, self.print_button):
            b.setEnabled(record is not None)
        self.use_state.setEnabled(record is not None and bool(mdb.specimen_points(record)))
        favourite = record is not None and record["record_id"] in self.db.favourites
        self.favourite.setText(tr("★ Favourite") if favourite else tr("☆ Favourite"))
        user = record is not None and record.get("origin") == "user"
        self.edit.setEnabled(user)
        self.delete.setEnabled(user)
        if record is None:
            self.html = "<i>{0}</i>".format(tr("No record."))
            self.view.setHtml(self.html)
            return
        e = html.escape

        def rows(pairs):
            return "".join(f"<tr><td><b>{e(label)}</b></td><td>{e(str(value))}</td></tr>" for label, value in pairs if value not in (None, ""))

        origin = tr("built-in (bibliography, read-only)") if record.get("origin") == "builtin" else tr("my records")
        head = [(_field_label(label), record.get(key)) for key, label in mdb.RECORD_FIELDS] + [
            (tr("Record ID"), record.get("record_id")), (tr("Origin"), origin)]
        parts = [f"<h3>{e(mdb.title(record))}</h3><table>{rows(head)}</table>"]
        loc = rows((_field_label(label), record.get("location", {}).get(key)) for key, label in mdb.LOCATION_FIELDS)
        if loc:
            parts.append(f"<h4>{tr('Location Information')}</h4><table>{loc}</table>")
        ref = rows((_field_label(label), record.get("reference", {}).get(key)) for key, label in mdb.REFERENCE_FIELDS)
        parts.append(f"<h4>{tr('Reference Information')}</h4><table>{ref}</table>")
        for block in mdb.TEST_BLOCKS:
            data = record.get("tests", {}).get(block, {})
            body = rows((f"{_field_label(label)}{f' ({unit})' if unit else ''}", data.get(key)) for key, label, unit in mdb.BLOCK_FIELDS[block])
            if body:
                parts.append(f"<h4>{_block_title(block)}</h4><table>{body}</table>")
        specimens = record.get("specimens") or []
        if specimens:
            keys = [k for k in specimens[0].keys()]
            header = "".join(f"<th>{e(k)}</th>" for k in keys)
            body = "".join("<tr>" + "".join(f"<td>{e(str(sp.get(k, '')))}</td>" for k in keys) + "</tr>" for sp in specimens)
            parts.append(f"<h4>{tr('Specimens ({0})').format(len(specimens))}</h4><table border='1' cellspacing='0' cellpadding='2'><tr>{header}</tr>{body}</table>")
        self.html = localize("".join(parts))
        self.view.setHtml(self.html)

    def _select(self, record_id: int) -> None:
        self.search()
        for page in range(mdb.MaterialDatabase.page_count(self.results)):
            ids = [r["record_id"] for r in mdb.MaterialDatabase.page(self.results, page)]
            if record_id in ids:
                self.go_page(page)
                self.list.setCurrentRow(ids.index(record_id))
                return

    def _edit_and_save(self, record: dict) -> dict | None:
        dialog = RecordEditDialog(record, self)
        if not dialog.exec():
            return None
        return self.save(dialog.record)

    def save(self, record: dict) -> dict | None:
        try:
            stored = self.db.save_record(record)
        except ValueError as exc:
            QMessageBox.warning(self, tr("Material Database"), str(exc))
            return None
        self._select(stored["record_id"])
        return stored

    def new_record(self) -> None:
        self._edit_and_save(mdb.empty_record())

    def copy_to_new(self) -> None:
        if self.current is None:
            return
        record = copy.deepcopy(self.current)
        record["record_id"] = None
        record["origin"] = "user"
        self._edit_and_save(record)

    def edit_record(self) -> None:
        if self.current is not None and self.current.get("origin") == "user":
            self._edit_and_save(self.current)

    def delete_record(self, confirm: bool = True) -> None:
        if self.current is None or self.current.get("origin") != "user":
            return
        question = tr("Delete record {0}?").format(self.current["record_id"])
        if confirm and QMessageBox.question(self, tr("Delete record"), question) != QMessageBox.StandardButton.Yes:
            return
        self.db.delete(self.current["record_id"])
        self.search()

    def copy_to_clipboard(self) -> None:
        if self.current is not None:
            QApplication.clipboard().setText(mdb.clipboard_text(self.current))

    def toggle_favourite(self) -> None:
        if self.current is None:
            return
        record_id = self.current["record_id"]
        self.db.toggle_favourite(record_id)
        row = self.list.currentRow()
        self.go_page(self.page)
        if self.origin.currentIndex() != 3 and 0 <= row < self.list.count():
            self.list.setCurrentRow(row)

    def export_results(self, path: str | None = None) -> int:
        if path is None:
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getSaveFileName(self, tr("Export results to Excel (CSV)"), "materials.csv", "CSV (*.csv)")  # i18n: ignore
            if not path:
                return 0
        return mdb.export_csv(path, self.results)

    def print_record(self, pdf_path: str | None = None) -> None:
        """Print the record view, or write it to PDF when a path is given."""

        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter

        if self.current is None:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        if pdf_path is not None:
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(pdf_path)
        elif QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return
        document = QTextDocument()
        document.setHtml(self.html)
        document.print_(printer)

    def use_record_state(self) -> None:
        if self.current is None or self.on_use_state is None:
            return
        try:
            self.on_use_state(self.current)
        except ValueError as exc:
            QMessageBox.warning(self, tr("Use as Failure State"), str(exc))

    def use_record(self) -> None:
        if self.current is None or self.on_use is None:
            return
        try:
            self.on_use(self.current)
        except ValueError as exc:
            QMessageBox.warning(self, tr("Use as Material"), str(exc))
