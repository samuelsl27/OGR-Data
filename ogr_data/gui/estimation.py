"""Estimation of properties without tests (spec 022).

One-click selectors next to the GHB fields, as ORMAS (and the old RocData)
offer them; RSData hides them behind double-click buttons.

- GsiDialog: the Hoek & Marinos (2000) chart selector of spec 003; the
  digitized charts, redrawn and clickable (general 2000, flysch 2000 and
  heterogeneous V. Marinos 2007; texts in English or Spanish, see
  gsi_chart_view); the quantified chart of Hoek, Carter & Diederichs (2013,
  Fig. 5) redrawn from its equation GSI = 1.5 JCond89 + RQD/2 (click on it
  to read GSI); and the 2013 calculator (RQD direct / from lambda / from
  Jv; joint condition as JCond89, its Table 1 ratings, JCond76 or Jr/Ja).
- disturbance_picker: D guidelines (Practical Rock Engineering 2023, Fig. 9).
- modulus_ratio_picker: Ei = MR x sigci with the MR table (idem, Fig. 13).
"""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import gsi as qgsi
from ..core import tables
from .gsi_chart_view import DigitizedGsiPage
from .i18n import current_language, decimal_point, localize, tr
from .number_spin import NumberSpinBox
from .pickers import GsiPickerDialog
from .themes import mpl_colors


def _spin(lo: float, hi: float, value: float, decimals: int = 2, step: float = 1.0) -> QDoubleSpinBox:
    spin = NumberSpinBox()
    spin.setRange(lo, hi)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(value)
    return spin


# ------------------------------------------------------------------ GSI


class QuantifiedGsiChart(FigureCanvasQTAgg):
    """Hoek, Carter & Diederichs (2013) Fig. 5, redrawn: A = 1.5 JCond89 (45 -> 0), B = RQD/2."""

    def __init__(self, theme: str = "light", on_pick=None) -> None:
        self.figure = Figure(figsize=(6.4, 4.6), tight_layout=True)
        super().__init__(self.figure)
        self.on_pick = on_pick
        self.point: tuple[float, float] | None = None
        self.axes = self.figure.add_subplot(111)
        colors = mpl_colors(theme)
        self._colors = colors
        data = tables.gsi_quantified()["chart"]
        ax = self.axes
        self.figure.set_facecolor(colors["figure"])
        ax.set_facecolor(colors["figure"])
        ax.set_xlim(qgsi.CHART_A_MAX, 0.0)  # decreasing surface quality to the right
        ax.set_ylim(0.0, qgsi.CHART_B_MAX)
        ax.set_aspect("equal")  # isolines at 45 degrees, as in Fig. 5
        ax.set_xlabel("1.5 JCond89", color=colors["axes"])
        ax.set_ylabel("RQD/2", color=colors["axes"])
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.tick_params(colors=colors["axes"], labelcolor=colors["axes"])
        ax.grid(True, alpha=0.4, color=colors["grid"])
        # GSI isolines: A + B = GSI (eq. 1), every 10
        for value in range(10, 90, 10):
            xs = [max(0.0, value - qgsi.CHART_B_MAX), min(qgsi.CHART_A_MAX, float(value))]
            ys = [value - xs[0], value - xs[1]]
            ax.plot(xs, ys, color=colors["axes"], linewidth=0.9)
            # label near the upper-left end of each line
            lx = min(qgsi.CHART_A_MAX - 1.5, value - 2.0)
            ly = value - lx
            if 0.0 <= ly <= qgsi.CHART_B_MAX:
                ax.text(lx, ly, f"{value}", color=colors["axes"], fontsize=8, ha="center", va="center",
                        rotation=45, backgroundcolor=colors["figure"])
        # structure bands (Fig. 5 rows) and surface condition headings (columns)
        for row in data["rows"]:
            ax.axhline(row["y_lo"], color=colors["grid"], linewidth=1.2)
            ax.text(qgsi.CHART_A_MAX - 0.6, (row["y_lo"] + row["y_hi"]) / 2.0, row["label"], fontsize=7,
                    ha="left", va="center", color=colors["mc"], alpha=0.9)
        for column in data["columns"]:
            ax.text(column["x"], qgsi.CHART_B_MAX + 0.6, column["label"], fontsize=7, rotation=0,
                    ha="center", va="bottom", color=colors["mc"])
        (self._marker,) = ax.plot([], [], marker="o", color=colors["point"], markersize=8, linestyle="None")
        self.mpl_connect("button_press_event", self._click)

    def _click(self, event) -> None:
        if event.inaxes is not self.axes or event.xdata is None:
            return
        self.set_point(float(event.xdata), float(event.ydata))

    def set_point(self, a: float, b: float) -> float | None:
        value = qgsi.chart_gsi(a, b)
        if value is None:
            return None
        self.point = (a, b)
        self._marker.set_data([a], [b])
        self.draw_idle()
        if self.on_pick is not None:
            self.on_pick(a, b, value)
        return value


CHART_LANGUAGES = (("en", "English (original)"), ("es", "Español"))  # codes; names shown with tr() below


class GsiDialog(QDialog):
    """GSI: 2000 selector, digitized charts (2000 / flysch / heterogeneous), quantified chart and calculator (2013)."""

    def __init__(self, parent=None, theme: str = "light", lang: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Pick GSI"))
        self.resize(1000, 860)
        self.value: float | None = None
        if lang is None:  # spec 024: the charts start in the interface language
            lang = current_language()
        self._lang = lang if lang in {code for code, _ in CHART_LANGUAGES} else "en"
        self._tabs = QTabWidget()

        # 1. Hoek & Marinos (2000) selector (spec 003)
        self._chart2000 = GsiPickerDialog(self)
        self._chart2000.setWindowFlags(Qt.WindowType.Widget)  # embedded as a tab page
        for box in self._chart2000.findChildren(QDialogButtonBox):
            box.hide()
        for label in self._chart2000.findChildren(QLabel):
            label.setWordWrap(True)  # long source note
        for combo in (self._chart2000._structure, self._chart2000._surface):
            combo.currentIndexChanged.connect(self._update_result)
        self._chart2000._value.valueChanged.connect(self._update_result)
        self._tabs.addTab(self._chart2000, tr("Chart 2000 (selector)"))

        # 2. digitized charts: click -> GSI (general 2000, flysch 2000, heterogeneous 2007)
        self._digitized: dict[str, DigitizedGsiPage] = {}
        for chart_id, title in (
            ("general_2000", tr("Chart 2000 (click)")),
            ("flysch_2000", "Flysch 2000 (Marinos && Hoek)"),  # i18n: ignore (same in Spanish)
            ("heterogeneous_marinos_2007", tr("Heterogeneous (V. Marinos 2007)")),
        ):
            page = DigitizedGsiPage(chart_id, theme, self._lang, on_change=self._update_result)
            self._digitized[chart_id] = page
            self._tabs.addTab(page, title)

        # 3. quantified chart (2013)
        chart_page = QWidget()
        chart_layout = QVBoxLayout(chart_page)
        self._chart = QuantifiedGsiChart(theme, on_pick=self._chart_picked)
        self._chart_label = QLabel(tr("Click on the chart: GSI = 1.5 JCond89 + RQD/2 (Hoek, Carter & Diederichs 2013)."))
        self._chart_label.setWordWrap(True)
        chart_layout.addWidget(self._chart, stretch=1)
        chart_layout.addWidget(self._chart_label)
        self._tabs.addTab(chart_page, tr("Quantified chart 2013"))
        self._chart_page = chart_page

        # 4. calculator (2013)
        self._tabs.addTab(self._build_calculator(), tr("Calculator 2013"))
        self._tabs.currentChanged.connect(self._update_result)

        self._result = QLabel()
        source = tables.gsi_quantified()["source"]
        note = QLabel(
            tr(
                "Sources: Hoek & Marinos (2000); Marinos & Hoek (2001), flysch; V. Marinos (2007), in Marinos (2014), "
                "JRMGE 6(3), Fig. 3; {0} Digitized charts: redrawn from isolines digitized from the sources "
                "(max. error 1.3 GSI at the control points)."
            ).format(source)
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 8pt;")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._language = QComboBox()
        self._language.addItem(tr("English (original)"), "en")
        self._language.addItem("Español", "es")  # i18n: ignore (language name)
        self._language.setCurrentIndex(self._language.findData(self._lang))
        self._language.activated.connect(self._language_chosen)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(QLabel(tr("Chart text / Texto de las cartas:")))
        top.addWidget(self._language)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._tabs, stretch=1)
        layout.addWidget(self._result)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self._update_result()

    # ---------------------------------------------------------- calculator

    def _build_calculator(self) -> QWidget:
        data = tables.gsi_quantified()
        page = QWidget()
        layout = QVBoxLayout(page)

        rqd_box = QGroupBox("RQD (%)")
        rqd_form = QFormLayout(rqd_box)
        self._rqd_mode = QComboBox()
        self._rqd_mode.addItems([tr("RQD from core logging"), tr("From discontinuities per metre, lambda (eq. 4)"), tr("From volumetric joint count Jv (eq. 6, Palmstrom 2005)"), tr("From volumetric joint count Jv (eq. 5, Palmstrom 1982)")])
        self._rqd = _spin(0.0, 100.0, 30.0)
        self._lambda = _spin(0.0, 200.0, 10.0)
        self._jv = _spin(0.0, 100.0, 10.0)
        self._rqd_value = QLabel()
        rqd_form.addRow(tr("Method"), self._rqd_mode)
        rqd_form.addRow("RQD", self._rqd)
        rqd_form.addRow("lambda (1/m)", self._lambda)  # i18n: ignore (same in Spanish)
        rqd_form.addRow(tr("Jv (joints/m3)"), self._jv)
        rqd_form.addRow(tr("RQD used"), self._rqd_value)
        self._rqd_form = rqd_form
        layout.addWidget(rqd_box)

        joint_box = QGroupBox(tr("Joint condition"))
        joint_layout = QVBoxLayout(joint_box)
        self._joint_mode = QComboBox()
        self._joint_mode.addItems([tr("JCond89 (eq. 1)"), tr("JCond89 from Table 1 ratings (eq. 1)"), tr("JCond76 (eq. 2)"), tr("Jr / Ja (eq. 3)")])
        joint_layout.addWidget(self._joint_mode)
        self._joint_stack = QStackedWidget()
        # JCond89 direct, with the condition presets of Table 1
        page_j89 = QWidget()
        form = QFormLayout(page_j89)
        self._j89_preset = QComboBox()
        self._j89_preset.addItem(tr("(enter value)"), None)
        for c in data["jcond89_conditions"]:
            self._j89_preset.addItem(f'{c["rating"]}: {c["description"]}', c["rating"])
        self._j89 = _spin(0.0, 30.0, 10.0)
        self._j89_preset.currentIndexChanged.connect(lambda: self._j89.setValue(self._j89_preset.currentData()) if self._j89_preset.currentData() is not None else None)
        form.addRow(tr("Condition"), self._j89_preset)
        form.addRow("JCond89", self._j89)
        self._joint_stack.addWidget(page_j89)
        # JCond89 from the five guideline ratings
        page_ratings = QWidget()
        form = QFormLayout(page_ratings)
        self._ratings: dict[str, QComboBox] = {}
        for param in data["jcond89_parameters"]:
            combo = QComboBox()
            for label, rating in param["options"]:
                combo.addItem(f"{label}  ({rating})", rating)
            combo.currentIndexChanged.connect(self._update_result)
            self._ratings[param["key"]] = combo
            form.addRow(param["label"], combo)
        self._joint_stack.addWidget(page_ratings)
        # JCond76
        page_j76 = QWidget()
        form = QFormLayout(page_j76)
        self._j76_preset = QComboBox()
        self._j76_preset.addItem(tr("(enter value)"), None)
        for c in data["jcond76_conditions"]:
            self._j76_preset.addItem(f'{c["rating"]}: {c["description"]}', c["rating"])
        self._j76 = _spin(0.0, 25.0, 10.0)
        self._j76_preset.currentIndexChanged.connect(lambda: self._j76.setValue(self._j76_preset.currentData()) if self._j76_preset.currentData() is not None else None)
        form.addRow(tr("Condition"), self._j76_preset)
        form.addRow("JCond76", self._j76)
        self._joint_stack.addWidget(page_j76)
        # Jr / Ja
        page_q = QWidget()
        form = QFormLayout(page_q)
        self._jr = QComboBox()
        for label, value in data["jr"]:
            self._jr.addItem(f"{label}  ({value:g})", value)
        self._ja = QComboBox()
        for label, value in data["ja"]:
            self._ja.addItem(f"{value:g}: {label}", value)
        self._jr.setCurrentIndex(2)  # Smooth, undulating (2)
        self._ja.setCurrentIndex(1)  # Unaltered (1)
        form.addRow("Jr", self._jr)
        form.addRow("Ja", self._ja)
        self._joint_stack.addWidget(page_q)
        joint_layout.addWidget(self._joint_stack)
        layout.addWidget(joint_box)
        note = QLabel(data["rsdata_note"])
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 8pt;")
        layout.addWidget(note)
        layout.addStretch(1)

        self._joint_mode.currentIndexChanged.connect(self._joint_stack.setCurrentIndex)
        for widget in (self._rqd_mode, self._joint_mode, self._jr, self._ja):
            widget.currentIndexChanged.connect(self._update_result)
        for widget in (self._rqd, self._lambda, self._jv, self._j89, self._j76):
            widget.valueChanged.connect(self._update_result)
        return page

    def rqd(self) -> float:
        mode = self._rqd_mode.currentIndex()
        if mode == 1:
            return qgsi.rqd_from_lambda(self._lambda.value())
        if mode in (2, 3):
            return qgsi.rqd_from_jv(self._jv.value(), palmstrom_2005=mode == 2)
        return self._rqd.value()

    def calculator_gsi(self) -> tuple[float, str]:
        rqd = self.rqd()
        mode = self._joint_mode.currentIndex()
        if mode == 1:
            r = {k: c.currentData() for k, c in self._ratings.items()}
            j = qgsi.jcond89_from_ratings(r["persistence"], r["aperture"], r["roughness"], r["infilling"], r["weathering"])
            return qgsi.gsi_from_jcond89(j, rqd), tr("JCond89 = {0:g} (sum of ratings); GSI = 1.5 x {0:g} + {1:.2f}/2").format(j, rqd)
        if mode == 2:
            j = self._j76.value()
            return qgsi.gsi_from_jcond76(j, rqd), f"GSI = 2 x {j:g} + {rqd:.2f}/2"
        if mode == 3:
            jr, ja = self._jr.currentData(), self._ja.currentData()
            return qgsi.gsi_from_jr_ja(jr, ja, rqd), f"Jr/Ja = {jr / ja:.3f}; GSI = 52 (Jr/Ja)/(1 + Jr/Ja) + {rqd:.2f}/2"
        j = self._j89.value()
        return qgsi.gsi_from_jcond89(j, rqd), f"GSI = 1.5 x {j:g} + {rqd:.2f}/2"

    # ------------------------------------------------------------ result

    def _chart_picked(self, a: float, b: float, value: float) -> None:
        row = qgsi.chart_row(b)
        self._chart_label.setText(
            f"1.5 JCond89 = {a:.1f} (JCond89 = {a / 1.5:.1f}), RQD/2 = {b:.1f} (RQD = {2 * b:.0f} %)"
            + (f" — {row['label']}" if row else "")
        )
        self._update_result()

    def _update_result(self) -> None:
        tab = self._tabs.currentIndex()
        if hasattr(self, "_rqd_value"):
            mode = self._rqd_mode.currentIndex()
            for widget, shown in ((self._rqd, mode == 0), (self._lambda, mode == 1), (self._jv, mode in (2, 3))):
                self._rqd_form.setRowVisible(widget, shown)
            self._rqd_value.setText(localize(f"{self.rqd():.2f} %"))
        text = ""
        page = self._tabs.widget(tab)
        if page is self._chart2000:
            self.value = self._chart2000.gsi()
            text = "" if self.value is None else tr("GSI = {0:.1f} (chart 2000)").format(self.value)
        elif isinstance(page, DigitizedGsiPage):
            self.value = page.value
            if page.result is None:
                text = tr("Click on the chart.")
            elif self.value is None:
                text = tr("Not applicable here (N/A): pick another cell.")
            else:
                text = f"GSI = {self.value:.1f} — {page.result.summary(self._lang)}"
        elif page is self._chart_page:
            self.value = None if self._chart.point is None else sum(self._chart.point)
            text = tr("Click on the chart.") if self.value is None else f"GSI = {self.value:.1f}"
        else:
            self.value, formula = self.calculator_gsi()
            text = f"{formula} = {self.value:.2f}"
        self._result.setText(f"<b>{localize(text)}</b>")

    def set_language(self, lang: str) -> None:
        """Language of the digitized charts' texts: 'en' (literal) or 'es'."""

        self._lang = lang
        if self._language.currentData() != lang:
            self._language.setCurrentIndex(self._language.findData(lang))
        for page in self._digitized.values():
            page.set_language(lang)
        self._update_result()

    def _language_chosen(self) -> None:
        self.set_language(self._language.currentData())  # this dialog only (spec 024: not persisted)

    def accept(self) -> None:
        self._update_result()
        if self.value is not None:
            super().accept()


def gsi_dialog(parent=None, theme: str = "light") -> float | None:
    dlg = GsiDialog(parent, theme)
    return dlg.value if dlg.exec() == QDialog.DialogCode.Accepted else None


# -------------------------------------------------------------- tables


class FilteredTableDialog(QDialog):
    """Table with text search and combo filters; value() returns the row value.

    ``columns`` are the row keys; ``headers`` (default: the keys) the texts shown
    above them, translated by the caller (spec 024).
    """

    def __init__(self, title: str, columns: list[str], rows: list[dict], value_key: str, filters: list[str], source: str, parent=None, extra: QWidget | None = None, headers: list[str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 520)
        self._rows = rows
        self._value_key = value_key
        self._columns = columns
        headers = list(columns) if headers is None else list(headers)
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Filter…"))
        self._search.textChanged.connect(self._filter)
        self._filters: dict[str, QComboBox] = {}
        top = QHBoxLayout()
        top.addWidget(self._search, stretch=1)
        for key in filters:
            combo = QComboBox()
            name = headers[columns.index(key)] if key in columns else key
            combo.addItem(tr("All ({0})").format(name.replace("_", " ")), None)
            for value in sorted({str(r[key]) for r in rows if r.get(key)}):
                combo.addItem(value, value)
            combo.currentIndexChanged.connect(lambda _=0: self._filter(self._search.text()))
            self._filters[key] = combo
            top.addWidget(combo)
        self.table = QTableWidget(len(rows), len(columns))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept)
        for i, row in enumerate(rows):
            for j, key in enumerate(columns):
                self.table.setItem(i, j, QTableWidgetItem("" if row.get(key) is None else localize(str(row.get(key)))))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table, stretch=1)
        if extra is not None:
            layout.addWidget(extra)
        src = QLabel(tr("Source: {0}").format(source))
        src.setWordWrap(True)
        src.setStyleSheet("font-size: 8pt;")
        layout.addWidget(src)
        layout.addWidget(buttons)

    def _filter(self, text: str) -> None:
        words = text.lower().split()
        for i, row in enumerate(self._rows):
            visible = all(any(w in str(v).lower() for v in row.values()) for w in words)
            for key, combo in self._filters.items():
                if combo.currentData() is not None and str(row.get(key)) != combo.currentData():
                    visible = False
            self.table.setRowHidden(i, not visible)

    def visible_rows(self) -> int:
        return sum(not self.table.isRowHidden(i) for i in range(len(self._rows)))

    def selected(self) -> dict | None:
        row = self.table.currentRow()
        return None if row < 0 else self._rows[row]

    def value(self) -> float | None:
        row = self.selected()
        return None if row is None else float(row[self._value_key])


def mi_dialog(parent=None) -> FilteredTableDialog:
    data = tables.mi_values()
    rows = [{**v, "mi ± std": f'{v["mi"]} ± {v["std"]}' + (" (est.)" if v["estimated"] else "")} for v in data["values"]]
    return FilteredTableDialog(
        tr("Pick mi — Hoek-Brown constant for intact rock (Hoek, Table 3)"),
        ["rock", "rock_type", "class", "group", "texture", "mi ± std"], rows, "mi", ["rock_type", "texture"],
        data["source"], parent,
        headers=[tr("rock"), tr("rock_type"), tr("class"), tr("group"), tr("texture"), "mi ± std"],
    )


def mi_picker(parent=None) -> float | None:
    dlg = mi_dialog(parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None


def disturbance_dialog(parent=None) -> FilteredTableDialog:
    data = tables.disturbance_factor()
    return FilteredTableDialog(
        tr("Pick D — disturbance factor (Hoek, Practical Rock Engineering 2023, Fig. 9)"),
        ["application", "case", "d", "description"], data["values"], "d", ["application"], data["source"], parent,
        headers=[tr("application"), tr("case"), "d", tr("description")],
    )


def disturbance_picker(parent=None) -> float | None:
    dlg = disturbance_dialog(parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None


class ModulusRatioDialog(FilteredTableDialog):
    """Ei = MR x sigci: MR from the table (editable), sigci from the form (kPa)."""

    def __init__(self, sigci_kpa: float, unit: str = "kPa", parent=None) -> None:
        self._sigci_kpa = float(sigci_kpa)
        self._unit = unit
        extra = QWidget()
        form = QFormLayout(extra)
        self.mr = _spin(1.0, 5000.0, 450.0, decimals=1, step=10.0)
        self.ei_label = QLabel()
        form.addRow(tr("MR (modulus ratio)"), self.mr)
        form.addRow("Ei = MR x sigci", self.ei_label)
        data = tables.modulus_ratio()
        rows = [
            {**v, "MR range": f'{v["mr_lo"]:g}' + ("" if v["mr_hi"] is None else f'–{v["mr_hi"]:g}') + (" (est.)" if v["estimated"] else ""), "MR used": v["mr_pick"]}
            for v in data["values"]
        ]
        super().__init__(
            tr("Pick Ei — modulus ratio MR (Hoek, Practical Rock Engineering 2023, Fig. 13)"),
            ["rock", "rock_type", "class", "group", "texture", "MR range", "MR used", "note"], rows, "MR used",
            ["rock_type", "texture"], f'{data["source"]} {data["notes"]}', parent, extra,
            headers=[tr("rock"), tr("rock_type"), tr("class"), tr("group"), tr("texture"), tr("MR range"), tr("MR used"), tr("note")],
        )
        self.table.currentCellChanged.connect(self._row_changed)
        self.mr.valueChanged.connect(self._update_ei)
        self._update_ei()

    def _row_changed(self, row: int, *_args) -> None:
        if row >= 0:
            self.mr.setValue(float(self._rows[row]["mr_pick"]))

    def ei_kpa(self) -> float:
        return self.mr.value() * self._sigci_kpa

    def _update_ei(self) -> None:
        from ..core import units

        scale = units.stress_factor(self._unit) / 1000.0
        self.ei_label.setText((f"{self.ei_kpa() * scale:,.0f}" if decimal_point() == "." else f"{self.ei_kpa() * scale:.0f}") + f" {self._unit}")

    def value(self) -> float | None:  # Ei in kPa
        return self.ei_kpa()


def modulus_ratio_picker(sigci_kpa: float, unit: str = "kPa", parent=None) -> float | None:
    dlg = ModulusRatioDialog(sigci_kpa, unit, parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None


# ------------------------------------------------- spec 018: Barton-Bandis and soils


class PhiRDialog(FilteredTableDialog):
    """phi r: basic friction angle (FHWA 1989, after Barton) with the Schmidt correction (eq. 5)."""

    def __init__(self, parent=None) -> None:
        extra = QWidget()
        form = QFormLayout(extra)
        self.surface = QComboBox()
        self.surface.addItems([tr("Dry surfaces (upper value)"), tr("Wet surfaces (lower value)")])
        self.phi_b = _spin(0.0, 60.0, 30.0, decimals=1)
        self.schmidt = QComboBox()
        self.schmidt.addItems([tr("phi r = phi b (fresh joint walls)"), tr("Weathered walls: phi r = (phi b - 20) + 20 r/R (eq. 5)")])
        self.r = _spin(0.0, 100.0, 30.0, decimals=1)
        self.big_r = _spin(0.1, 100.0, 40.0, decimals=1)
        self.result = QLabel()
        form.addRow(tr("Surface condition"), self.surface)
        form.addRow("phi b (deg)", self.phi_b)
        form.addRow(tr("Residual angle"), self.schmidt)
        form.addRow(tr("r: rebound on wet weathered joint"), self.r)
        form.addRow(tr("R: rebound on dry unweathered sawn surface"), self.big_r)
        form.addRow("phi r", self.result)
        self._form = form
        data = tables.basic_friction_angle()
        rows = [{**v, "phi b (deg)": f'{v["phi_lo"]:g}' if v["phi_lo"] == v["phi_hi"] else f'{v["phi_lo"]:g}-{v["phi_hi"]:g}'} for v in data["values"]]
        super().__init__(
            tr("Pick phi r — basic friction angle (FHWA 1989, after Barton)"),
            ["rock", "phi b (deg)"], rows, "phi_hi", [], tr("{0} {1} Eq. 5: Hoek, Practical Rock Engineering 2023.").format(data["source"], data["note"]),
            parent, extra, headers=[tr("rock"), "phi b (deg)"],
        )
        self.table.currentCellChanged.connect(lambda *_: self._row_changed())
        for widget in (self.surface, self.schmidt):
            widget.currentIndexChanged.connect(lambda _=0: self._row_changed())
        for widget in (self.phi_b, self.r, self.big_r):
            widget.valueChanged.connect(lambda _=0: self._update())
        self._update()

    def _row_changed(self) -> None:
        row = self.selected()
        if row is not None:
            self.phi_b.setValue(float(row["phi_lo"] if self.surface.currentIndex() == 1 else row["phi_hi"]))
        self._update()

    def phi_r(self) -> float:
        from ..core import barton

        if self.schmidt.currentIndex() == 1:
            return barton.phi_r_from_schmidt(self.phi_b.value(), self.r.value(), self.big_r.value())
        return self.phi_b.value()

    def _update(self) -> None:
        weathered = self.schmidt.currentIndex() == 1
        self._form.setRowVisible(self.r, weathered)
        self._form.setRowVisible(self.big_r, weathered)
        self.result.setText(localize(f"{self.phi_r():.2f} deg"))

    def value(self) -> float | None:
        return self.phi_r()


class JrcDialog(QDialog):
    """JRC with the Barton and Bandis (1982) scale correction (eq. 6)."""

    def __init__(self, jrc0: float = 10.0, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Pick JRC — joint roughness coefficient"))
        form = QFormLayout()
        self.jrc0 = _spin(0.0, 20.0, jrc0, decimals=2)
        self.lab = _spin(0.001, 100.0, 0.1, decimals=3, step=0.01)
        self.length = _spin(0.001, 1000.0, 1.0, decimals=3, step=0.1)
        self.result = QLabel()
        form.addRow(tr("JRC0 at laboratory scale (visual comparison with the profiles of Barton and Choubey 1977)"), self.jrc0)
        form.addRow(tr("L0, laboratory length (m)"), self.lab)
        form.addRow(tr("Ln, in-situ block size (m)"), self.length)
        form.addRow("JRCn = JRC0 (Ln/L0)^(-0.02 JRC0)", self.result)  # i18n: ignore (formula)
        for spin in (self.jrc0, self.lab, self.length):
            spin.valueChanged.connect(lambda _=0: self._update())
        note = QLabel(
            tr(
                "Source: Hoek, Practical Rock Engineering 2023 (eq. 6, Barton and Bandis 1982). The standard roughness "
                "profiles (Barton and Choubey 1977, Figure 5 of that chapter) are a copyrighted figure and are not "
                "reproduced: compare the joint with the figure in the book."
            )
        )
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self._update()

    def value(self) -> float:
        from ..core import barton

        return barton.jrc_scaled(self.jrc0.value(), self.length.value(), self.lab.value())

    def _update(self) -> None:
        self.result.setText(localize(f"{self.value():.3f}"))


class JcsDialog(FilteredTableDialog):
    """JCS: field estimates for rocks (Hoek Table 2) and soils (FHWA Table II), scale correction (eq. 7)."""

    def __init__(self, jrc0: float = 10.0, unit: str = "kPa", parent=None) -> None:
        from ..core import units

        self._kpa_scale = units.stress_factor(unit) / 1000.0
        self._unit = unit
        extra = QWidget()
        form = QFormLayout(extra)
        self.jcs0 = _spin(0.0, 1e12, 100000.0 * self._kpa_scale, decimals=4)
        self.jcs0.setSuffix(f" {unit}")
        self.jrc0 = _spin(0.0, 20.0, jrc0, decimals=2)
        self.lab = _spin(0.001, 100.0, 0.1, decimals=3, step=0.01)
        self.length = _spin(0.001, 1000.0, 0.1, decimals=3, step=0.1)
        self.result = QLabel()
        form.addRow(tr("JCS0 (laboratory scale)"), self.jcs0)
        form.addRow("JRC0", self.jrc0)
        form.addRow("L0 (m)", self.lab)
        form.addRow(tr("Ln, in-situ block size (m)"), self.length)
        form.addRow("JCSn = JCS0 (Ln/L0)^(-0.03 JRC0)", self.result)  # i18n: ignore (formula)
        rocks = tables.rock_strength_grades()
        soils = tables.soil_field_strength()
        rows = []
        for g in rocks["grades"]:
            hi = g["ucs_hi_mpa"]
            rows.append({"material": tr("Rock"), "grade": g["grade"], "term": g["term"], "UCS (MPa)": f'{g["ucs_lo_mpa"]:g}-{hi:g}' if hi else f'>{g["ucs_lo_mpa"]:g}',
                         "description": g["field_estimate"], "pick_kpa": g["ucs_pick_mpa"] * 1000.0})
        for g in soils["grades"]:
            lo = g["ucs_lo_mpa"]
            rows.append({"material": tr("Soil"), "grade": g["grade"], "term": g["term"], "UCS (MPa)": f'{lo:g}-{g["ucs_hi_mpa"]:g}' if lo is not None else f'<{g["ucs_hi_mpa"]:g}',
                         "description": g["description"], "pick_kpa": g["ucs_pick_mpa"] * 1000.0})
        super().__init__(
            tr("Pick JCS — joint wall compressive strength"),
            ["material", "grade", "term", "UCS (MPa)", "description"], rows, "pick_kpa", ["material"],
            tr(
                "Rocks: {0} Soils: {1} Scale correction: Hoek, Practical Rock Engineering 2023, eq. 7 "
                "(Barton and Bandis 1982). Weathering can reduce the joint wall strength to as low as one quarter of the intact UCS (FHWA 1989, p. 5.18, after Barton)."
            ).format(rocks["source"], soils["source"]),
            parent, extra, headers=["material", tr("grade"), tr("term"), "UCS (MPa)", tr("description")],  # "material": same in Spanish
        )
        self.table.currentCellChanged.connect(lambda *_: self._row_changed())
        for spin in (self.jcs0, self.jrc0, self.lab, self.length):
            spin.valueChanged.connect(lambda _=0: self._update())
        self._update()

    def _row_changed(self) -> None:
        row = self.selected()
        if row is not None:
            self.jcs0.setValue(row["pick_kpa"] * self._kpa_scale)

    def value(self) -> float:  # kPa
        from ..core import barton

        return barton.jcs_scaled(self.jcs0.value() / self._kpa_scale, self.jrc0.value(), self.length.value(), self.lab.value())

    def _update(self) -> None:
        self.result.setText(localize(f"{self.value() * self._kpa_scale:.4g} {self._unit}"))


class CompactedSoilDialog(FilteredTableDialog):
    """Typical c' and phi' of compacted soils by USCS group (UFC 3-220-01N Table 8-3.1)."""

    def __init__(self, symbol: str = "", parent=None) -> None:
        extra = QWidget()
        form = QFormLayout(extra)
        self.cohesion = QComboBox()
        self.cohesion.addItems([tr("Cohesion (saturated)"), tr("Cohesion (as compacted)")])
        form.addRow(tr("Cohesion to use"), self.cohesion)
        data = tables.uscs_compacted_properties()
        rows = []
        for v in data["values"]:
            rows.append({
                **v,
                "c' compacted (kPa)": "-----" if v["cohesion_compacted_kpa"] is None else f'{v["cohesion_compacted_kpa"]:g}',
                "c' saturated (kPa)": "-----" if v["cohesion_saturated_kpa"] is None else f'{v["cohesion_saturated_kpa"]:g}',
                "phi' (deg)": v["phi_effective"] or "-----",
                "dry unit weight g/cm3 (pcf)": v["max_dry_unit_weight"],
            })
        super().__init__(
            tr("Pick c and phi — typical properties of compacted soils (UFC 3-220-01N)"),
            ["symbol", "soil_type", "c' compacted (kPa)", "c' saturated (kPa)", "phi' (deg)", "dry unit weight g/cm3 (pcf)", "note"],
            rows, "symbol", [], f'{data["source"]} {data["legend"]} {data["missing"]}', parent, extra,
            headers=[tr("symbol"), tr("soil_type"), tr("c' compacted (kPa)"), tr("c' saturated (kPa)"), "phi' (deg)", tr("dry unit weight g/cm3 (pcf)"), tr("note")],
        )
        if symbol:
            from ..core import barton

            row = barton.compacted_properties(symbol)
            if row is not None:
                self.table.setCurrentCell([r["symbol"] for r in rows].index(row["symbol"]), 0)

    def parameters(self) -> dict | None:
        from ..core import barton

        row = self.selected()
        if row is None:
            return None
        return barton.mohr_coulomb_from_symbol(row["symbol"], saturated=self.cohesion.currentIndex() == 0)

    def value(self) -> dict | None:
        return self.parameters()
