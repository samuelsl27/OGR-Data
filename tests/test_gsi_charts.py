"""Spec 022: digitized GSI charts (general 2000, flysch 2000, heterogeneous 2007), click -> GSI."""

from __future__ import annotations

from ogr_data.core import gsi_charts


def _keys(d, prefix=""):
    out = set()
    if isinstance(d, dict):
        for k, v in d.items():
            out |= {f"{prefix}{k}"} | _keys(v, f"{prefix}{k}.")
    return out


def test_control_points_of_the_digitization() -> None:
    # every control point of the digitization (read on the source) is reproduced within 2 GSI
    # (the digitization reports max. 1.3) and our interpolator matches its own result
    for chart_id in gsi_charts.CHART_IDS:
        data = gsi_charts.chart(chart_id)
        points = data["quality"]["control_points"]
        assert len(points) >= 15
        for cp in points:
            value = gsi_charts.gsi_at(chart_id, cp["u"], cp["v"])
            assert abs(value - cp["gsi_interpolated"]) <= 0.051, (chart_id, cp)
            assert abs(value - cp["gsi_read_by_eye"]) <= 2.0, (chart_id, cp)


def test_isolines_and_monotonic_values() -> None:
    for chart_id in gsi_charts.CHART_IDS:
        data = gsi_charts.chart(chart_id)
        values = sorted(line["gsi"] for line in data["isolines"])
        assert all(b - a == 5 for a, b in zip(values, values[1:]))
        # GSI falls from the top-left to the bottom-right along the diagonal (outside N/A)
        seq = [gsi_charts.gsi_at(chart_id, t, t) for t in (0.3, 0.45, 0.6, 0.75)]
        seq = [g for g in seq if g is not None]
        assert len(seq) >= 3 and all(a > b for a, b in zip(seq, seq[1:])), (chart_id, seq)
    assert gsi_charts.gsi_at("general_2000", 1.2, 0.5) is None


def test_not_applicable_cells() -> None:
    # general: INTACT x POOR/VERY POOR and LAMINATED x VERY GOOD/GOOD
    assert gsi_charts.gsi_at("general_2000", 0.9, 0.05) is None
    assert gsi_charts.gsi_at("general_2000", 0.1, 0.95) is None
    # flysch: G/H x VERY GOOD/GOOD are blank (no contours) -> treated as N/A
    p = gsi_charts.pick("flysch_2000", 0.1, 0.9)
    assert p.gsi is None and p.how == "na" and p.column == "very_good"
    # heterogeneous: 7 N/A cells
    assert len(gsi_charts.chart("heterogeneous_marinos_2007")["not_applicable"]) == 7
    assert gsi_charts.gsi_at("heterogeneous_marinos_2007", 0.9, 0.3) is None
    assert gsi_charts.pick("general_2000", -0.1, 0.5).how == "outside"


def test_types_and_ranges() -> None:
    assert gsi_charts.chart_types("flysch_2000") == list("ABCDEFGH")
    assert gsi_charts.chart_types("heterogeneous_marinos_2007")[-1] == "XI"
    assert gsi_charts.chart_types("general_2000") == []
    # GSI at each type label lies in the band ranges of the digitization (ranges.csv)
    expected = {"A": (44, 66), "C": (32, 45), "F": (13, 28), "H": (5, 20)}
    for label, (lo, hi) in expected.items():
        p = gsi_charts.pick("flysch_2000", *gsi_charts.type_center("flysch_2000", label))
        assert p.types == [label] and lo <= p.gsi <= hi, (label, p)
    p = gsi_charts.pick("flysch_2000", *gsi_charts.type_center("flysch_2000", "C"))
    assert p.type_inferred  # B-C-D-E is one continuous band in the original
    p = gsi_charts.pick("heterogeneous_marinos_2007", *gsi_charts.type_center("heterogeneous_marinos_2007", "XI"))
    assert p.types == ["XI"] and not p.type_inferred and 7 <= p.gsi <= 19


def test_texts_in_english_and_spanish() -> None:
    for chart_id in gsi_charts.CHART_IDS:
        en, es = gsi_charts.texts(chart_id, "en"), gsi_charts.texts(chart_id, "es")
        assert _keys(en) == _keys(es), chart_id
        data = gsi_charts.chart(chart_id)
        assert set(en["columns"]) == {c["key"] for c in data["columns"]}
        assert set(en["rows"]) == {r["key"] for r in data["rows"]}
    assert gsi_charts.texts("flysch_2000", "es")["columns"]["fair"]["label"] == "MEDIA"
    assert gsi_charts.texts("flysch_2000", "fr")["columns"]["fair"]["label"] == "FAIR"  # falls back to English
    p = gsi_charts.pick("flysch_2000", *gsi_charts.type_center("flysch_2000", "A"))
    assert "type A" in p.summary("en") and "tipo A" in p.summary("es")


def test_digitized_pages_in_the_gsi_dialog() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.estimation import GsiDialog

    app = QApplication.instance() or QApplication([])
    dlg = GsiDialog(None, lang="en")
    try:
        page = dlg._digitized["flysch_2000"]
        dlg._tabs.setCurrentWidget(page)
        assert dlg.value is None and "Click" in dlg._result.text()
        u, v = gsi_charts.type_center("flysch_2000", "F")
        page.chart.set_point(u, v)
        assert dlg.value == round(gsi_charts.gsi_at("flysch_2000", u, v), 1)
        assert "type F" in dlg._result.text() and page._type.currentData() == "F"
        dlg.set_language("es")
        assert "tipo F" in dlg._result.text() and "MALA" in dlg._result.text()
        assert "Marinos" in page.notes_html()
        page.chart.set_point(0.1, 0.9)  # blank G/H cells
        assert dlg.value is None and "N/A" in dlg._result.text()
        hetero = dlg._digitized["heterogeneous_marinos_2007"]
        dlg._tabs.setCurrentWidget(hetero)
        hetero._type.setCurrentIndex(hetero._type.findData("IX"))
        hetero._type_chosen()
        assert hetero.result.types == ["IX"] and dlg.value is not None
        general = dlg._digitized["general_2000"]
        dlg._tabs.setCurrentWidget(general)
        general.chart.set_point(0.101, 0.0537)  # control point on the 90 isoline
        assert abs(dlg.value - 90.0) <= 0.1
        app.processEvents()
    finally:
        dlg.deleteLater()
