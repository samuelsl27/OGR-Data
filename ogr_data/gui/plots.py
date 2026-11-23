"""matplotlib canvases for the strength envelopes."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np

from .themes import mpl_colors

_EMPTY_OFFSETS = np.empty((0, 2))


class EnvelopeCanvas(FigureCanvasQTAgg):
    """Single-axes canvas; call redraw(sig3, sig1, normal, shear, mc).

    space is "principal" (x is sigma3) or "shear" (x is normal stress);
    the sampler handler receives (space, kind, x_data) on mouse events.
    """

    def __init__(self, title: str, xlabel: str, ylabel: str, theme: str = "light", space: str = "principal") -> None:
        self._theme = theme
        self.space = space
        self.sampler_handler = None  # set by MainWindow: fn(space, kind, x)
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

    # --------------------------------------------------------------- theme

    def apply_theme(self, theme: str) -> None:
        """Recolor figure, axes, grid and series with the theme palette."""

        self._theme = theme
        colors = mpl_colors(theme)
        self.figure.set_facecolor(colors["figure"])
        self.axes.set_facecolor(colors["figure"])
        for label in (self.axes.title, self.axes.xaxis.label, self.axes.yaxis.label):
            label.set_color(colors["axes"])
        self.axes.tick_params(colors=colors["axes"], labelcolor=colors["axes"])
        for spine in self.axes.spines.values():
            spine.set_color(colors["axes"])
        self.axes.grid(True, alpha=0.6, color=colors["grid"])
        self._line.set_color(colors["envelope"])
        self._line.set_label("envelope")
        self._mc_line.set_color(colors["mc"])
        self._tangent_line.set_color(colors["point"])
        self._marker.set_facecolor(colors["point"])
        self._marker.set_edgecolor(colors["figure"])
        self._vline.set_color(colors["point"])
        self._mogi_line.set_color(colors["mogi"])
        self._mogi_line.set_label("Mogi line")
        self.draw_idle()

    # ------------------------------------------------------------ overlays

    def set_axes_labels(self, xlabel: str, ylabel: str) -> None:
        """Relabel the axes (spec 017: display units)."""

        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.apply_theme(self._theme)

    def redraw(self, x, y, x_mc=None, y_mc=None) -> None:
        self._line.set_data(x, y)
        self._mc_line.set_data(x_mc if x_mc is not None else [], y_mc if y_mc is not None else [])
        self.axes.relim()
        self.axes.autoscale_view()
        self.draw_idle()

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

    def line_color(self, kind: str) -> str:
        return mpl_colors(self._theme)[kind]
