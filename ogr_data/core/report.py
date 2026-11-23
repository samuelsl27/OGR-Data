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

Language (spec 024): the core knows no languages. Every user-visible text
goes through ``_t(text, translate)`` (English is the key; the default
translation is the identity) and the interface passes its translator,
``build_html(..., translate=i18n.translator("es"), lang="es")``. Numbers,
units and data (names) are never translated.
"""

from __future__ import annotations

import base64
import html
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from . import criteria_envelopes as ce
from . import material_results
from . import samplers
from . import simulation as sm
from . import units
from .hoek_brown import HbInput, ModulusMethod, compute, equivalent_mc, global_strength
from .models import CRITERIA
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

Rows = list[tuple[str, str]]
Translate = Callable[[str], str]


def _t(text: str, translate: Translate | None = None) -> str:
    """``text`` (English) through the report's translation (identity by default)."""

    return translate(text) if translate is not None else text


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


def parameter_rows(material: Material, unit: str, translate: Translate | None = None) -> Rows:
    """(label, value) of the material's registry fields in the display unit."""

    rows: Rows = []
    for f in CRITERIA[material.criterion].fields:
        value = material.parameters.get(f.key, f.default)
        if f.kind == "bool":
            text = _t("Yes", translate) if value else _t("No", translate)
        elif f.kind == "enum":
            text = _t(str(value), translate)
        elif f.kind == "table":
            scale = units.stress_factor(unit) / 1000.0
            stress = f.stress_columns or tuple(False for _ in f.options)
            cells = [
                "(" + ", ".join(_number(float(v) * (scale if st else 1.0)) for v, st in zip(row, stress)) + ")"
                for row in (value or [])
            ]
            text = _t("{0} rows: ", translate).format(len(cells)) + " ".join(cells)
        elif f.unit == "kPa":
            text = f"{_number(_kpa(value, unit))} {unit}"
        elif f.unit == "deg":
            text = f"{_number(float(value))} deg"
        else:
            text = _number(float(value))
        rows.append((_t(f.label, translate), text))
    return rows


def stiffness_rows(material: Material, unit: str, translate: Translate | None = None) -> Rows:
    """Stiffness tab of the material, by model (spec 013)."""

    st = sm.stiffness_from(material.stiffness)
    stress = lambda key: f"{_number(_kpa(st[key], unit))} {unit}"  # noqa: E731
    stiffness = _t("Stiffness", translate)
    if material.criterion in ("cam_clay", "modified_cam_clay"):
        rows: Rows = [
            (stiffness, _t("CamClay Isotropic", translate)),
            (_t("Elastic Parameter", translate), _t(st["elastic_parameter"], translate)),
        ]
        if st["elastic_parameter"] == "Constant Shear Modulus":
            return rows + [(_t("Shear Modulus", translate), stress("shear_modulus"))]
        return rows + [(_t("Poisson's Ratio", translate), _number(st["poisson"]))]
    if material.criterion == "norsand":
        return [
            (stiffness, "NorSand"),
            (_t("Shear modulus at reference", translate), stress("g_ref")),
            (_t("Reference pressure for shear modulus", translate), stress("p_ref")),
            (_t("Modulus exponent", translate), _number(st["g_exp"])),
            (_t("Poisson's ratio", translate), _number(st["ns_poisson"])),
            (_t("Minimum Shear Modulus", translate), stress("g_min")),
        ]
    return [
        (stiffness, _t(st["type"], translate)),
        (_t("Poisson's Ratio", translate), _number(st["poisson"])),
        (_t("Young's Modulus", translate), stress("young")),
    ]


def _application_label(mode: str, translate: Translate | None) -> str:
    labels = {"custom": _t("Custom", translate), "tunnel": _t("Tunnel", translate), "slope": _t("Slope", translate)}
    return labels.get(mode, mode)


def range_rows(material: Material, unit: str, translate: Translate | None = None) -> Rows:
    """Envelope range and application (spec 009) of a material."""

    app = material.application
    rows: Rows = [(_t("Application", translate), _application_label(app.mode, translate))]
    if app.mode != "custom":
        rows.append((_t("Unit weight", translate), f"{_number(app.unit_weight)} MN/m3"))
        depth = _t("Tunnel depth", translate) if app.mode == "tunnel" else _t("Slope height", translate)
        rows.append((depth, f"{_number(app.depth)} m"))
    rows.append((_t("sig3max (envelope range)", translate), _mpa_text(material.sig3max_mpa, unit)))
    return rows


def _modulus_method(params: Mapping) -> ModulusMethod:
    return material_results.modulus_method(params)


def computed_rows(material: Material, unit: str, translate: Translate | None = None) -> Rows:
    """Derived results of a material, as the window's Computed panel.

    Generalized Hoek-Brown: mb, s, a, sigt, sigc, sigcm, equivalent MC and
    Erm. Hoek-Brown (a = 0.5): sigcm and equivalent MC (Hoek 2002).
    Power Curve and Barton-Bandis: best-fit MC over the range (RocData
    2004 p. 10). Other criteria have no derived results.
    """

    p = material.parameters
    sig3max = float(material.sig3max_mpa)
    deg = lambda value: f"{value:.2f} deg"  # noqa: E731
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
                (_t("Tensile strength sigt", translate), _mpa_text(r.sigt, unit)),
                (_t("Uniaxial compressive strength sigc", translate), _mpa_text(r.sigc, unit)),
                (_t("Global strength sigcm", translate), _mpa_text(r.sigcm, unit)),
                (_t("Equivalent cohesion c", translate), _mpa_text(r.mc.cohesion, unit)),
                (_t("Equivalent friction angle phi", translate), deg(r.mc.friction_deg)),
                (_t("Rock mass modulus Erm", translate), _mpa_text(r.erm, unit)),
            ]
        if material.criterion == "hoek_brown":
            sigci = float(p["compressive_strength"]) / 1000.0
            mb, s, a = float(p["mb"]), float(p["s"]), 0.5
            inp = HbInput(sigci=sigci, gsi=50.0, mi=10.0, disturbance=0.0, sig3max=sig3max)
            mc = equivalent_mc(inp, mb, s, a)
            return [
                (_t("Global strength sigcm", translate), _mpa_text(global_strength(inp, mb, s, a), unit)),
                (_t("Equivalent cohesion c", translate), _mpa_text(mc.cohesion, unit)),
                (_t("Equivalent friction angle phi", translate), deg(mc.friction_deg)),
            ]
        if material.criterion in ("power_curve", "barton_bandis"):
            curve = ce.shear_curve(material.criterion, p, sig3max)
            if curve is None:
                return []
            fit = samplers.best_fit_mc(*curve)
            return [
                (_t("Best-fit MC cohesion c", translate), _mpa_text(fit.cohesion_mpa, unit)),
                (_t("Best-fit MC friction angle phi", translate), deg(fit.friction_deg)),
            ]
    except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
        return [(_t("Computation", translate), _t("not available ({0})", translate).format(exc))]
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


def _state_rows(state: FailureState, unit: str, translate: Translate | None = None) -> tuple[list[str], list[list[str]]]:
    if state.test_type == "general":
        header = [f"{c} ({unit})" for c in state.columns]
        rows = [[_number(_kpa(v, unit)) for v in row] for row in state.tensors]
        return header, rows
    header = [f"{c} ({unit})" for c in state.columns] + [_t("Exclude", translate)]
    yes, no = _t("Yes", translate), _t("No", translate)
    rows = [
        [_number(_kpa(p.x, unit)), _number(_kpa(p.y, unit)), yes if p.exclude else no]
        for p in state.points
    ]
    return header, rows


def _path_settings(path: StressPath, unit: str, translate: Translate | None = None) -> Rows:
    rows: Rows = [(_t("Test Type", translate), _t(PATH_TEST_TYPES.get(path.test_type, path.test_type), translate))]
    if path.test_type in ("triaxial", "biaxial"):
        rows += [
            (_t("Seepage Condition", translate), _t(path.seepage, translate)),
            (_t("Loading Direction", translate), _t(path.loading, translate)),
            (_t("Initial Effective Lateral Stress", translate), f"{_number(_kpa(path.lateral_stress, unit))} {unit}"),
            (_t("Initial Effective K0", translate), _number(path.k0)),
        ]
    elif path.test_type == "uniaxial":
        rows.append((_t("Strain Type", translate), _t(path.strain_type, translate)))
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
    def __init__(
        self,
        project: Project,
        views: Sequence[ReportView],
        visibility: Mapping[str, bool],
        title: str,
        generated: datetime,
        translate: Translate | None = None,
        lang: str = "en",
    ) -> None:
        self.project = project
        self.views = list(views)
        self.visibility = {**default_visibility(), **dict(visibility)}
        self.title = title
        self.generated = generated
        self.translate = translate
        self.lang = lang
        self.unit = project.stress_unit if project.stress_unit in units.STRESS_FACTORS else units.DEFAULT_STRESS_UNIT

    def _t(self, text: str) -> str:
        return _t(text, self.translate)

    def _yes_no(self, value: bool) -> str:
        return self._t("Yes") if value else self._t("No")

    # ------------------------------------------------------------ sections

    def project_summary(self) -> str:
        p = self.project
        n_states = sum(len(m.failure_states) for m in p.materials)
        n_paths = sum(len(m.stress_paths) for m in p.materials)
        summary = _kv_table(
            [
                (self._t("Project title"), self.title),
                (self._t("Date"), self.generated.strftime("%Y-%m-%d %H:%M")),
                (self._t("Materials"), str(len(p.materials))),
                (self._t("Failure states"), str(n_states)),
                (self._t("Test simulations"), str(sum(len(m.test_simulations) for m in p.materials))),
                (self._t("Stress paths"), str(n_paths)),
                (self._t("Graph views"), str(len(self.views))),
            ]
        )
        rock, soil = self._t("Rock"), self._t("Soil")
        rows = [
            [m.name, self._t(CRITERIA[m.criterion].label), rock if CRITERIA[m.criterion].category == "rock" else soil,
             str(len(m.failure_states)), str(len(m.stress_paths)), self._yes_no(m.visible)]
            for m in p.materials
        ]
        header = ["Material", self._t("Criterion"), self._t("Category"), self._t("Failure states"),
                  self._t("Stress paths"), "Visible"]
        materials = _grid_table(header, rows)
        return summary + f"<h3>{_e(self._t('Materials'))}</h3>" + materials

    def project_settings(self) -> str:
        return _kv_table(
            [
                (self._t("Units"), self._t("Metric, stress as {0}").format(self.unit)),
                (self._t("Stress"), self.unit),
                (self._t("Length"), "m"),
                (self._t("Unit weight"), "MN/m3"),
                (self._t("Angles"), "deg"),
            ]
        )

    def views_section(self) -> str:
        # a view is a snapshot with the English registry labels: translated here
        # (a label already translated is not a key and stays as it is)
        tr = self._t
        parts = []
        for i, v in enumerate(self.views, 1):
            figures = "".join(_image(caption, png) for caption, png in v.images)
            meta = f"{_e(v.material)} · {_e(tr(v.criterion))} · {_e(v.created)}" if v.material else _e(v.created)
            tables = ""
            if v.parameters:
                rows = [(tr(k), value) for k, value in v.parameters]
                tables += f"<div><h4>{_e(self._t('Parameters ({0})').format(v.stress_unit))}</h4>{_kv_table(rows)}</div>"
            if v.results:
                rows = [(tr(k), value) for k, value in v.results]
                tables += f"<div><h4>{_e(self._t('Computed'))}</h4>{_kv_table(rows)}</div>"
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
        header = [self._t("View"), self._t("Sampler reading")]
        head = "".join(f"<th>{_e(h)}</th>" for h in header)
        body = "".join(f"<tr><td>{_e(a)}</td><td>{_e(b)}</td></tr>" for a, b in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    def material_models(self) -> str:
        parts = []
        tr = self.translate
        for m in self.project.materials:
            crit = CRITERIA[m.criterion]
            display = _kv_table(
                [(self._t("Criterion"), self._t(crit.label)), ("Color", m.color or self._t("theme default")),
                 (self._t("Symbol"), self._t(SYMBOLS.get(m.symbol, m.symbol))), ("Visible", self._yes_no(m.visible))]
            )
            computed = computed_rows(m, self.unit, tr)
            parts.append(
                f"<h3>{_swatch(m.color)}{_e(m.name)}</h3>{display}"
                f'<div class="pair"><div><h4>{_e(self._t("Parameters"))}</h4>{_kv_table(parameter_rows(m, self.unit, tr))}</div>'
                f"<div><h4>{_e(self._t('Envelope range'))}</h4>{_kv_table(range_rows(m, self.unit, tr))}"
                + (f"<h4>{_e(self._t('Computed'))}</h4>{_kv_table(computed)}" if computed else "")
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
                header, rows = _state_rows(s, self.unit, self.translate)
                info = _kv_table(
                    [(self._t("Test Type"), self._t(FAILURE_TEST_TYPES.get(s.test_type, s.test_type))),
                     (self._t("Points"), str(len(rows))), ("Visible", self._yes_no(s.visible))]
                )
                table = _grid_table(header, rows) if rows else f'<p class="muted">{_e(self._t("No points."))}</p>'
                parts.append(f"<h4>{_swatch(s.color)}{_e(s.name)}</h4>{info}{table}")
        return "".join(parts)

    def test_simulations(self) -> str:
        """Settings and computed summary of each test (spec 013)."""

        parts = []
        u = self.unit
        stress = lambda value: f"{_number(_kpa(value, u))} {u}"  # noqa: E731
        for m in self.project.materials:
            if not m.test_simulations:
                continue
            parts.append(f"<h3>{_e(m.name)}</h3>" + _kv_table(stiffness_rows(m, u, self.translate)))
            for t in m.test_simulations:
                rows: Rows = [(self._t("Test Type"), self._t(sm.TEST_TYPES[t.test_type]))]
                if t.test_type != "uniaxial":
                    rows.append((self._t("Seepage Condition"), self._t(t.seepage)))
                rows.append((self._t("Loading Direction"), self._t(t.loading)))
                if t.confined:
                    rows.append((self._t("Initial Effective Lateral Stress"), stress(t.confining)))
                    rows.append((self._t("Initial Effective K0"), _number(t.k0)))
                if t.test_type == "general":
                    direction = ", ".join(f"{n} {_number(v)}" for n, v in zip(sm.STRAIN_COMPONENTS, t.strain_ratio))
                    rows.append((self._t("Strain direction"), direction))
                rows += [(self._t("Maximum Strain"), _number(t.max_strain)), (self._t("Number of Steps"), str(t.steps))]
                if t.cyclic:
                    rows.append((self._t("Cyclic Loading Cycles"), str(t.cycles)))
                try:
                    r = sm.simulate_material(m, t)
                except sm.SimulationError as exc:
                    result = f'<p class="muted">{_e(self._t("Not simulated: {0}").format(exc))}</p>'
                else:
                    end: Rows = [
                        (self._t("Peak deviator q"), stress(r.peak_q)),
                        (self._t("Final axial strain"), _number(float(r.axial_strain[-1]))),
                        (self._t("Final axial stress sigma'a"), stress(float(r.axial_stress[-1]))),
                        (self._t("Final p'"), stress(float(r.p[-1]))),
                        (self._t("Final q"), stress(float(r.q[-1]))),
                        (self._t("Final volumetric strain"), _number(float(r.eps_v[-1]))),
                    ]
                    if t.seepage == "Undrained":
                        end.append((self._t("Final pore pressure u"), stress(float(r.pore_pressure[-1]))))
                    result = f"<h4>{_e(self._t('Computed'))}</h4>{_kv_table(end)}"
                parts.append(f"<h4>{_swatch(t.color)}{_e(t.name)}</h4>{_kv_table(rows)}{result}")
        return "".join(parts)

    def stress_paths(self) -> str:
        parts = []
        for m in self.project.materials:
            if not m.stress_paths:
                continue
            parts.append(f"<h3>{_e(m.name)}</h3>")
            for path in m.stress_paths:
                header, rows = _path_rows(path, self.unit)
                table = _grid_table(header, rows) if rows else f'<p class="muted">{_e(self._t("No steps."))}</p>'
                parts.append(
                    f"<h4>{_swatch(path.color)}{_e(path.name)}</h4>"
                    f"{_kv_table(_path_settings(path, self.unit, self.translate))}{table}"
                )
        return "".join(parts)

    # -------------------------------------------------------------- document

    def content(self) -> list[tuple[str, str, str]]:
        """(key, label, html) of the visible, non-empty content sections (label translated)."""

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
                out.append((key, self._t(label), body))
        return out

    def build(self) -> str:
        from .. import __version__

        sections = self.content()
        date = self.generated.strftime("%Y-%m-%d %H:%M")
        report_name = self._t("OGR Data Report")
        parts = []
        if self.visibility.get("cover"):
            parts.append(
                '<div class="cover"><div class="brand">OPENGEOROCK · OGR DATA</div>'
                f"<h1>{_e(self.title)}</h1><p>{_e(report_name)}</p><p class=\"muted\">{_e(date)}</p></div>"
            )
        if self.visibility.get("toc") and sections:
            items = "".join(f'<li><a href="#{key}">{_e(label)}</a></li>' for key, label, _ in sections)
            parts.append(f'<nav class="toc"><h2>{_e(self._t("Table of Contents"))}</h2><ol>{items}</ol></nav>')
        if self.visibility.get("title"):
            parts.append(f'<header><h1>{_e(self.title)}</h1><p class="muted">{_e(report_name)} · {_e(date)}</p></header>')
        for key, label, body in sections:
            parts.append(f'<section class="content" id="{key}"><h2>{_e(label)}</h2>{body}</section>')
        footer = self._t("Generated by OGR Data {0} on {1}.").format(__version__, date)
        parts.append(f"<footer>{_e(footer)}</footer>")
        return (
            "<!DOCTYPE html>\n"
            f'<html lang="{_e(self.lang)}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="generator" content="OGR Data {_e(__version__)}">'
            f"<title>{_e(self.title)} - {_e(report_name)}</title>"
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
    translate: Translate | None = None,
    lang: str = "en",
) -> str:
    """Self-contained HTML report of a project and its graph views.

    ``translate`` gives each English text of the document in the report's
    language (identity by default); ``lang`` is the ``<html lang>``.
    """

    title = (title if title is not None else project.title).strip() or _t("Untitled Project", translate)
    return _Builder(project, list(views), visibility or {}, title, generated or datetime.now(), translate, lang).build()


def included_sections(
    project: Project,
    views: Iterable[ReportView] = (),
    visibility: Mapping[str, bool] | None = None,
    translate: Translate | None = None,
) -> list[str]:
    """Keys of the content sections a report would contain (non-empty, visible)."""

    builder = _Builder(project, list(views), visibility or {}, _t("Untitled Project", translate), datetime.now(), translate)
    return [key for key, _, _ in builder.content()]


def write_report(path: str | Path, document: str) -> Path:
    path = Path(path)
    path.write_text(document, encoding="utf-8")
    return path
