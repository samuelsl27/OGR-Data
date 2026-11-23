"""Spec 015: report generator (self-contained HTML)."""

from __future__ import annotations

import base64
import re
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from ogr_data.core import project, report
from ogr_data.core.states import FailureState, StressPath, TestPoint

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
VOID = {"meta", "img", "br", "hr", "link", "input", "col", "area", "base", "source", "wbr"}


class _Checker(HTMLParser):
    """Tag balance, ids and every resource reference of a document."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.ids: list[str] = []
        self.refs: list[str] = []
        self.images = 0
        self.doctype = False

    def handle_decl(self, decl: str) -> None:
        self.doctype = decl.lower() == "doctype html"

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for key in ("src", "href"):
            if key in attrs:
                self.refs.append(attrs[key])
        if tag == "img":
            self.images += 1
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}> (open: {self.stack[-3:]})")
            return
        self.stack.pop()


def _check(document: str) -> _Checker:
    checker = _Checker()
    checker.feed(document)
    checker.close()
    assert checker.doctype, "missing <!DOCTYPE html>"
    assert not checker.errors, checker.errors
    assert not checker.stack, f"unclosed tags {checker.stack}"
    assert len(checker.ids) == len(set(checker.ids)), "duplicated ids"
    for ref in checker.refs:  # self-contained: only embedded images and in-page anchors
        assert ref.startswith("data:image/png;base64,") or ref.startswith("#"), ref
        if ref.startswith("#"):
            assert ref[1:] in checker.ids, f"dangling anchor {ref}"
    assert "<link" not in document and "<script" not in document and "url(" not in document
    return checker


def _two_material_project() -> project.Project:
    proj = project.Project.new()
    proj.title = "Dam <foundation> & abutments"
    proj.stress_unit = "MPa"
    rock = proj.materials[0]
    rock.name = "Granite"
    rock.criterion = "generalized_hoek_brown"
    rock.parameters = {**project.defaults("generalized_hoek_brown"), "sigci": 120000.0, "gsi": 60.0, "mi": 32.0}
    rock.sig3max_mpa = 10.0
    rock.failure_states.append(
        FailureState(name="Triaxial UCS", points=[TestPoint(0.0, 120000.0), TestPoint(10000.0, 210000.0, True)])
    )
    soil = proj.materials[proj.add("soil")]
    soil.name = "Clayey sand"
    soil.stress_paths[0].steps = [[0.0, 0.0, 0.0], [0.001, 50.0, -0.0003]]
    return proj


def _view(title: str, sample: str = "") -> report.ReportView:
    return report.ReportView(title=title, material="Granite", criterion="Generalized Hoek Brown",
                             parameters=[("GSI", "60")], results=[("mb", "7.6")], images=[("Principal Stresses", PNG)],
                             sample=sample)


def test_parameter_and_computed_rows() -> None:
    proj = _two_material_project()
    rock, soil = proj.materials
    rows = dict(report.parameter_rows(rock, "MPa"))
    assert rows["UCS of intact rock"] == "120 MPa" and rows["GSI"] == "60" and rows["Set Residual to Peak"] == "Yes"
    assert dict(report.parameter_rows(rock, "kPa"))["UCS of intact rock"] == "120000 kPa"
    soil_rows = dict(report.parameter_rows(soil, "kPa"))
    assert soil_rows["Peak Cohesion"] == "10.5 kPa" and soil_rows["Peak Friction Angle"] == "35 deg"
    computed = dict(report.computed_rows(rock, "MPa"))
    assert set(computed) >= {"mb", "s", "a", "Global strength sigcm", "Equivalent cohesion c", "Rock mass modulus Erm"}
    # same numbers as the window (core.compute): mb = mi exp((GSI-100)/28) for D = 0
    assert abs(float(computed["mb"]) - 32.0 * 2.718281828 ** (-40.0 / 28.0)) < 1e-3
    assert report.computed_rows(soil, "kPa") == []  # Mohr-Coulomb: nothing derived
    bb = project.Material("Joint", "barton_bandis", {})
    assert [k for k, _ in report.computed_rows(bb, "kPa")] == ["Best-fit MC cohesion c", "Best-fit MC friction angle phi"]
    tunnel = rock.copy()
    tunnel.application = project.Application("tunnel", 0.027, 300.0)
    ranges = dict(report.range_rows(tunnel, "MPa"))
    assert ranges["Application"] == "Tunnel" and ranges["Tunnel depth"] == "300 m"


def test_views_add_remove_reorder_rename() -> None:
    views = report.ReportViews()
    for t in ("A", "B", "C"):
        views.add(_view(t))
    assert views.move(0, 1) == 1 and views.titles() == ["B", "A", "C"]
    assert views.move(2, -5) == 0 and views.titles() == ["C", "B", "A"]
    assert views.move(2, 1) == 2  # already last
    assert views.rename(1, "  Beta ") == "Beta"
    try:
        views.rename(1, "  ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty title accepted")
    assert views.remove(2) == 1 and views.titles() == ["C", "Beta"]
    # the report follows the managed order
    document = report.build_html(_two_material_project(), views)
    assert document.index("C</h3>") < document.index("Beta</h3>")
    assert views.remove(0) == 0 and views.remove(0) == -1 and len(views) == 0


def test_two_material_report_is_valid_and_self_contained() -> None:
    proj = _two_material_project()
    views = report.ReportViews([_view("Granite - Strength Graphs", "sigma3 = 1 MPa   sigma1 = 50 MPa"), _view("Granite - Stress Path Graphs")])
    document = report.build_html(proj, views, generated=datetime(2026, 11, 23, 10, 30))
    checker = _check(document)
    assert checker.images == 2
    # title escaped, project data present, values in the project's display unit
    assert "Dam &lt;foundation&gt; &amp; abutments" in document and "<foundation>" not in document
    for text in ("Granite", "Clayey sand", "Generalized Hoek Brown", "Mohr Coulomb", "Triaxial UCS", "Path 1",
                 "Global strength sigcm", "120 MPa", "Metric, stress as MPa", "2026-11-23 10:30", "sigma1 = 50 MPa"):
        assert text in document, text
    # excluded point listed as such; sections in RSData order (the soil template brings a test, spec 013)
    assert re.search(r"<td class=\"num\">10</td><td class=\"num\">210</td><td class=\"num\">Yes</td>", document)
    assert report.included_sections(proj, views) == [
        "project_summary", "project_settings", "views", "samples", "material_models", "failure_states",
        "test_simulations", "stress_paths",
    ]
    toc = re.search(r'<nav class="toc">(.*?)</nav>', document).group(1)
    assert "Defined Test Simulations" in toc and "Defined Stress Paths" in toc
    tests = document[document.index('id="test_simulations"'):document.index('id="stress_paths"')]
    # uniaxial MC test of the soil: peak q = 2 c sqrt(N_phi) = 40.34 kPa = 0.0403406 MPa
    assert "Uniaxial Test" in tests and "<th>Peak deviator q</th><td>0.0403406 MPa</td>" in tests
    assert "Young&#x27;s Modulus</th><td>20 MPa" in tests
    # a test that cannot be simulated is listed with the reason
    proj.materials[0].test_simulations.append(report.sm.TestSimulation(name="GT", test_type="general", seepage="Undrained"))
    assert "Not simulated: General Test: an undrained test needs a deviatoric strain direction" in report.build_html(proj)


def test_section_visibility_and_empty_sections() -> None:
    proj = project.Project.new()  # one material, no states, paths or views
    assert report.included_sections(proj) == ["project_summary", "project_settings", "material_models"]
    document = report.build_html(proj)
    _check(document)
    assert "Untitled Project" in document and "<img" not in document and "Samples" not in document
    hidden = {key: False for key, _ in report.SECTIONS}
    hidden["material_models"] = True
    document = report.build_html(proj, visibility=hidden, title="Only models")
    _check(document)
    assert 'class="cover"' not in document and 'class="toc"' not in document and "<header>" not in document
    assert "Defined Material Models" in document and "Project Summary" not in document
    with tempfile.TemporaryDirectory() as tmp:
        path = report.write_report(Path(tmp) / "r.html", document)
        assert path.read_text(encoding="utf-8") == document


def test_spanish_report_same_numbers() -> None:
    """Spec 024: the report in Spanish translates texts, never values."""

    from ogr_data.gui import i18n

    proj = _two_material_project()
    proj.title = ""
    proj.materials[0].application.mode = "tunnel"
    views = [_view("Granite - Strength Graphs", "sigma3 = 1 MPa   sigma1 = 50 MPa")]
    generated = datetime(2026, 11, 23, 10, 30)
    english = report.build_html(proj, views, generated=generated)
    spanish = report.build_html(proj, views, generated=generated, translate=i18n.translator("es"), lang="es")
    _check(spanish)
    assert '<html lang="en">' in english and '<html lang="es">' in spanish
    for text in ("Modelos de material definidos", "Estados de rotura definidos", "Índice", "Resumen del proyecto",
                 "Proyecto sin título", "Hoek Brown generalizado", "Ensayo triaxial", "Ensayo de compresión simple",
                 "Resistencia global sigcm", "Profundidad del túnel", "Peso específico", "Métricas, tensiones en MPa",
                 "Hoek &amp; Diederichs generalizado (2006)", "<td class=\"num\">Sí</td>", "Informe de OGR Data"):
        assert text in spanish, text
    for text in ("Defined Material Models", "Table of Contents", "Untitled Project", "Global strength", "Triaxial Test",
                 "Tunnel depth", "Peak Friction Angle"):
        assert text in english and text not in spanish, text
    # data are not translated: names, sampler reading, and every number
    for text in ("Granite", "Clayey sand", "Triaxial UCS", "sigma1 = 50 MPa", "2026-11-23 10:30"):
        assert text in spanish, text
    number = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e[+-]?\d+)?")
    texts = lambda doc: re.sub(r"<[^>]*>", " ", doc[doc.index("<main>"):])  # noqa: E731
    numbers = lambda doc: sorted(number.findall(texts(doc)))  # noqa: E731
    assert numbers(english) == numbers(spanish) and len(numbers(english)) > 40
    # rows used by the window and the API: English unless a translation is given
    rock = proj.materials[0]
    assert report.parameter_rows(rock, "MPa") == report.parameter_rows(rock, "MPa", translate=None)
    es_rows = report.parameter_rows(rock, "MPa", translate=i18n.translator("es"))
    assert [v for _, v in es_rows][:2] == [v for _, v in report.parameter_rows(rock, "MPa")][:2]
    assert dict(es_rows)["RCS de la roca intacta"] == "120 MPa"
    assert report.included_sections(proj, views, translate=i18n.translator("es")) == report.included_sections(proj, views)


def test_window_add_view_manage_and_generate() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow
    from ogr_data.gui.report_dialog import ManageReportViewsDialog, ReportGeneratorDialog

    QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w._set_stress_unit("kPa")
        w._title_edit.setText("Report test")
        names = [a.text() for m in w.menuBar().actions() if m.text() == "Analysis" for a in m.menu().actions()]
        assert {"Report Generator…", "Add View To Report", "Manage Report View…"} <= set(names)
        first = w.add_view_to_report()
        assert first.title == "Material - Strength Graphs" and len(first.images) == 2
        assert all(png[:8] == b"\x89PNG\r\n\x1a\n" for _, png in first.images)
        w._add_material("rock")
        w._graph_tabs.setCurrentIndex(1)
        second = w.add_view_to_report()
        assert second.title == "Rock - Stress Path Graphs" and len(second.images) == 4
        assert ("GSI", "50") in second.parameters and dict(second.results)["mb"]
        # snapshot: later edits do not change the view
        w._widgets["gsi"].setValue(70.0)
        assert ("GSI", "50") in second.parameters
        manage = ManageReportViewsDialog(w.report_views, w)
        try:
            manage.list.setCurrentRow(1)
            manage.move(-1)
            assert w.report_views.titles() == ["Rock - Stress Path Graphs", "Material - Strength Graphs"]
            assert manage.list.currentRow() == 0 and not manage.up.isEnabled()
            manage.list.item(0).setText("Rock paths")  # rename in place
            assert w.report_views.titles()[0] == "Rock paths"
            manage.list.setCurrentRow(1)
            manage.remove_current()
            assert w.report_views.titles() == ["Rock paths"]
        finally:
            manage.deleteLater()
        dialog = ReportGeneratorDialog(w)
        try:
            assert dialog.title.text() == "Report test" and "1 graph view" in dialog.views_label.text()
            dialog.checks["cover"].setChecked(False)
            assert w.report_visibility["cover"] is False  # remembered for the session
            with tempfile.TemporaryDirectory() as tmp:
                path = dialog.generate(Path(tmp) / "report.html")
                document = path.read_text(encoding="utf-8")
            checker = _check(document)
            assert checker.images == 4 and 'class="cover"' not in document
            assert "Rock paths" in document and "GSI" in document and "Material" in document
            # the second material's edited GSI reaches the Defined Material Models section
            models = document[document.index('id="material_models"'):]
            assert "<th>GSI</th><td>70</td>" in models
        finally:
            dialog.deleteLater()
        w._new_project(confirm=False)
        assert len(w.report_views) == 0
    finally:
        w.deleteLater()


def test_spanish_report_decimal_comma() -> None:
    """Spec 024: in Spanish the numbers of the report tables use the decimal comma."""

    import re
    from datetime import datetime

    from ogr_data.core import project as projects
    from ogr_data.gui import i18n

    proj = projects.Project.new()
    proj.materials[0] = projects.Material.from_template("rock", "Granite")
    when = datetime(2026, 11, 23, 12, 0)
    point = report.build_html(proj, generated=when, translate=i18n.translator("es"), lang="es")
    comma = report.build_html(proj, generated=when, translate=i18n.translator("es"), lang="es", decimal=",")
    cells = re.findall(r"<td>(.*?)</td>", comma, re.S)
    assert any(re.search(r"\d,\d", c) for c in cells) and not any(re.search(r"\d\.\d", c) for c in cells)
    # only the table cells change, and only their decimal points
    assert re.sub(r"(?<=\d),(?=\d)", ".", comma) == re.sub(r"(?<=\d),(?=\d)", ".", point)
    assert "<style>" in comma and comma.count("<td>") == point.count("<td>")
