"""Outputs: envelope picture (PNG) and the HTML report (spec 015)."""

from __future__ import annotations

from ...core import report as rpt
from ...core import units
from ..errors import Conflict, InvalidArgument, choice
from ..render import envelope_png
from . import operation
from ._common import get_material


def _materials(project, materials):
    if materials is None:
        chosen = [m for m in project.materials if m.visible] or project.materials[:1]
    else:
        if not isinstance(materials, list) or not materials:
            raise InvalidArgument("materials is a non-empty list of names (or 0-based indices).")
        chosen = [get_material(project, x)[1] for x in materials]
    return chosen


def _target(ws, path: str, suffix: str, overwrite: bool):
    target = ws.resolve(path)
    if target.suffix.lower() != suffix:
        target = target.with_name(target.name + suffix)
    if target.exists() and not overwrite:
        raise Conflict(f"{target} already exists.", hint="Pass overwrite=true to replace it.")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


@operation("render_envelope", toolset="output")
def render_envelope(ws, project_id: str | None = None, materials: list | None = None, plot: str = "principal",
                    unit: str | None = None, show_data: bool = True, show_mc: bool = False,
                    save_path: str | None = None, overwrite: bool = False) -> dict:
    """PNG of the envelopes (sigma1-sigma3 or shear-normal) of materials, with their test points."""

    p = ws.get(project_id).project
    choice("plot", plot, ("principal", "shear"))
    unit = choice("unit", unit or p.stress_unit, units.STRESS_FACTORS)
    chosen = _materials(p, materials)
    png = envelope_png(chosen, plot, unit, show_data=bool(show_data), show_mc=bool(show_mc))
    saved = None
    if save_path is not None:
        target = _target(ws, save_path, ".png", overwrite)
        target.write_bytes(png)
        saved = str(target)
    return {"png": png, "saved_to": saved, "materials": [m.name for m in chosen], "plot": plot, "unit": unit}


@operation("report_generate", toolset="output", mutates=True)
def report_generate(ws, path: str, project_id: str | None = None, title: str | None = None,
                    sections: list | None = None, views: list | None = None, unit: str | None = None,
                    overwrite: bool = False) -> dict:
    """Write the self-contained HTML report; views = materials to add as graph views (both envelopes + values)."""

    p = ws.get(project_id).project
    unit = choice("unit", unit or p.stress_unit, units.STRESS_FACTORS)
    keys = [k for k, _ in rpt.SECTIONS]
    visibility = rpt.default_visibility()
    if sections is not None:
        for s in sections:
            choice("section", s, keys)
        visibility = {k: k in sections for k in keys}
    report_views = []
    for m in _materials(p, views) if views is not None else []:
        report_views.append(rpt.ReportView(
            title=m.name, material=m.name, criterion=m.criterion, stress_unit=unit,
            parameters=rpt.parameter_rows(m, unit), results=rpt.computed_rows(m, unit),
            images=[("sigma1 - sigma3", envelope_png([m], "principal", unit)),
                    ("shear - normal stress", envelope_png([m], "shear", unit))]))
    old_unit = p.stress_unit
    p.stress_unit = unit  # the report writes values in the project's display unit
    try:
        document = rpt.build_html(p, report_views, visibility, title=title)
    finally:
        p.stress_unit = old_unit
    target = _target(ws, path, ".html", overwrite)
    rpt.write_report(target, document)
    return {"saved_to": str(target), "sections": rpt.included_sections(p, report_views, visibility),
            "views": [v.title for v in report_views], "bytes": len(document.encode("utf-8"))}
