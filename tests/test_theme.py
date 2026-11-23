"""Spec 020: OGR-Slip2D design language (themes, menus, canvases)."""

from __future__ import annotations

from ogr_data.gui.themes import THEMES, mpl_colors


def test_theme_sheets_contain_suite_tokens():
    # Tokens verified in OGR-Slip2D ogr_gui/themes/__init__.py
    assert "#4a90d9" in THEMES["light"]  # accent
    assert "#b9d7f7" in THEMES["light"]  # selection
    assert "#fffddc" in THEMES["light"]  # tooltip
    assert THEMES["dark"].count("#2b2b2b") > 0  # dark background
    assert "#6aa3d5" in THEMES["dark"]


def test_mpl_colors_per_theme():
    light = mpl_colors("light")
    dark = mpl_colors("dark")
    assert light["figure"] == "#ffffff"
    assert dark["figure"] == "#2b2b2b"
    assert light["envelope"] != dark["envelope"]


def test_apply_theme_sets_stylesheet():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.themes import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "dark")
    assert "#2b2b2b" in app.styleSheet()
    apply_theme(app, "light")
    assert "#f3f3f3" in app.styleSheet()


def test_window_theme_switch_offscreen():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    # menu bar with the suite structure
    titles = [a.text() for a in w.menuBar().actions()]
    assert titles == ["File", "Edit", "Materials", "Failure States", "Tests", "Stress Paths", "Calibrate", "Compute", "Analysis", "View", "Help"]
    w._set_theme("dark")
    assert "#2b2b2b" in QApplication.instance().styleSheet()
    assert w._principal.line_color("envelope") == mpl_colors("dark")["envelope"]
    assert str(w._settings.value("theme")) == "dark"
    w._set_theme("light")
    assert w._principal.line_color("envelope") == mpl_colors("light")["envelope"]


def test_canvas_recolors_with_data():
    import numpy as np

    from ogr_data.gui.plots import EnvelopeCanvas

    canvas = EnvelopeCanvas("T", "x", "y", "light")
    x = np.linspace(0, 1, 10)
    canvas.redraw(x, 2 * x + 1)
    canvas.apply_theme("dark")
    r, g, b, _ = canvas.figure.get_facecolor()
    assert (round(r, 3), round(g, 3), round(b, 3)) == (0.169, 0.169, 0.169)  # #2b2b2b
    assert canvas._line.get_color() == mpl_colors("dark")["envelope"]
