"""Spec 016: plot display options, graph editor behaviour and CSV export."""

from __future__ import annotations

import csv


def test_plot_options_round_trip() -> None:
    from ogr_data.core.graph_options import PlotOptions

    options = PlotOptions(
        title="My plot",
        grid=False,
        square_axis=True,
        labels_inside=True,
        x_range=(0.0, 5.0),
        y_range=(0.0, 10.0),
    )
    options.styles["envelope"].color = "#123456"
    options.styles["envelope"].linewidth = 2.5
    options.styles["mc"].visible = False
    options.styles["mogi"].linestyle = ":"
    restored = PlotOptions.from_dict(options.to_dict())
    assert restored.title == "My plot"
    assert restored.grid is False
    assert restored.square_axis is True
    assert restored.labels_inside is True
    assert restored.x_range == (0.0, 5.0)
    assert restored.y_range == (0.0, 10.0)
    assert restored.styles["envelope"].color == "#123456"
    assert restored.styles["envelope"].linewidth == 2.5
    assert restored.styles["mc"].visible is False
    assert restored.styles["mogi"].linestyle == ":"


def test_plot_options_defaults_and_validation() -> None:
    from ogr_data.core.graph_options import PlotOptions, SeriesStyle

    options = PlotOptions()
    assert options.grid is True and options.square_axis is False
    assert options.x_range is None and options.y_range is None
    assert options.styles["envelope"].visible is True
    assert options.linewidth("envelope") == 1.8  # theme default
    assert options.linestyle("mc") == "--"
    # invalid linestyle and reversed range fall back to defaults
    restored = PlotOptions.from_dict({"styles": {"mc": {"linestyle": "bogus"}}, "x_range": [5.0, 1.0]})
    assert restored.styles["mc"].linestyle == ""
    assert restored.x_range is None
    assert SeriesStyle.from_dict({"visible": "no"}).visible is True


def test_write_series_csv(tmp_path=None) -> None:
    import tempfile
    from pathlib import Path

    import numpy as np

    from ogr_data.core.export import write_series_csv

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "graph.csv"
        write_series_csv(
            path,
            [
                ("sigma3", "sigma1", np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0, 3.0])),
                ("MC sigma3", "MC sigma1", np.array([0.0, 1.0]), np.array([1.5, 2.5])),
            ],
            unit="MPa",
        )
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ["sigma3 (MPa)", "sigma1 (MPa)", "MC sigma3 (MPa)", "MC sigma1 (MPa)"]
        assert len(rows) == 4  # header + longest series (3 rows)
        assert rows[3] == ["2", "3", "", ""]  # shorter series padded
        try:
            write_series_csv(path, [])
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for empty series")
        try:
            write_series_csv(path, [("x", "y", np.array([1.0]), np.array([1.0, 2.0]))])
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for length mismatch")


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w._set_stress_unit("kPa")
    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("generalized_hoek_brown"))
    app.processEvents()
    return w


def test_canvas_options_apply_offscreen() -> None:
    import numpy as np

    from ogr_data.core.graph_options import PlotOptions

    w = _window()
    canvas = w._principal
    canvas.redraw(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0, 5.0]))
    options = PlotOptions(title="Custom title", grid=False, square_axis=True, x_range=(0.0, 4.0), y_range=(0.0, 6.0))
    options.styles["envelope"].color = "#ff0000"
    options.styles["envelope"].linewidth = 3.0
    options.styles["mc"].visible = False
    canvas.apply_options(options)
    assert canvas.axes.get_title() == "Custom title"
    assert canvas.axes.get_xlim() == (0.0, 4.0)
    assert canvas.axes.get_ylim() == (0.0, 6.0)
    assert canvas.axes.get_aspect() == 1.0  # square axis
    assert not canvas.axes.xaxis.get_gridlines()[0].get_visible()
    assert canvas._line.get_color() == "#ff0000"
    assert canvas._line.get_linewidth() == 3.0
    assert not canvas._mc_line.get_visible()
    # zoom extents returns to the natural envelope limits
    canvas.zoom_extents()
    assert canvas.options.x_range is None and canvas.options.y_range is None
    assert canvas.axes.get_xlim() != (0.0, 4.0)


def test_canvas_save_image_and_series_data() -> None:
    import tempfile
    from pathlib import Path

    import numpy as np

    w = _window()
    canvas = w._principal
    series = canvas.series_data()
    assert "envelope" in series and len(series["envelope"][0]) > 0
    assert "mc" in series  # default GHB overlay
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "plot.png"
        canvas.save_image(str(path))
        assert path.exists() and path.stat().st_size > 0


def test_graph_editor_dialog_offscreen() -> None:
    import numpy as np

    w = _window()
    w._principal.redraw(np.array([0.0, 1.0, 2.0]), np.array([1.0, 2.0, 5.0]))
    from ogr_data.gui.graph_editor import GraphEditorDialog

    dlg = GraphEditorDialog(w)
    try:
        dlg._title_edit.setText("Portal section")
        assert w._principal.axes.get_title() == "Portal section"
        # editing does not freeze the default (theme / material) color
        assert w._principal.options.styles["envelope"].color == ""
        dlg._series_controls["envelope"]["width"].setValue(3.0)
        assert w._principal._line.get_linewidth() == 3.0
        dlg._default_range.setChecked(False)
        # ranges are typed in the display unit (kPa) and kept in MPa
        dlg._range_edits["x_lo"].setText("0")
        dlg._range_edits["x_hi"].setText("4000")
        assert w._principal.axes.get_xlim() == (0.0, 4.0)
        assert w._principal.options.x_range == (0.0, 4.0)
        dlg._square_axis.setChecked(True)
        assert w._principal.axes.get_aspect() == 1.0
        dlg._grid.setChecked(False)
        assert not w._principal.axes.xaxis.get_gridlines()[0].get_visible()
        # Cancel restores the snapshot taken at open
        dlg._cancel()
        assert w._principal.axes.get_title() == "Principal Stresses"
        assert w._principal._line.get_linewidth() == 1.8
        assert w._principal.options.x_range is None
        assert w._principal.axes.xaxis.get_gridlines()[0].get_visible()
    finally:
        dlg.deleteLater()
        w.deleteLater()


def test_graph_options_project_round_trip() -> None:
    import tempfile
    from pathlib import Path

    from ogr_data.core import project
    from ogr_data.core.graph_options import PlotOptions

    w = _window()
    w._principal.apply_options(PlotOptions(title="Persisted", x_range=(0.0, 3.0)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.ogrdata"
        project.save_project(path, w._project_for_save())
        data = project.load_project(path)
        restored = PlotOptions.from_dict(data.graph_options["principal"])
        assert restored.title == "Persisted"
        assert restored.x_range == (0.0, 3.0)
    w.deleteLater()
