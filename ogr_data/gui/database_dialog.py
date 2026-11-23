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

HELP = (
    "Enter your search key words below. You can use wildcards * to match partial words, "
    'or include words in double quotes " to match an exact phrase.'
)


class RecordEditDialog(QDialog):
    """Edit a user record; Save validates (a record without source is not saved)."""

    def __init__(self, record: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Material record")
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
                form.addRow(f"{label}{f' ({unit[0]})' if unit and unit[0] else ''}", edit)
            return widget

        tabs.addTab(page([("rock_name", "Rock Name"), ("rock_name_prefix", "Rock Name Prefix"), ("unit_weight_mn_m3", "Unit Weight", "MN/m3"), ("fabric", "Fabric"), ("notes", "Notes")], ()), "Record")
        tabs.addTab(page(mdb.LOCATION_FIELDS, ("location",)), "Location")
        tabs.addTab(page(mdb.REFERENCE_FIELDS, ("reference",)), "Reference *")
        for block in mdb.TEST_BLOCKS:
            tabs.addTab(page(mdb.BLOCK_FIELDS[block], ("tests", block)), f"{mdb.TEST_LABELS[block]} Data")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(QLabel("* Reference title and author are required: a record without source is not saved."))
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
            QMessageBox.warning(self, "Material record", str(exc))
            return
        self.record = record
        super().accept()


class DatabaseDialog(QDialog):
    def __init__(self, database: mdb.MaterialDatabase, parent=None, on_use=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Material Database")
        self.resize(1100, 700)
        self.db = database
        self.on_use = on_use  # callback(record)
        self.results: list[dict] = []
        self.page = 0
        self.current: dict | None = None

        # search panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        title = QLabel("<h2>Search</h2>")
        help_label = QLabel(HELP)
        help_label.setWordWrap(True)
        self.query = QLineEdit()
        self.query.returnPressed.connect(self.search)
        self.origin = QComboBox()
        self.origin.addItems(["All records", "Built-in (bibliography)", "My records"])
        self.origin.currentIndexChanged.connect(self.search)
        reset = QPushButton("Reset")
        reset.clicked.connect(self.reset)
        go = QPushButton("Search")
        go.clicked.connect(self.search)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addWidget(go)
        for widget in (title, help_label, self.query, self.origin):
            left_layout.addWidget(widget)
        left_layout.addLayout(row)
        new = QPushButton("New Record…")
        new.clicked.connect(self.new_record)
        left_layout.addWidget(new)
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
        self.copy_new = QPushButton("Copy to New Record…")
        self.copy_new.clicked.connect(self.copy_to_new)
        self.edit = QPushButton("Edit this Record…")
        self.edit.clicked.connect(self.edit_record)
        self.delete = QPushButton("Delete this Record")
        self.delete.clicked.connect(lambda: self.delete_record())
        self.copy = QPushButton("Copy to Clipboard")
        self.copy.clicked.connect(self.copy_to_clipboard)
        self.use = QPushButton("Use as Material")
        self.use.clicked.connect(self.use_record)
        for b in (self.copy_new, self.edit, self.delete, self.copy, self.use):
            buttons.addWidget(b)
        right_layout.addLayout(buttons)

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
        self.results = results
        self.go_page(0)

    def go_page(self, page: int) -> None:
        pages = mdb.MaterialDatabase.page_count(self.results)
        self.page = max(0, min(page, pages - 1))
        items = mdb.MaterialDatabase.page(self.results, self.page)
        self.list.blockSignals(True)
        self.list.clear()
        for record in items:
            tests = ", ".join(mdb.available_tests(record)) or "none"
            item = QListWidgetItem(f"{mdb.title(record)}\n   Record ID {record['record_id']},  Available test data: {tests}")
            item.setData(Qt.ItemDataRole.UserRole, record["record_id"])
            self.list.addItem(item)
        self.list.blockSignals(False)
        first = self.page * mdb.PAGE_SIZE + 1 if self.results else 0
        last = self.page * mdb.PAGE_SIZE + len(items)
        q = self.query.text().strip()
        self.summary.setText(f'<b>Search Records{f" for &quot;{html.escape(q)}&quot;" if q else ""}</b> — Showing Results {first} - {last} of {len(self.results)}')
        self.page_label.setText(f"Page {self.page + 1} of {pages}")
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
        for b in (self.copy_new, self.copy, self.use):
            b.setEnabled(record is not None)
        user = record is not None and record.get("origin") == "user"
        self.edit.setEnabled(user)
        self.delete.setEnabled(user)
        if record is None:
            self.view.setHtml("<i>No record.</i>")
            return
        e = html.escape

        def rows(pairs):
            return "".join(f"<tr><td><b>{e(label)}</b></td><td>{e(str(value))}</td></tr>" for label, value in pairs if value not in (None, ""))

        head = [("Rock Name", record.get("rock_name")), ("Rock Name Prefix", record.get("rock_name_prefix")),
                ("Unit Weight (MN/m3)", record.get("unit_weight_mn_m3")), ("Fabric", record.get("fabric")),
                ("Notes", record.get("notes")), ("Record ID", record.get("record_id")),
                ("Origin", "built-in (bibliography, read-only)" if record.get("origin") == "builtin" else "my records")]
        parts = [f"<h3>{e(mdb.title(record))}</h3><table>{rows(head)}</table>"]
        loc = rows((label, record.get("location", {}).get(key)) for key, label in mdb.LOCATION_FIELDS)
        if loc:
            parts.append(f"<h4>Location Information</h4><table>{loc}</table>")
        parts.append(f"<h4>Reference Information</h4><table>{rows((label, record.get('reference', {}).get(key)) for key, label in mdb.REFERENCE_FIELDS)}</table>")
        for block in mdb.TEST_BLOCKS:
            data = record.get("tests", {}).get(block, {})
            body = rows((f"{label}{f' ({unit})' if unit else ''}", data.get(key)) for key, label, unit in mdb.BLOCK_FIELDS[block])
            if body:
                parts.append(f"<h4>{mdb.TEST_LABELS[block]} Data</h4><table>{body}</table>")
        self.view.setHtml("".join(parts))

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
            QMessageBox.warning(self, "Material Database", str(exc))
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
        if confirm and QMessageBox.question(self, "Delete record", f"Delete record {self.current['record_id']}?") != QMessageBox.StandardButton.Yes:
            return
        self.db.delete(self.current["record_id"])
        self.search()

    def copy_to_clipboard(self) -> None:
        if self.current is not None:
            QApplication.clipboard().setText(mdb.clipboard_text(self.current))

    def use_record(self) -> None:
        if self.current is None or self.on_use is None:
            return
        try:
            self.on_use(self.current)
        except ValueError as exc:
            QMessageBox.warning(self, "Use as Material", str(exc))
