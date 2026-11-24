"""matplotlib canvases for the strength envelopes."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
import numpy as np

from ..core.graph_options import PlotOptions
from ..core.numbers import symbols
from .i18n import localize, tr
from .themes import mpl_colors

_EMPTY_OFFSETS = np.empty((0, 2))


class EnvelopeCanvas(FigureCanvasQTAgg):
    """Single-axes canvas; call redraw(sig3, sig1, normal, shear, mc).

    space is "principal" (x is sigma3) or "shear" (x is normal stress);
    the sampler handler receives (space, kind, x_data) on mouse events and
    the menu handler receives (canvas, kind) from the context menu.
    """

    def __init__(self, title: str, xlabel: str, ylabel: str, theme: str = "light", space: str = "principal") -> None:
        self._theme = theme
        self.space = space
        self._default_title = title
        self.options = PlotOptions()
        self.sampler_handler = None  # set by MainWindow: fn(space, kind, x)
        self.menu_handler = None  # set by MainWindow: fn(canvas, kind)
        # spec 011: the selected material's color ("" = theme envelope),
        # its visibility and the curves of the other visible materials
        self.material_color = ""
        self.primary_label = ""
        self._primary_visible = True
        self._others: list = []  # Line2D of the other materials
        self._layers: list = []  # spec 012: test points, Mohr circles, stress paths
        # spec 017: data stay in internal MPa; ticks show the display unit
        self.display_scale = 1.0
        self.figure = Figure(figsize=(4.0, 4.0), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(symbols(xlabel))
        self.axes.set_ylabel(symbols(ylabel))
        (self._line,) = self.axes.plot([], [], linewidth=1.8)
        (self._mc_line,) = self.axes.plot([], [], linewidth=1.2, linestyle="--")
        (self._tangent_line,) = self.axes.plot([], [], linewidth=1.3, linestyle="-.")
        self._marker = self.axes.scatter([], [], s=28, zorder=5)
        self._vline = self.axes.axvline(0.0, linestyle=":", linewidth=1.0, visible=False)
        (self._mogi_line,) = self.axes.plot([], [], linewidth=1.2)
        self.axes.margins(x=0.05, y=0.05)
        self.mpl_connect("button_press_event", self._on_press)
        self.mpl_connect("motion_notify_event", self._on_motion)
        self.mpl_connect("button_release_event", self._on_release)
        self.apply_theme(theme)

    # -------------------------------------------------------------- events

    def _dispatch(self, kind: str, event) -> None:
        if self.sampler_handler is not None and event.inaxes is self.axes and event.xdata is not None:
            self.sampler_handler(self.space, kind, float(event.xdata))

    def _on_press(self, event) -> None:
        self._dispatch("press", event)

    def _on_motion(self, event) -> None:
        self._dispatch("move", event)

    def _on_release(self, event) -> None:
        self._dispatch("release", event)

    def contextMenuEvent(self, event) -> None:
        if self.menu_handler is None:
            return
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        menu.addAction(tr("Copy Graph as Image"), lambda: self.menu_handler(self, "copy"))
        menu.addAction(tr("Save Graph as Image…"), lambda: self.menu_handler(self, "save"))
        export = menu.addAction(tr("Export Graph to Excel (CSV)…"), lambda: self.menu_handler(self, "export"))
        export.setEnabled(self.can_export())  # spec 025d RF-5: disabled with its reason
        export.setToolTip(self.export_reason())
        menu.addSeparator()
        menu.addAction(tr("Zoom Extents"), lambda: self.menu_handler(self, "zoom"))
        menu.addAction(tr("Graph Editor…"), lambda: self.menu_handler(self, "editor"))
        menu.exec(event.globalPos())

    # --------------------------------------------------------------- theme

    def _series_artists(self):
        return {
            "envelope": self._line,
            "mc": self._mc_line,
            "tangent": self._tangent_line,
            "mogi": self._mogi_line,
        }

    def apply_theme(self, theme: str) -> None:
        """Recolor figure, axes, grid and series with the theme palette.

        Series with a user-chosen color in the options keep it; theme
        switches only reset series that follow the theme default.
        """

        self._theme = theme
        colors = mpl_colors(theme)
        self.figure.set_facecolor(colors["figure"])
        self.axes.set_facecolor(colors["figure"])
        for label in (self.axes.title, self.axes.xaxis.label, self.axes.yaxis.label):
            label.set_color(colors["axes"])
        self.axes.tick_params(colors=colors["axes"], labelcolor=colors["axes"])
        for spine in self.axes.spines.values():
            spine.set_color(colors["axes"])
        self._marker.set_facecolor(colors["point"])
        self._marker.set_edgecolor(colors["figure"])
        self._vline.set_color(colors["point"])
        self._apply_style()
        self.draw_idle()

    # -------------------------------------------------------------- options

    def apply_options(self, options: PlotOptions) -> None:
        """Store and apply display options (spec 016); reflects live."""

        self.options = options
        self._apply_style()
        self.draw_idle()

    def _apply_style(self) -> None:
        options = self.options
        self.axes.set_title(options.title or self._default_title)
        colors = mpl_colors(self._theme)
        if options.grid:
            self.axes.grid(True, alpha=0.6, color=colors["grid"])
        else:
            self.axes.grid(False)
        self.axes.set_aspect("equal" if options.square_axis else "auto")
        if options.x_range:
            self.axes.set_xlim(*options.x_range)
        if options.y_range:
            self.axes.set_ylim(*options.y_range)
        pad = -16 if options.labels_inside else 4
        direction = "in" if options.labels_inside else "out"
        self.axes.tick_params(axis="both", pad=pad, direction=direction, colors=colors["axes"], labelcolor=colors["axes"])
        default_colors = {
            "envelope": colors["envelope"],
            "mc": colors["mc"],
            "tangent": colors["point"],
            "mogi": colors["mogi"],
        }
        if self.material_color:
            default_colors["envelope"] = self.material_color
        for key, artist in self._series_artists().items():
            style = self.options.styles[key]
            artist.set_visible(style.visible and self._primary_visible)
            artist.set_color(style.color or default_colors[key])
            artist.set_linewidth(self.options.linewidth(key))
            artist.set_linestyle(self.options.linestyle(key))
        for line in self._others:
            line.set_color(getattr(line, "ogr_color", "") or colors["envelope"])
            line.set_linewidth(self.options.linewidth("envelope"))
        self._update_legend()

    def zoom_extents(self) -> None:
        """Scale back to the natural envelope limits (RocData)."""

        self.options.x_range = None
        self.options.y_range = None
        self.axes.set_autoscale_on(True)
        self.axes.relim(visible_only=True)
        self.axes.autoscale_view()
        self.draw_idle()

    # ----------------------------------------------------------- materials

    def set_primary(self, color: str, visible: bool = True, label: str = "") -> None:
        """Color, visibility and legend label of the selected material (spec 011)."""

        self.material_color = color
        self._primary_visible = visible
        self.primary_label = label
        self._apply_style()

    def set_others(self, curves) -> None:
        """Draw the other visible materials: iterable of (label, x, y, color)."""

        for line in self._others:
            line.remove()
        self._others = []
        for label, x, y, color in curves:
            # below the selected material (default line zorder is 2)
            (line,) = self.axes.plot(x, y, linestyle="-", zorder=1.8)
            line.ogr_label = label
            line.ogr_color = color
            self._others.append(line)
        self._apply_style()
        self._rescale()

    def set_layers(self, layers) -> None:
        """Draw data layers (spec 012) above the envelopes.

        Each layer is a dict: x, y (MPa), color, and optionally marker,
        linestyle ("None" for points), linewidth, filled (marker face),
        alpha, legend (legend label) and export ((x, y) CSV column names).
        """

        for line in self._layers:
            line.remove()
        self._layers = []
        for layer in layers:
            color = layer["color"]
            (line,) = self.axes.plot(
                layer["x"],
                layer["y"],
                color=color,
                marker=layer.get("marker") or "None",
                linestyle=layer.get("linestyle", "None"),
                linewidth=layer.get("linewidth", 1.0),
                markersize=layer.get("markersize", 6.0),
                markerfacecolor=color if layer.get("filled", True) else "none",
                markeredgecolor=color,
                alpha=layer.get("alpha", 1.0),
                zorder=3,
            )
            line.ogr_legend = layer.get("legend", "")
            line.ogr_export = layer.get("export")
            self._layers.append(line)
        self._update_legend()
        self._rescale()

    def layer_series(self) -> list[tuple[str, str, np.ndarray, np.ndarray]]:
        """(x column, y column, x, y) of the exportable data layers (spec 012)."""

        out = []
        for line in self._layers:
            if line.ogr_export:
                x, y = line.get_data()
                x_name, y_name = line.ogr_export
                out.append((x_name, y_name, np.asarray(x, dtype=float), np.asarray(y, dtype=float)))
        return out

    def _update_legend(self) -> None:
        """Legend of material names when more than one material is drawn."""

        legend = self.axes.get_legend()
        if legend is not None:
            legend.remove()
        handles = []
        if self._primary_visible and self.options.styles["envelope"].visible and len(self._line.get_xdata()):
            handles.append((self._line, self.primary_label or "Material"))
        handles += [(line, line.ogr_label) for line in self._others]
        handles += [(line, line.ogr_legend) for line in getattr(self, "_layers", []) if line.ogr_legend]
        if len(handles) < 2:
            return
        colors = mpl_colors(self._theme)
        legend = self.axes.legend([h for h, _ in handles], [t for _, t in handles], fontsize="small")
        legend.get_frame().set_facecolor(colors["figure"])
        legend.get_frame().set_edgecolor(colors["grid"])
        for text in legend.get_texts():
            text.set_color(colors["axes"])

    def _rescale(self) -> None:
        self.axes.relim(visible_only=True)
        self.axes.autoscale_view()
        if self.options.x_range:
            self.axes.set_xlim(*self.options.x_range)
        if self.options.y_range:
            self.axes.set_ylim(*self.options.y_range)
        self.draw_idle()

    # ------------------------------------------------------------ overlays

    def set_display_scale(self, scale: float) -> None:
        """Tick labels in the display unit (display = MPa * scale)."""

        self.display_scale = scale
        for axis in (self.axes.xaxis, self.axes.yaxis):
            axis.set_major_formatter(FuncFormatter(lambda v, _pos, k=scale: localize(f"{v * k:g}")))
        self.draw_idle()

    def set_axes_labels(self, xlabel: str, ylabel: str) -> None:
        """Relabel the axes (spec 017: display units)."""

        self.axes.set_xlabel(symbols(xlabel))  # spec 025e: σ₃, τ on screen
        self.axes.set_ylabel(symbols(ylabel))
        self.apply_theme(self._theme)

    def redraw(self, x, y, x_mc=None, y_mc=None) -> None:
        self._line.set_data(x, y)
        self._mc_line.set_data(x_mc if x_mc is not None else [], y_mc if y_mc is not None else [])
        self._update_legend()
        self._rescale()

    def show_mogi(self, x, y) -> None:
        self._mogi_line.set_data(x, y)
        self.draw_idle()

    def clear_mogi(self) -> None:
        self._mogi_line.set_data([], [])
        self.draw_idle()

    # -------------------------------------------------------------- sampler

    def show_sample(self, x: float | None, tangent=None, marker=None) -> None:
        """Dotted vertical marker at x; optional tangent line and point.

        x=None keeps the marker hidden (used for converted tangent lines
        drawn on a plot with no envelope).
        """

        if x is None:
            self._vline.set_visible(False)
        else:
            self._vline.set_xdata([x, x])
            self._vline.set_visible(True)
        if tangent is not None:
            self._tangent_line.set_data(tangent[0], tangent[1])
        else:
            self._tangent_line.set_data([], [])
        if marker is not None:
            self._marker.set_offsets([[marker[0], marker[1]]])
        else:
            self._marker.set_offsets(_EMPTY_OFFSETS)
        self.draw_idle()

    def clear_sample(self) -> None:
        self._vline.set_visible(False)
        self._tangent_line.set_data([], [])
        self._marker.set_offsets(_EMPTY_OFFSETS)
        self.draw_idle()

    # --------------------------------------------------------------- export

    def series_data(self) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        """Current (x, y) arrays per series, for CSV export."""

        data = {}
        for key, artist in self._series_artists().items():
            x, y = artist.get_data()
            if len(x) and artist.get_visible():
                data[key] = (np.asarray(x, dtype=float), np.asarray(y, dtype=float))
        return data

    def can_export(self) -> bool:
        return bool(self.series_data() or self.other_series() or self.layer_series())

    def export_reason(self) -> str:
        return "" if self.can_export() else tr("This graph has no data to export.")

    def other_series(self) -> list[tuple[str, np.ndarray, np.ndarray]]:
        """(material name, x, y) of the other materials drawn (spec 011)."""

        out = []
        for line in self._others:
            x, y = line.get_data()
            out.append((line.ogr_label, np.asarray(x, dtype=float), np.asarray(y, dtype=float)))
        return out

    def save_image(self, path: str) -> None:
        self.figure.savefig(path)

    def line_color(self, kind: str) -> str:
        return mpl_colors(self._theme)[kind]


class PathCanvas(FigureCanvasQTAgg):
    """One of the Stress Path Graphs (spec 012): series of (x, y) per path.

    Stress axes hold internal MPa and show the display unit through a tick
    formatter (spec 017); strain axes are plotted as given. The axis labels
    come in English: shown translated, kept in English for the CSV export
    (spec 024: files do not change with the language).
    """

    def __init__(self, title: str, xlabel: str, ylabel: str, x_stress: bool, y_stress: bool, theme: str = "light") -> None:
        self._theme = theme
        self.title = title
        self._labels = (xlabel, ylabel)
        self._stress_axes = (x_stress, y_stress)
        self._unit = "kPa"
        self.menu_handler = None  # fn(canvas, kind)
        self.figure = Figure(figsize=(4.0, 3.0), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self._lines: list = []
        # spec 025d RF-1: what an empty graph is missing, in the middle of it
        self._empty = self.axes.text(
            0.5, 0.5, "", transform=self.axes.transAxes, ha="center", va="center", wrap=True, fontsize="small"
        )
        # spec 013c: animation marker and the current yield surface (q-p graph)
        (self._anim_marker,) = self.axes.plot([], [], "o", color="#1f4fd8", markersize=7, zorder=6)
        (self._anim_surface,) = self.axes.plot([], [], "--", color="#1f4fd8", linewidth=1.0, zorder=2)
        self.set_display(1.0, "kPa")
        self.apply_theme(theme)

    def show_animation(self, point=None, surface=None) -> None:
        """Mark the animated step (x, y) and draw the current yield surface (xs, ys); MPa."""

        self._anim_marker.set_data(*(([point[0]], [point[1]]) if point is not None else ([], [])))
        self._anim_surface.set_data(*(surface if surface is not None else ([], [])))
        self.draw_idle()

    def animation_data(self):
        return self._anim_marker.get_data(), self._anim_surface.get_data()

    def set_display(self, scale: float, unit: str) -> None:
        """Display factor and unit of the stress axes."""

        self._unit = unit
        xlabel, ylabel = (tr(label) for label in self._labels)  # i18n: ignore (keys marked where the canvases are made)
        self.axes.set_xlabel(symbols(f"{xlabel} ({unit})" if self._stress_axes[0] else xlabel))
        self.axes.set_ylabel(symbols(f"{ylabel} ({unit})" if self._stress_axes[1] else ylabel))
        for axis, is_stress in ((self.axes.xaxis, self._stress_axes[0]), (self.axes.yaxis, self._stress_axes[1])):
            if is_stress:
                axis.set_major_formatter(FuncFormatter(lambda v, _pos, k=scale: localize(f"{v * k:g}")))
        self.display_scale = scale
        self.apply_theme(self._theme)

    def export_labels(self) -> tuple[str, str]:
        """The axis labels in English with the stress unit (CSV column names)."""

        return tuple(
            f"{label} ({self._unit})" if stress else label for label, stress in zip(self._labels, self._stress_axes)
        )

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        colors = mpl_colors(theme)
        self.figure.set_facecolor(colors["figure"])
        self.axes.set_facecolor(colors["figure"])
        self.axes.set_title(self.title, color=colors["axes"])
        for label in (self.axes.xaxis.label, self.axes.yaxis.label):
            label.set_color(colors["axes"])
        self.axes.tick_params(colors=colors["axes"], labelcolor=colors["axes"])
        for spine in self.axes.spines.values():
            spine.set_color(colors["axes"])
        self.axes.grid(True, alpha=0.6, color=colors["grid"])
        self._legend()
        self.draw_idle()

    def set_series(self, series) -> None:
        """Iterable of (label, x, y, color[, style]) with stress values in MPa.

        style (optional dict) overrides the line keywords: stress paths are
        dotted lab steps, simulated tests (spec 013) plain lines.
        """

        for line in self._lines:
            line.remove()
        self._lines = []
        for entry in series:
            label, x, y, color = entry[:4]
            style = {"marker": ".", "markersize": 5.0, "linewidth": 1.4}
            if len(entry) > 4 and entry[4]:
                style.update(entry[4])
            (line,) = self.axes.plot(x, y, color=color, **style)
            line.ogr_label = label
            self._lines.append(line)
        self._empty.set_text("" if self._lines else tr("No stress paths or computed test simulations"))
        self.axes.relim()
        self.axes.autoscale_view()
        self._legend()
        self.draw_idle()

    def _legend(self) -> None:
        legend = self.axes.get_legend()
        if legend is not None:
            legend.remove()
        if not self._lines:
            return
        colors = mpl_colors(self._theme)
        legend = self.axes.legend(self._lines, [l.ogr_label for l in self._lines], fontsize="small")
        legend.get_frame().set_facecolor(colors["figure"])
        legend.get_frame().set_edgecolor(colors["grid"])
        for text in legend.get_texts():
            text.set_color(colors["axes"])

    def series_data(self) -> list[tuple[str, np.ndarray, np.ndarray]]:
        return [(l.ogr_label, *(np.asarray(v, dtype=float) for v in l.get_data())) for l in self._lines]

    def empty_message(self) -> str:
        return self._empty.get_text()

    def can_export(self) -> bool:
        return bool(self._lines)

    def export_reason(self) -> str:
        return "" if self.can_export() else tr("This graph has no data to export.")

    def save_image(self, path: str) -> None:
        self.figure.savefig(path)

    def contextMenuEvent(self, event) -> None:
        if self.menu_handler is None:
            return
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        menu.addAction(tr("Copy Graph as Image"), lambda: self.menu_handler(self, "copy"))
        menu.addAction(tr("Save Graph as Image…"), lambda: self.menu_handler(self, "save"))
        export = menu.addAction(tr("Export Graph to Excel (CSV)…"), lambda: self.menu_handler(self, "export"))
        export.setEnabled(self.can_export())  # spec 025d RF-5: disabled with its reason
        export.setToolTip(self.export_reason())
        menu.exec(event.globalPos())
