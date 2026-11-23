"""Digitized GSI charts, redrawn and clickable (spec 022).

The general chart (Hoek & Marinos 2000), the flysch chart (Marinos & Hoek
2000) and the heterogeneous chart (V. Marinos 2007) are redrawn with
matplotlib from ``core.gsi_charts`` data only (isolines, grid, type bands,
N/A cells, arrows); no image of the original is used. Click -> GSI; the
chart texts switch between English (literal) and Spanish.
"""

from __future__ import annotations

import html
import textwrap

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..core import gsi_charts
from .i18n import localize
from .themes import mpl_colors

SHORT_NAMES = {
    "general_2000": "Hoek & Marinos (2000)",
    "flysch_2000": "Marinos & Hoek (2000), flysch",
    "heterogeneous_marinos_2007": "V. Marinos (2007), heterogeneous",
}
# the notes window follows the chart language (its own selector), like the chart texts
SHORT_NAMES_ES = {
    "general_2000": "Hoek & Marinos (2000)",
    "flysch_2000": "Marinos & Hoek (2000), flysch",
    "heterogeneous_marinos_2007": "V. Marinos (2007), heterogénea",
}


class DigitizedGsiChart(FigureCanvasQTAgg):
    """One digitized chart in the (u, v) frame (u right, v down)."""

    def __init__(self, chart_id: str, theme: str = "light", lang: str = "en", on_pick=None, on_hover=None) -> None:
        self.figure = Figure(figsize=(7.2, 6.2))
        super().__init__(self.figure)
        self.chart_id = chart_id
        self.theme = theme
        self.lang = lang
        self.on_pick = on_pick
        self.on_hover = on_hover
        self.point: tuple[float, float] | None = None
        self.axes = self.figure.add_axes((0.075, 0.015, 0.915, 0.885))
        self._draw()
        self.mpl_connect("button_press_event", self._click)
        self.mpl_connect("motion_notify_event", self._motion)

    # ------------------------------------------------------------ drawing

    def set_language(self, lang: str) -> None:
        if lang != self.lang:
            self.lang = lang
            self._draw()

    def _draw(self) -> None:
        data = gsi_charts.chart(self.chart_id)
        t = gsi_charts.texts(self.chart_id, self.lang)
        c = mpl_colors(self.theme)
        ink, paper = c["axes"], c["figure"]
        ax = self.axes
        ax.clear()
        self.figure.set_facecolor(paper)
        ax.set_facecolor(paper)
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(1.0, 0.0)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(ink)
            spine.set_linewidth(1.0)

        # type bands: faded fringe, then core (whole or combined bands; the split is not drawn)
        for region in sorted(data.get("regions", []), key=lambda r: r["shading"] != "fringe"):
            if region.get("split_inferred"):
                continue
            alpha = 0.10 if region["shading"] == "fringe" else 0.22
            ax.add_patch(Polygon(region["polygon"], closed=True, facecolor=ink, alpha=alpha, edgecolor="none", zorder=1))
        for region in data.get("regions", []):
            if region["shading"] == "core" and region.get("label_at") and not region.get("combined"):
                u, v = region["label_at"]
                ax.text(u, v, region["label"], ha="center", va="center", fontsize=13, weight="bold", color=c["mc"], zorder=6)
        # not applicable cells
        for zone in data.get("not_applicable", []):
            blank = zone.get("kind") == "blank_no_contours"
            ax.add_patch(Polygon(zone["polygon"], closed=True, facecolor=paper, edgecolor=ink, linewidth=0.0,
                                 hatch=".." if blank else "///", alpha=0.55, zorder=2))
            us = [p[0] for p in zone["polygon"]]
            vs = [p[1] for p in zone["polygon"]]
            label = ("(sin isolíneas)" if self.lang == "es" else "(no contours)") if blank else t.get("na_label", "N/A")
            ax.text(sum(us) / len(us), sum(vs) / len(vs), label, ha="center", va="center", fontsize=9, color=ink,
                    zorder=6, bbox={"facecolor": paper, "edgecolor": "none", "pad": 1.0})
        # isolines with their value at mid-length
        for line in data["isolines"]:
            us = [p[0] for p in line["points"]]
            vs = [p[1] for p in line["points"]]
            grey = line.get("style") == "grey"
            ax.plot(us, vs, color=ink, alpha=0.5 if grey else 1.0, linewidth=0.9, zorder=3)
            ax.text((us[0] + us[-1]) / 2, (vs[0] + vs[-1]) / 2, f'{line["gsi"]:g}', fontsize=7.5, color=c["point"],
                    ha="center", va="center", zorder=7, bbox={"facecolor": paper, "edgecolor": "none", "pad": 0.3, "alpha": 0.85})
        # dashed boundary of the 'possible' zone (heterogeneous chart)
        parts = data.get("dashed_boundary_parts") or ([data["dashed_boundary"] + data["dashed_boundary"][:1]] if data.get("dashed_boundary") else [])
        for part in parts:
            ax.plot([p[0] for p in part], [p[1] for p in part], "--", color=ink, linewidth=1.8, zorder=4)
        # arrows between types (tectonic disturbance)
        for arrow in data.get("arrows", []):
            a = gsi_charts.type_center(self.chart_id, arrow["from"])
            b = gsi_charts.type_center(self.chart_id, arrow["to"])
            if a and b:
                ax.annotate("", xy=b, xytext=a, zorder=5,
                            arrowprops={"arrowstyle": "->", "color": c["envelope"], "lw": 1.2, "alpha": 0.8,
                                        "shrinkA": 11, "shrinkB": 11})
        # grid, column headings (top) and structure headings (left)
        for col in data["columns"]:
            ax.axvline(col["u0"], color=ink, linewidth=0.8, zorder=4)
            ax.text((col["u0"] + col["u1"]) / 2, -0.012, "\n".join(textwrap.wrap(t["columns"][col["key"]]["label"], 14)),
                    ha="center", va="bottom", fontsize=8, color=ink, clip_on=False)
        for row in data["rows"]:
            ax.axhline(row["v0"], color=ink, linewidth=0.8, zorder=4)
            width = max(8, int((row["v1"] - row["v0"]) * 95))  # characters that fit along the row height
            ax.text(-0.012, (row["v0"] + row["v1"]) / 2, "\n".join(textwrap.wrap(t["rows"][row["key"]]["label"], width)),
                    ha="right", va="center", fontsize=6.5, rotation=90, color=ink, clip_on=False, linespacing=1.0)
        title = "\n".join(textwrap.wrap(t["title"], 90))
        self.figure.suptitle(title, fontsize=8.5, color=ink, y=0.995, va="top")
        (self._marker,) = ax.plot([], [], marker="o", markersize=9, markerfacecolor="none", markeredgewidth=2.2,
                                  color=c["point"], linestyle="None", zorder=10)
        if self.point is not None:
            self._marker.set_data([self.point[0]], [self.point[1]])
        self.draw_idle()

    # ------------------------------------------------------------ picking

    def _click(self, event) -> None:
        if event.inaxes is not self.axes or event.xdata is None:
            return
        self.set_point(float(event.xdata), float(event.ydata))

    def _motion(self, event) -> None:
        if self.on_hover is None:
            return
        if event.inaxes is not self.axes or event.xdata is None:
            self.on_hover(None)
            return
        self.on_hover(gsi_charts.pick(self.chart_id, float(event.xdata), float(event.ydata)))

    def set_point(self, u: float, v: float) -> gsi_charts.ChartPick:
        result = gsi_charts.pick(self.chart_id, u, v)
        if result.how != "outside":
            self.point = (u, v)
            self._marker.set_data([u], [v])
            self.draw_idle()
            if self.on_pick is not None:
                self.on_pick(result)
        return result


class DigitizedGsiPage(QWidget):
    """Chart + quick pick by type + description of the picked cell."""

    def __init__(self, chart_id: str, theme: str = "light", lang: str = "en", on_change=None, parent=None) -> None:
        super().__init__(parent)
        self.chart_id = chart_id
        self.lang = lang
        self.on_change = on_change
        self.result: gsi_charts.ChartPick | None = None
        self.chart = DigitizedGsiChart(chart_id, theme, lang, on_pick=self._picked, on_hover=self._hovered)

        top = QHBoxLayout()
        self._hover = QLabel()
        self._hover.setMinimumWidth(260)
        top.addWidget(self._hover, stretch=1)
        self._type = QComboBox()
        types = gsi_charts.chart_types(chart_id)
        if types:
            self._type.addItem("", None)
            for label in types:
                self._type.addItem(label, label)
            self._type.activated.connect(self._type_chosen)
            self._type_label = QLabel()
            top.addWidget(self._type_label)
            top.addWidget(self._type)
        self._notes_button = QPushButton()
        self._notes_button.clicked.connect(self.show_notes)
        top.addWidget(self._notes_button)

        self._details = QLabel()
        self._details.setWordWrap(True)
        self._details.setTextFormat(Qt.TextFormat.RichText)
        self._details.setMinimumHeight(64)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(top)
        layout.addWidget(self.chart, stretch=1)
        layout.addWidget(self._details)
        self._retranslate()

    @property
    def value(self) -> float | None:
        return None if self.result is None or self.result.gsi is None else round(self.result.gsi, 1)

    def set_language(self, lang: str) -> None:
        self.lang = lang
        self.chart.set_language(lang)
        self._retranslate()

    def _retranslate(self) -> None:
        es = self.lang == "es"
        if hasattr(self, "_type_label"):
            self._type_label.setText("Tipo:" if es else "Type:")  # i18n: ignore (chart language)
            self._type.setItemText(0, "(clic en la carta)" if es else "(click on the chart)")
        self._notes_button.setText("Notas de la carta…" if es else "Chart notes…")  # i18n: ignore (chart language)
        self._reset_hover()
        self._show_details()

    def _type_chosen(self) -> None:
        label = self._type.currentData()
        if label is not None:
            center = gsi_charts.type_center(self.chart_id, label)
            if center is not None:
                self.chart.set_point(*center)

    def _hovered(self, result: gsi_charts.ChartPick | None) -> None:
        if result is None or result.how == "outside":
            self._reset_hover()
            return
        value = "N/A" if result.gsi is None else f"{result.gsi:.1f}"
        self._hover.setText(localize(f"GSI ≈ {value}") + f"  ·  {result.summary(self.lang)}")

    def _reset_hover(self) -> None:
        self._hover.setText("Clic en la carta para leer el GSI." if self.lang == "es" else "Click on the chart to read GSI.")  # i18n: ignore (chart language)

    def _picked(self, result: gsi_charts.ChartPick) -> None:
        self.result = result
        if hasattr(self, "_type_label"):
            self._type.setCurrentIndex(max(0, self._type.findData(result.types[0])) if result.types else 0)
        self._show_details()
        if self.on_change is not None:
            self.on_change()

    def _show_details(self) -> None:
        r = self.result
        if r is None:
            self._details.setText("")
            return
        t = gsi_charts.texts(self.chart_id, self.lang)
        es = self.lang == "es"
        lines = [f"<b>{html.escape(r.summary(self.lang))}</b>"]
        if r.column is not None:
            col = t["columns"][r.column]
            lines.append(f'<i>{html.escape(col["label"])}</i>: {html.escape(col["description"])}')
        if r.types:
            desc = t.get("type_descriptions", {}).get(r.types[0], "")
            if desc:
                lines.append(f'<i>{"Tipo" if es else "Type"} {html.escape(r.types[0])}</i>: {html.escape(desc).replace(chr(10), " ")}')
        elif r.row is not None:
            row = t["rows"][r.row]
            if row.get("description"):
                lines.append(f'<i>{html.escape(row["label"])}</i>: {html.escape(row["description"])}')
        self._details.setText("<br>".join(lines))

    # ------------------------------------------------------------ notes

    def notes_html(self) -> str:
        data = gsi_charts.chart(self.chart_id)
        t = gsi_charts.texts(self.chart_id, self.lang)
        es = self.lang == "es"
        tx = t.get("texts", {})
        out = [f'<h3>{html.escape(t["title"])}</h3>']
        if t.get("caption"):
            out.append(f'<p><i>{html.escape(t["caption"])}</i></p>')
        instructions = html.escape(tx.get("instructions", ""))
        emphasis = html.escape(tx.get("emphasis", "") or "")
        if emphasis and emphasis in instructions:
            tag = "u" if tx.get("emphasis_style") == "underline" else "b"
            instructions = instructions.replace(emphasis, f"<{tag}>{emphasis}</{tag}>")
        if instructions:
            out.append(f"<p>{instructions}</p>")
        for key in ("box_note", "side_note"):
            if tx.get(key):
                out.append(f"<p>{html.escape(tx[key])}</p>")
        if data.get("arrows") and t.get("arrow_meaning"):
            arrows = ", ".join(f'{a["from"]}→{a["to"]}' for a in data["arrows"])
            out.append(f'<p>{"Flechas" if es else "Arrows"} ({arrows}): {html.escape(t["arrow_meaning"])}</p>')
        for note in tx.get("footnotes", []) or []:
            out.append(f"<p><small>{html.escape(note)}</small></p>")
        q = data.get("quality", {})
        source = (
            f'<b>{"Fuente" if es else "Source"}:</b> {html.escape(data["citation"])}<br>'
            + (
                f'<b>Digitalización:</b> isolíneas digitalizadas de la fuente; error máximo en los puntos de control {q.get("max_abs_error_gsi", "?")} GSI. '
                "Carta redibujada a partir de los datos numéricos (no se reproduce la imagen original)."
                if es
                else f'<b>Digitization:</b> isolines digitized from the source; max. error at the control points {q.get("max_abs_error_gsi", "?")} GSI. '
                "Chart redrawn from the numeric data (the original image is not reproduced)."
            )
        )
        if self.lang == "es" and data["i18n"].get("note"):
            source += f'<br><small>{html.escape(data["i18n"]["note"])}</small>'
        out.append(f"<hr><p><small>{source}</small></p>")
        return "".join(out)

    def show_notes(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle((SHORT_NAMES_ES if self.lang == "es" else SHORT_NAMES).get(self.chart_id, self.chart_id))
        dlg.resize(720, 560)
        browser = QTextBrowser()
        browser.setHtml(self.notes_html())
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        layout = QVBoxLayout(dlg)
        layout.addWidget(browser)
        layout.addWidget(buttons)
        dlg.exec()
