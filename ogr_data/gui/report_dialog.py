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
from .i18n import current_language, decimal_point, tr, translator


class ManageReportViewsDialog(QDialog):
    """Reorder, rename and remove the views added to the report."""

    def __init__(self, views: report.ReportViews, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Manage Report View"))
        self.resize(460, 340)
        self.views = views
        self.list = QListWidget()
        self.list.itemChanged.connect(self._renamed)
        self.list.currentRowChanged.connect(self._update_buttons)
        self.up = QPushButton(tr("Up"))
        self.down = QPushButton(tr("Down"))
        self.remove = QPushButton(tr("Remove"))
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
        layout.addWidget(QLabel(tr("Views in report order (double-click to rename):")))
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
        self.setWindowTitle(tr("Report Generator"))
        self.main = main
        self.title = QLineEdit(main.report_project().title)
        self.title.setPlaceholderText(tr("Untitled Project"))  # report.UNTITLED

        box = QGroupBox(tr("Section Visibility"))
        grid = QGridLayout(box)
        self.checks: dict[str, QCheckBox] = {}
        visibility = main.report_visibility
        for i, (key, label) in enumerate(report.SECTIONS):
            check = QCheckBox(tr(label))  # i18n: registry
            check.setChecked(visibility.get(key, True))
            check.toggled.connect(self._store_visibility)
            self.checks[key] = check
            grid.addWidget(check, i % 6, i // 6)

        self.views_label = QLabel()
        manage = QPushButton(tr("Manage Report View…"))
        manage.clicked.connect(self._manage)
        views_row = QHBoxLayout()
        views_row.addWidget(self.views_label, stretch=1)
        views_row.addWidget(manage)

        self.open_after = QCheckBox(tr("Open in the browser after generating (Save / Print to PDF from there)"))
        self.open_after.setChecked(True)
        self.generate_button = QPushButton(tr("Generate…"))
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self._generate_clicked)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.addButton(self.generate_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow(tr("Report title"), self.title)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(box)
        layout.addLayout(views_row)
        note = QLabel(tr("Empty sections are left out of the report."))
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
        if n == 1:
            text = tr("{0} graph view in the report").format(n)
        elif n:
            text = tr("{0} graph views in the report").format(n)
        else:
            text = tr("No graph views yet: use Analysis > Add View To Report.")
        self.views_label.setText(text)

    def _manage(self) -> None:
        ManageReportViewsDialog(self.main.report_views, self).exec()
        self._update_views_label()

    def html(self) -> str:
        return report.build_html(
            self.main.report_project(),
            self.main.report_views,
            self.visibility(),
            self.title.text(),
            translate=translator(),
            lang=current_language(),
            decimal=decimal_point(),
        )

    def generate(self, path: str | Path, open_browser: bool = False) -> Path:
        written = report.write_report(path, self.html())
        if open_browser:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(written.resolve())))
        return written

    def _generate_clicked(self) -> None:
        title = self.title.text().strip() or tr("Untitled Project")
        suggested = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip() or "report"
        path, _ = QFileDialog.getSaveFileName(self, tr("Generate report"), f"{suggested}.html", tr("HTML report (*.html)"))
        if not path:
            return
        if not path.lower().endswith((".html", ".htm")):
            path += ".html"
        try:
            written = self.generate(path, open_browser=self.open_after.isChecked())
        except OSError as exc:
            QMessageBox.warning(self, tr("Report"), str(exc))
            return
        self.main.statusBar().showMessage(tr("Report written to {0}").format(written), 8000)
