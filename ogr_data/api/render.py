"""PNG of a strength envelope plot, without Qt (matplotlib Agg).

A language model reads a picture, not 200-point arrays: this draws what
the window's envelope tabs draw (envelopes of the chosen materials, their
failure-state points, the equivalent / best-fit MC on request) in the
light theme, so it can also go into a report.
"""

from __future__ import annotations

import io

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..core import criteria_envelopes as ce
from ..core import material_results as mr
from ..core import units
from ..core.project import Material

ACCENT = "#4a90d9"  # suite envelope colour (light theme)
MC_COLOUR = "#40607a"


def envelope_png(materials: list[Material], plot: str = "principal", unit: str = "MPa", show_data: bool = True,
                 show_mc: bool = False, width_px: int = 900, height_px: int = 620) -> bytes:
    scale = units.stress_factor(unit)  # display = MPa * scale
    fig = Figure(figsize=(width_px / 100.0, height_px / 100.0), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    principal = plot == "principal"
    ax.set_xlabel(f"sigma3 ({unit})" if principal else f"normal stress ({unit})")
    ax.set_ylabel(f"sigma1 ({unit})" if principal else f"shear stress ({unit})")
    ax.grid(True, color="#dedede")
    drawn = 0
    for m in materials:
        colour = m.color or ACCENT
        try:
            curves = ce.envelopes(m.criterion, m.parameters, m.sig3max_mpa)
        except (ValueError, ZeroDivisionError, FloatingPointError):
            continue
        curve = curves[0] if principal else curves[1]
        if curve is not None:
            ax.plot(np.asarray(curve[0]) * scale, np.asarray(curve[1]) * scale, color=colour, lw=1.8, label=m.name)
            drawn += 1
            if show_mc:
                mc = mr.overlay_mc(m.criterion, m.parameters, m.sig3max_mpa, None if principal else curve)
                if mc is not None:
                    x = np.asarray(curve[0])
                    if principal:
                        line = ce.mc_line(mc.cohesion_mpa, mc.friction_deg, float(x.max()))[0]
                    else:
                        line = ce.mc_line(mc.cohesion_mpa, mc.friction_deg, float(x.max()))[1]
                    ax.plot(np.asarray(line[0]) * scale, np.asarray(line[1]) * scale, "--", color=MC_COLOUR, lw=1.1,
                            label=f"{m.name}: MC c={mc.cohesion_mpa * scale:.4g} {unit}, phi={mc.friction_deg:.2f}")
        if show_data:
            for state in m.failure_states:
                pts = state.principal_points() if principal else state.shear_points()
                if pts is None or len(pts[0]) == 0:
                    continue
                k = scale / 1000.0  # points are kPa
                ax.plot(np.asarray(pts[0]) * k, np.asarray(pts[1]) * k, linestyle="None", marker=state.symbol or "o",
                        color=state.color, label=f"{m.name}: {state.name}")
    if drawn == 0:
        ax.text(0.5, 0.5, "no envelope to draw in this space", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.set_xlim(left=min(0.0, ax.get_xlim()[0]))
        ax.set_ylim(bottom=min(0.0, ax.get_ylim()[0]))
        ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return buf.getvalue()
