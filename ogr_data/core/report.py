"""Report generator (spec 015): self-contained HTML report of a project.

Content model of the RSData 1.009 Report Generator (capture 41, analysis
05_profundizacion.md): a document of sections whose visibility is chosen
with check boxes — Cover Page, Table of Contents, Title, Project Summary,
Project Settings, Samples, Defined Material Models, Defined Failure
States, Defined Test Simulations, Defined Stress Paths. OGR Data adds
"Graph Views", the views captured with Add View To Report.

The output is one HTML5 file with inline CSS and the graph images
embedded as base64 data URIs (no external resources), printable to PDF
from any browser. Empty sections are left out, also from the contents.

Values: registry parameters are kPa and degrees; computed stresses are
MPa (core convention); both are shown in the display stress unit.
"""

from __future__ import annotations

import base64
import html
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from . import criteria_envelopes as ce
from . import samplers
from . import units
from .hoek_brown import HbInput, ModulusMethod, compute, equivalent_mc, global_strength
from .models import CRITERIA, MODULUS_METHODS
from .project import SYMBOLS, Material, Project
from .states import FAILURE_TEST_TYPES, PATH_TEST_TYPES, FailureState, StressPath

# (key, label) in document order. Labels as in RSData, plus Graph Views.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("cover", "Cover Page"),
    ("toc", "Table of Contents"),
    ("title", "Title"),
    ("project_summary", "Project Summary"),
    ("project_settings", "Project Settings"),
    ("views", "Graph Views"),
    ("samples", "Samples"),
    ("material_models", "Defined Material Models"),
    ("failure_states", "Defined Failure States"),
    ("test_simulations", "Defined Test Simulations"),
    ("stress_paths", "Defined Stress Paths"),
)
SECTION_LABELS = dict(SECTIONS)
# sections that frame the document; the others are content listed in the TOC
FRAME_SECTIONS = ("cover", "toc", "title")

UNTITLED = "Untitled Project"
APPLICATION_LABELS = {"custom": "Custom", "tunnel": "Tunnel", "slope": "Slope"}

Rows = list[tuple[str, str]]


def default_visibility() -> dict[str, bool]:
    return {key: True for key, _ in SECTIONS}


# ------------------------------------------------------------------ views


@dataclass
class ReportView:
    """Snapshot of a graph view (Add View To Report).

    A copy taken when the view is added: editing the material later does
    not change it. images: (caption, PNG bytes).
    """

    title: str
    material: str = ""
    criterion: str = ""
    stress_unit: str = units.DEFAULT_STRESS_UNIT
    parameters: Rows = field(default_factory=list)
    results: Rows = field(default_factory=list)
    images: list[tuple[str, bytes]] = field(default_factory=list)
    sample: str = ""  # sampler reading when the view was added (Samples section)
    created: str = ""

    def __post_init__(self) -> None:
        if not self.created:
            self.created = datetime.now().strftime("%Y-%m-%d %H:%M")


class ReportViews:
    """Ordered list of report views (Manage Report View)."""

    def __init__(self, views: Iterable[ReportView] = ()) -> None:
        self.views: list[ReportView] = list(views)

    def __len__(self) -> int:
        return len(self.views)

    def __iter__(self):
        return iter(self.views)

    def __getitem__(self, index: int) -> ReportView:
        return self.views[index]

    def titles(self) -> list[str]:
        return [v.title for v in self.views]

    def add(self, view: ReportView) -> int:
        self.views.append(view)
        return len(self.views) - 1

    def remove(self, index: int) -> int:
        """Delete a view; returns the index to select next (-1 if none left)."""

        del self.views[index]
        return min(index, len(self.views) - 1)

    def move(self, index: int, delta: int) -> int:
        """Move a view up (delta < 0) or down; returns its new index."""

        if not 0 <= index < len(self.views):
            raise IndexError(index)
        target = max(0, min(len(self.views) - 1, index + delta))
        self.views.insert(target, self.views.pop(index))
        return target

    def rename(self, index: int, title: str) -> str:
        title = title.strip()
        if not title:
            raise ValueError("view title cannot be empty")
        self.views[index].title = title
        return title

    def clear(self) -> None:
        self.views.clear()


# ------------------------------------------------------------- formatting


def _number(value: float) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "-"
    return f"{value:.6g}"


def _kpa(value: float, unit: str) -> float:
    return float(value) * units.stress_factor(unit) / 1000.0


def _mpa_text(value: float, unit: str) -> str:
    return f"{_number(units.to_display(value, unit))} {unit}"


def parameter_rows(material: Material, unit: str) -> Rows:
    """(label, value) of the material's registry fields in the display unit."""

    rows: Rows = []
    for f in CRITERIA[material.criterion].fields:
        value = material.parameters.get(f.key, f.default)
        if f.kind == "bool":
            text = "Yes" if value else "No"
        elif f.kind == "enum":
            text = str(value)
        elif f.unit == "kPa":
            text = f"{_number(_kpa(value, unit))} {unit}"
        elif f.unit == "deg":
            text = f"{_number(float(value))} deg"
        else:
            text = _number(float(value))
        rows.append((f.label, text))
    return rows


def range_rows(material: Material, unit: str) -> Rows:
    """Envelope range and application (spec 009) of a material."""

    app = material.application
    rows: Rows = [("Application", APPLICATION_LABELS.get(app.mode, app.mode))]
    if app.mode != "custom":
        rows.append(("Unit weight", f"{_number(app.unit_weight)} MN/m3"))
        rows.append(("Tunnel depth" if app.mode == "tunnel" else "Slope height", f"{_number(app.depth)} m"))
    rows.append(("sig3max (envelope range)", _mpa_text(material.sig3max_mpa, unit)))
    return rows


def _modulus_method(params: Mapping) -> ModulusMethod:
    label = params.get("modulus_method", MODULUS_METHODS[0])
    index = MODULUS_METHODS.index(label) if label in MODULUS_METHODS else 0
    return list(ModulusMethod)[index]


def computed_rows(material: Material, unit: str) -> Rows:
    """Derived results of a material, as the window's Computed panel.

    Generalized Hoek-Brown: mb, s, a, sigt, sigc, sigcm, equivalent MC and
    Erm. Hoek-Brown (a = 0.5): sigcm and equivalent MC (Hoek 2002).
    Power Curve and Barton-Bandis: best-fit MC over the range (RocData
    2004 p. 10). Other criteria have no derived results.
    """

    p = material.parameters
    sig3max = float(material.sig3max_mpa)
    try:
        if material.criterion == "generalized_hoek_brown":
            inp = HbInput(
                sigci=float(p["sigci"]) / 1000.0,
                gsi=float(p["gsi"]),
                mi=float(p["mi"]),
                disturbance=float(p["d"]),
                ei=float(p.get("ei", 12000000.0)) / 1000.0,
                sig3max=sig3max,
            )
            r = compute(inp, _modulus_method(p))
            return [
                ("mb", f"{r.mb:.4f}"),
                ("s", f"{r.s:.6g}"),
                ("a", f"{r.a:.4f}"),
                ("Tensile strength sigt", _mpa_text(r.sigt, unit)),
                ("Uniaxial compressive strength sigc", _mpa_text(r.sigc, unit)),
                ("Global strength sigcm", _mpa_text(r.sigcm, unit)),
                ("Equivalent cohesion c", _mpa_text(r.mc.cohesion, unit)),
                ("Equivalent friction angle phi", f"{r.mc.friction_deg:.2f} deg"),
                ("Rock mass modulus Erm", _mpa_text(r.erm, unit)),
            ]
        if material.criterion == "hoek_brown":
            sigci = float(p["compressive_strength"]) / 1000.0
            mb, s, a = float(p["mb"]), float(p["s"]), 0.5
            inp = HbInput(sigci=sigci, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max)
            mc = equivalent_mc(inp, mb, s, a)
            return [
                ("Global strength sigcm", _mpa_text(global_strength(inp, mb, s, a), unit)),
                ("Equivalent cohesion c", _mpa_text(mc.cohesion, unit)),
                ("Equivalent friction angle phi", f"{mc.friction_deg:.2f} deg"),
            ]
        if material.criterion in ("power_curve", "barton_bandis"):
            curve = ce.shear_curve(material.criterion, p, sig3max)
            if curve is None:
                return []
            fit = samplers.best_fit_mc(*curve)
            return [
                ("Best-fit MC cohesion c", _mpa_text(fit.cohesion_mpa, unit)),
                ("Best-fit MC friction angle phi", f"{fit.friction_deg:.2f} deg"),
            ]
    except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
        return [("Computation", f"not available ({exc})")]
    return []


# ------------------------------------------------------------------- HTML

_CSS = """
:root { --ink: #1f2933; --muted: #52606d; --line: #cbd2d9; --head: #f0f4f8; --accent: #1f618d; }
* { box-sizing: border-box; }
body { margin: 0; background: #ffffff; color: var(--ink);
       font: 14px/1.45 "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 20px; margin: 32px 0 12px; padding-bottom: 4px; border-bottom: 2px solid var(--accent); color: var(--accent); }
h3 { font-size: 16px; margin: 20px 0 8px; }
h4 { font-size: 14px; margin: 14px 0 6px; color: var(--muted); }
.muted { color: var(--muted); }
table { border-collapse: collapse; margin: 6px 0 12px; font-size: 13px; }
th, td { border: 1px solid var(--line); padding: 3px 8px; text-align: left; vertical-align: top; }
th { background: var(--head); font-weight: 600; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.kv th { width: 260px; }
.cover { min-height: 90vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
.cover .brand { font-size: 15px; letter-spacing: 0.2em; color: var(--accent); margin-bottom: 40px; }
.cover h1 { font-size: 34px; }
.toc ol { padding-left: 20px; }
.toc a { color: var(--accent); text-decoration: none; }
.swatch { display: inline-block; width: 12px; height: 12px; border: 1px solid var(--line); vertical-align: -1px; margin-right: 6px; }
.view { margin: 12px 0 28px; }
.figures { display: flex; flex-wrap: wrap; gap: 12px; }
figure { margin: 0; flex: 1 1 320px; max-width: 100%; }
figure img { width: 100%; height: auto; border: 1px solid var(--line); }
figcaption { font-size: 12px; color: var(--muted); text-align: center; }
.pair { display: flex; flex-wrap: wrap; gap: 24px; }
footer { margin-top: 40px; font-size: 12px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 8px; }
@media print {
  main { max-width: none; padding: 0; }
  .cover, .toc { page-break-after: always; break-after: page; }
  section.content { page-break-before: always; break-before: page; }
  .view, table, figure { page-break-inside: avoid; break-inside: avoid; }
}
"""


def _e(text) -> str:
    return html.escape(str(text), quote=True)


def _kv_table(rows: Sequence[tuple[str, str]]) -> str:
    if not rows:
        return ""
    body = "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in rows)
    return f'<table class="kv"><tbody>{body}</tbody></table>'


def _grid_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = "".join(f"<th>{_e(h)}</th>" for h in header)
    body = "".join(
        "<tr>" + "".join(f'<td class="num">{_e(c)}</td>' for c in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _swatch(color: str) -> str:
    if not color:
        return ""
    return f'<span class="swatch" style="background:{_e(color)}"></span>'


def _image(caption: str, png: bytes) -> str:
    data = base64.b64encode(png).decode("ascii")
    return (
        f'<figure><img alt="{_e(caption)}" src="data:image/png;base64,{data}">'
        f"<figcaption>{_e(caption)}</figcaption></figure>"
    )


def _state_rows(state: FailureState, unit: str) -> tuple[list[str], list[list[str]]]:
    if state.test_type == "general":
        header = [f"{c} ({unit})" for c in state.columns]
        rows = [[_number(_kpa(v, unit)) for v in row] for row in state.tensors]
        return header, rows
    header = [f"{c} ({unit})" for c in state.columns] + ["Exclude"]
    rows = [
        [_number(_kpa(p.x, unit)), _number(_kpa(p.y, unit)), "Yes" if p.exclude else "No"]
        for p in state.points
    ]
    return header, rows


def _path_settings(path: StressPath, unit: str) -> Rows:
    rows: Rows = [("Test Type", PATH_TEST_TYPES.get(path.test_type, path.test_type))]
    if path.test_type in ("triaxial", "biaxial"):
        rows += [
            ("Seepage Condition", path.seepage),
            ("Loading Direction", path.loading),
            ("Initial Effective Lateral Stress", f"{_number(_kpa(path.lateral_stress, unit))} {unit}"),
            ("Initial Effective K0", _number(path.k0)),
        ]
    elif path.test_type == "uniaxial":
        rows.append(("Strain Type", path.strain_type))
    return rows


def _path_rows(path: StressPath, unit: str) -> tuple[list[str], list[list[str]]]:
    columns = path.columns()
    stress = path.stress_columns()
    header = [f"{c} ({unit})" if s else c for c, s in zip(columns, stress)]
    rows = []
    for step in path.steps:
        row = []
        for i, is_stress in enumerate(stress):
            value = step[i] if i < len(step) else 0.0
            row.append(_number(_kpa(value, unit) if is_stress else value))
        rows.append(row)
    return header, rows


class _Builder:
    def __init__(self, project: Project, views: Sequence[ReportView], visibility: Mapping[str, bool], title: str, generated: datetime) -> None:
        self.project = project
        self.views = list(views)
        self.visibility = {**default_visibility(), **dict(visibility)}
        self.title = title
        self.generated = generated
        self.unit = project.stress_unit if project.stress_unit in units.STRESS_FACTORS else units.DEFAULT_STRESS_UNIT

    # ------------------------------------------------------------ sections

    def project_summary(self) -> str:
        p = self.project
        n_states = sum(len(m.failure_states) for m in p.materials)
        n_paths = sum(len(m.stress_paths) for m in p.materials)
        summary = _kv_table(
            [
                ("Project title", self.title),
                ("Date", self.generated.strftime("%Y-%m-%d %H:%M")),
                ("Materials", str(len(p.materials))),
                ("Failure states", str(n_states)),
                ("Stress paths", str(n_paths)),
                ("Graph views", str(len(self.views))),
            ]
        )
        rows = [
            [m.name, CRITERIA[m.criterion].label, "Rock" if CRITERIA[m.criterion].category == "rock" else "Soil",
             str(len(m.failure_states)), str(len(m.stress_paths)), "Yes" if m.visible else "No"]
            for m in p.materials
        ]
        materials = _grid_table(["Material", "Criterion", "Category", "Failure states", "Stress paths", "Visible"], rows)
        return summary + "<h3>Materials</h3>" + materials

    def project_settings(self) -> str:
        return _kv_table(
            [
                ("Units", f"Metric, stress as {self.unit}"),
                ("Stress", self.unit),
                ("Length", "m"),
                ("Unit weight", "MN/m3"),
                ("Angles", "deg"),
            ]
        )

    def views_section(self) -> str:
        parts = []
        for i, v in enumerate(self.views, 1):
            figures = "".join(_image(caption, png) for caption, png in v.images)
            meta = f"{_e(v.material)} · {_e(v.criterion)} · {_e(v.created)}" if v.material else _e(v.created)
            tables = ""
            if v.parameters:
                tables += f"<div><h4>Parameters ({_e(v.stress_unit)})</h4>{_kv_table(v.parameters)}</div>"
            if v.results:
                tables += f"<div><h4>Computed</h4>{_kv_table(v.results)}</div>"
            parts.append(
                f'<div class="view" id="view-{i}"><h3>{i}. {_e(v.title)}</h3>'
                f'<p class="muted">{meta}</p>'
                f'<div class="figures">{figures}</div>'
                f'<div class="pair">{tables}</div></div>'
            )
        return "".join(parts)

    def samples(self) -> str:
        rows = [[v.title, v.sample] for v in self.views if v.sample]
        if not rows:
            return ""
        header = ["View", "Sampler reading"]
        head = "".join(f"<th>{h}</th>" for h in header)
        body = "".join(f"<tr><td>{_e(a)}</td><td>{_e(b)}</td></tr>" for a, b in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    def material_models(self) -> str:
        parts = []
        for m in self.project.materials:
            crit = CRITERIA[m.criterion]
            display = _kv_table(
                [("Criterion", crit.label), ("Color", m.color or "theme default"),
                 ("Symbol", SYMBOLS.get(m.symbol, m.symbol)), ("Visible", "Yes" if m.visible else "No")]
            )
            computed = computed_rows(m, self.unit)
            parts.append(
                f"<h3>{_swatch(m.color)}{_e(m.name)}</h3>{display}"
                f'<div class="pair"><div><h4>Parameters</h4>{_kv_table(parameter_rows(m, self.unit))}</div>'
                f"<div><h4>Envelope range</h4>{_kv_table(range_rows(m, self.unit))}"
                + (f"<h4>Computed</h4>{_kv_table(computed)}" if computed else "")
                + "</div></div>"
            )
        return "".join(parts)

    def failure_states(self) -> str:
        parts = []
        for m in self.project.materials:
            if not m.failure_states:
                continue
            parts.append(f"<h3>{_e(m.name)}</h3>")
            for s in m.failure_states:
                header, rows = _state_rows(s, self.unit)
                info = _kv_table(
                    [("Test Type", FAILURE_TEST_TYPES.get(s.test_type, s.test_type)),
                     ("Points", str(len(rows))), ("Visible", "Yes" if s.visible else "No")]
                )
                table = _grid_table(header, rows) if rows else '<p class="muted">No points.</p>'
                parts.append(f"<h4>{_swatch(s.color)}{_e(s.name)}</h4>{info}{table}")
        return "".join(parts)

    def test_simulations(self) -> str:
        return ""  # spec 013 (test simulations) has no model yet

    def stress_paths(self) -> str:
        parts = []
        for m in self.project.materials:
            if not m.stress_paths:
                continue
            parts.append(f"<h3>{_e(m.name)}</h3>")
            for path in m.stress_paths:
                header, rows = _path_rows(path, self.unit)
                table = _grid_table(header, rows) if rows else '<p class="muted">No steps.</p>'
                parts.append(
                    f"<h4>{_swatch(path.color)}{_e(path.name)}</h4>{_kv_table(_path_settings(path, self.unit))}{table}"
                )
        return "".join(parts)

    # -------------------------------------------------------------- document

    def content(self) -> list[tuple[str, str, str]]:
        """(key, label, html) of the visible, non-empty content sections."""

        makers = {
            "project_summary": self.project_summary,
            "project_settings": self.project_settings,
            "views": self.views_section,
            "samples": self.samples,
            "material_models": self.material_models,
            "failure_states": self.failure_states,
            "test_simulations": self.test_simulations,
            "stress_paths": self.stress_paths,
        }
        out = []
        for key, label in SECTIONS:
            if key in FRAME_SECTIONS or not self.visibility.get(key, True):
                continue
            body = makers[key]()
            if body:
                out.append((key, label, body))
        return out

    def build(self) -> str:
        from .. import __version__

        sections = self.content()
        date = self.generated.strftime("%Y-%m-%d %H:%M")
        parts = []
        if self.visibility.get("cover"):
            parts.append(
                '<div class="cover"><div class="brand">OPENGEOROCK · OGR DATA</div>'
                f"<h1>{_e(self.title)}</h1><p>OGR Data Report</p><p class=\"muted\">{_e(date)}</p></div>"
            )
        if self.visibility.get("toc") and sections:
            items = "".join(f'<li><a href="#{key}">{_e(label)}</a></li>' for key, label, _ in sections)
            parts.append(f'<nav class="toc"><h2>Table of Contents</h2><ol>{items}</ol></nav>')
        if self.visibility.get("title"):
            parts.append(f'<header><h1>{_e(self.title)}</h1><p class="muted">OGR Data Report · {_e(date)}</p></header>')
        for key, label, body in sections:
            parts.append(f'<section class="content" id="{key}"><h2>{_e(label)}</h2>{body}</section>')
        parts.append(f"<footer>Generated by OGR Data {_e(__version__)} on {_e(date)}.</footer>")
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="generator" content="OGR Data {_e(__version__)}">'
            f"<title>{_e(self.title)} - OGR Data Report</title>"
            f"<style>{_CSS}</style></head><body><main>"
            + "".join(parts)
            + "</main></body></html>\n"
        )


def build_html(
    project: Project,
    views: Iterable[ReportView] = (),
    visibility: Mapping[str, bool] | None = None,
    title: str | None = None,
    generated: datetime | None = None,
) -> str:
    """Self-contained HTML report of a project and its graph views."""

    title = (title if title is not None else project.title).strip() or UNTITLED
    return _Builder(project, list(views), visibility or {}, title, generated or datetime.now()).build()


def included_sections(project: Project, views: Iterable[ReportView] = (), visibility: Mapping[str, bool] | None = None) -> list[str]:
    """Keys of the content sections a report would contain (non-empty, visible)."""

    builder = _Builder(project, list(views), visibility or {}, UNTITLED, datetime.now())
    return [key for key, _, _ in builder.content()]


def write_report(path: str | Path, document: str) -> Path:
    path = Path(path)
    path.write_text(document, encoding="utf-8")
    return path
