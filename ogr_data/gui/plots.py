"""matplotlib canvases for the strength envelopes."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class EnvelopeCanvas(FigureCanvasQTAgg):
    """Single-axes canvas; call redraw(sig3, sig1, normal, shear, mc)."""

    def __init__(self, title: str, xlabel: str, ylabel: str) -> None:
        self.figure = Figure(figsize=(4.0, 4.0), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, alpha=0.3)
        (self._line,) = self.axes.plot([], [], color="#c0392b", linewidth=1.5)
        (self._mc_line,) = self.axes.plot([], [], color="#2c3e50", linewidth=1.0, linestyle="--")
        self.axes.margins(x=0.05, y=0.05)

    def redraw(self, x, y, x_mc=None, y_mc=None) -> None:
        self._line.set_data(x, y)
        self._mc_line.set_data(x_mc if x_mc is not None else [], y_mc if y_mc is not None else [])
        self.axes.relim()
        self.axes.autoscale_view()
        self.draw_idle()
