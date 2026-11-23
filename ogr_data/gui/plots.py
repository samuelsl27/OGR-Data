"""matplotlib canvases for the strength envelopes."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
import numpy as np

from ..core.graph_options import PlotOptions
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
        # spec 017: data stay in internal MPa; ticks show the display unit
        self.display_scale = 1.0
        self.figure = Figure(figsize=(4.0, 4.0), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
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
        menu.addAction("Copy Graph as Image", lambda: self.menu_handler(self, "copy"))
        menu.addAction("Save Graph as Image…", lambda: self.menu_handler(self, "save"))
        menu.addAction("Export Graph to Excel (CSV)…", lambda: self.menu_handler(self, "export"))
        menu.addSeparator()
        menu.addAction("Zoom Extents", lambda: self.menu_handler(self, "zoom"))
        menu.addAction("Graph Editor…", lambda: self.menu_handler(self, "editor"))
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

    def _update_legend(self) -> None:
        """Legend of material names when more than one material is drawn."""

        legend = self.axes.get_legend()
        if legend is not None:
            legend.remove()
        handles = []
        if self._primary_visible and self.options.styles["envelope"].visible and len(self._line.get_xdata()):
            handles.append((self._line, self.primary_label or "Material"))
        handles += [(line, line.ogr_label) for line in self._others]
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
            axis.set_major_formatter(FuncFormatter(lambda v, _pos, k=scale: f"{v * k:g}"))
        self.draw_idle()

    def set_axes_labels(self, xlabel: str, ylabel: str) -> None:
        """Relabel the axes (spec 017: display units)."""

        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
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
