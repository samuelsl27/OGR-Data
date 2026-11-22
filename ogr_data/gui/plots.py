"""matplotlib canvases for the strength envelopes."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .themes import mpl_colors


class EnvelopeCanvas(FigureCanvasQTAgg):
    """Single-axes canvas; call redraw(sig3, sig1, normal, shear, mc)."""

    def __init__(self, title: str, xlabel: str, ylabel: str, theme: str = "light") -> None:
        self._theme = theme
        self.figure = Figure(figsize=(4.0, 4.0), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        (self._line,) = self.axes.plot([], [], linewidth=1.8)
        (self._mc_line,) = self.axes.plot([], [], linewidth=1.2, linestyle="--")
        self.axes.margins(x=0.05, y=0.05)
        self.apply_theme(theme)

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
        self.draw_idle()

    def redraw(self, x, y, x_mc=None, y_mc=None) -> None:
        self._line.set_data(x, y)
        self._mc_line.set_data(x_mc if x_mc is not None else [], y_mc if y_mc is not None else [])
        self.axes.relim()
        self.axes.autoscale_view()
        self.draw_idle()

    def line_color(self, kind: str) -> str:
        return mpl_colors(self._theme)[kind]
