"""Report Generator and Manage Report View dialogs (spec 015)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core import report


class ManageReportViewsDialog(QDialog):
    """Reorder, rename and remove the views added to the report."""

    def __init__(self, views: report.ReportViews, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage Report View")
        self.resize(460, 340)
        self.views = views
        self.list = QListWidget()
        self.list.itemChanged.connect(self._renamed)
        self.list.currentRowChanged.connect(self._update_buttons)
        self.up = QPushButton("Up")
        self.down = QPushButton("Down")
        self.remove = QPushButton("Remove")
        self.up.clicked.connect(lambda: self.move(-1))
        self.down.clicked.connect(lambda: self.move(1))
        self.remove.clicked.connect(self.remove_current)
        buttons = QVBoxLayout()
        for b in (self.up, self.down, self.remove):
            buttons.addWidget(b)
        buttons.addStretch(1)
        row = QHBoxLayout()
        row.addWidget(self.list, stretch=1)
        row.addLayout(buttons)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Views in report order (double-click to rename):"))
        layout.addLayout(row)
        layout.addWidget(close)
        self.populate(0)

    def populate(self, select: int = -1) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for title in self.views.titles():
            item = QListWidgetItem(title)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list.addItem(item)
        self.list.blockSignals(False)
        if 0 <= select < self.list.count():
            self.list.setCurrentRow(select)
        self._update_buttons()

    def _update_buttons(self, *_args) -> None:
        row = self.list.currentRow()
        has = 0 <= row < len(self.views)
        self.up.setEnabled(has and row > 0)
        self.down.setEnabled(has and row < len(self.views) - 1)
        self.remove.setEnabled(has)

    def move(self, delta: int) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        self.populate(self.views.move(row, delta))

    def remove_current(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        self.populate(self.views.remove(row))

    def _renamed(self, item: QListWidgetItem) -> None:
        row = self.list.row(item)
        try:
            title = self.views.rename(row, item.text())
        except ValueError:
            title = self.views[row].title
        self.list.blockSignals(True)
        item.setText(title)
        self.list.blockSignals(False)


class ReportGeneratorDialog(QDialog):
    """Section visibility, title and Generate (self-contained HTML)."""

    def __init__(self, main) -> None:
        super().__init__(main)
        self.setWindowTitle("Report Generator")
        self.main = main
        self.title = QLineEdit(main.report_project().title)
        self.title.setPlaceholderText(report.UNTITLED)

        box = QGroupBox("Section Visibility")
        grid = QGridLayout(box)
        self.checks: dict[str, QCheckBox] = {}
        visibility = main.report_visibility
        for i, (key, label) in enumerate(report.SECTIONS):
            check = QCheckBox(label)
            check.setChecked(visibility.get(key, True))
            check.toggled.connect(self._store_visibility)
            self.checks[key] = check
            grid.addWidget(check, i % 6, i // 6)

        self.views_label = QLabel()
        manage = QPushButton("Manage Report View…")
        manage.clicked.connect(self._manage)
        views_row = QHBoxLayout()
        views_row.addWidget(self.views_label, stretch=1)
        views_row.addWidget(manage)

        self.open_after = QCheckBox("Open in the browser after generating (Save / Print to PDF from there)")
        self.open_after.setChecked(True)
        self.generate_button = QPushButton("Generate…")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self._generate_clicked)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.addButton(self.generate_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("Report title", self.title)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(box)
        layout.addLayout(views_row)
        note = QLabel("Empty sections are left out of the report.")
        note.setEnabled(False)
        layout.addWidget(note)
        layout.addWidget(self.open_after)
        layout.addWidget(buttons)
        self._update_views_label()

    def visibility(self) -> dict[str, bool]:
        return {key: check.isChecked() for key, check in self.checks.items()}

    def _store_visibility(self) -> None:
        self.main.report_visibility = self.visibility()

    def _update_views_label(self) -> None:
        n = len(self.main.report_views)
        self.views_label.setText(
            f"{n} graph view{'s' if n != 1 else ''} in the report"
            if n
            else "No graph views yet: use Analysis > Add View To Report."
        )

    def _manage(self) -> None:
        ManageReportViewsDialog(self.main.report_views, self).exec()
        self._update_views_label()

    def html(self) -> str:
        return report.build_html(
            self.main.report_project(),
            self.main.report_views,
            self.visibility(),
            self.title.text(),
        )

    def generate(self, path: str | Path, open_browser: bool = False) -> Path:
        written = report.write_report(path, self.html())
        if open_browser:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(written.resolve())))
        return written

    def _generate_clicked(self) -> None:
        title = self.title.text().strip() or report.UNTITLED
        suggested = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip() or "report"
        path, _ = QFileDialog.getSaveFileName(self, "Generate report", f"{suggested}.html", "HTML report (*.html)")
        if not path:
            return
        if not path.lower().endswith((".html", ".htm")):
            path += ".html"
        try:
            written = self.generate(path, open_browser=self.open_after.isChecked())
        except OSError as exc:
            QMessageBox.warning(self, "Report", str(exc))
            return
        self.main.statusBar().showMessage(f"Report written to {written}", 8000)
