"""Materials: add, read, edit, delete, compute, copy/paste (clipboard contract), import .roc."""

from __future__ import annotations

from ...core import clipboard
from ...core import criteria_envelopes as ce
from ...core import material_factory as factory
from ...core import material_results as mr
from ...core import roc_import
from ...core import simulation as sm
from ...core.models import defaults
from ...core.project import APPLICATION_MODES, SYMBOLS, TEMPLATES, Material
from ..errors import Conflict, InvalidArgument, NotFound, choice
from . import operation
from ._common import (MPA_TO_KPA, get_material, kpa_dict, material_detail, number, project_summary,
                      sample, validate_parameters)
from ._common import criterion as get_criterion


def _apply_application(m: Material) -> float | None:
    """Recompute sigma3max when the application is tunnel / slope, as the window does live."""

    value = mr.application_sig3max(m.criterion, m.parameters, m.application.mode, m.application.unit_weight,
                                   m.application.depth, m.sig3max_mpa)
    if value is not None:
        m.sig3max_mpa = value
    return value


@operation("material_add", toolset="material", mutates=True)
def material_add(ws, project_id: str | None = None, template: str = "material", name: str | None = None,
                 criterion: str | None = None, parameters: dict | None = None) -> dict:
    """Add a material (Add Material / Add Rock Template / Add Soil Template) and select it."""

    handle = ws.get(project_id)
    p = handle.project
    choice("template", template, TEMPLATES)
    if criterion is not None:
        get_criterion(criterion)
    params = validate_parameters(criterion or TEMPLATES[template][1], parameters)
    index = p.add(template)
    m = p.materials[index]
    if criterion is not None and criterion != m.criterion:
        m.criterion = criterion
        m.parameters = defaults(criterion)
    m.parameters.update(params)
    if name:
        p.rename(index, str(name))
    p.selected = index
    return material_detail(p, index)


@operation("material_get", toolset="material")
def material_get(ws, project_id: str | None = None, material: str | None = None) -> dict:
    """Everything about one material: criterion, parameters (kPa, deg), range, application, data."""

    p = ws.get(project_id).project
    index, _ = get_material(p, material)
    return material_detail(p, index)


@operation("material_set", toolset="material", mutates=True)
def material_set(ws, project_id: str | None = None, material: str | None = None, name: str | None = None,
                 criterion: str | None = None, parameters: dict | None = None, sig3max_kpa: float | None = None,
                 application_mode: str | None = None, unit_weight_kn_m3: float | None = None,
                 depth_m: float | None = None, stiffness: dict | None = None, color: str | None = None,
                 symbol: str | None = None, visible: bool | None = None) -> dict:
    """Edit a material. A new criterion starts from its defaults; only the parameters given change."""

    p = ws.get(project_id).project
    index, m = get_material(p, material)
    new_criterion = m.criterion if criterion is None else get_criterion(criterion).key
    params = validate_parameters(new_criterion, parameters)
    mode = m.application.mode if application_mode is None else choice("application_mode", application_mode, APPLICATION_MODES)
    notes = []
    if mode != "custom" and new_criterion not in mr.HB_FAMILY:
        if application_mode is not None:
            raise Conflict(f"application_mode {mode!r} needs a Hoek-Brown criterion (sigcm); {new_criterion} has none.",
                           hint="Use application_mode='custom' and give sig3max_kpa.")
        mode = "custom"  # as the window: a non-HB criterion falls back to a custom range
        notes.append("application set back to custom: the new criterion is not Hoek-Brown.")
    if sig3max_kpa is not None and mode != "custom":
        raise Conflict("sig3max comes from the application (tunnel / slope).",
                       hint="Pass application_mode='custom' together with sig3max_kpa.")
    if stiffness is not None:
        unknown_keys = set(stiffness) - set(sm.DEFAULT_STIFFNESS)
        if unknown_keys:
            raise InvalidArgument(f"unknown stiffness keys {sorted(unknown_keys)}.", hint=f"Known: {sorted(sm.DEFAULT_STIFFNESS)}.")
    if symbol is not None:
        choice("symbol", symbol, SYMBOLS)
    # all checked: apply
    if new_criterion != m.criterion:
        m.criterion = new_criterion
        m.parameters = defaults(new_criterion)
    m.parameters.update(params)
    if name is not None:
        p.rename(index, str(name))
    if sig3max_kpa is not None:
        m.sig3max_mpa = number("sig3max_kpa", sig3max_kpa, positive=True) / MPA_TO_KPA
    m.application.mode = mode
    if unit_weight_kn_m3 is not None:
        m.application.unit_weight = number("unit_weight_kn_m3", unit_weight_kn_m3, positive=True) / 1000.0
    if depth_m is not None:
        m.application.depth = number("depth_m", depth_m, positive=True)
    if stiffness is not None:
        m.stiffness = sm.stiffness_from({**m.stiffness, **stiffness})
    if color is not None:
        m.color = str(color)
    if symbol is not None:
        m.symbol = symbol
    if visible is not None:
        m.visible = bool(visible)
    try:
        _apply_application(m)
    except (ValueError, ZeroDivisionError) as exc:
        notes.append(f"sigma3max by application not computed: {exc}")
    out = material_detail(p, index)
    if notes:
        out["notes"] = notes
    return out


@operation("material_delete", toolset="material", mutates=True)
def material_delete(ws, project_id: str | None = None, material: str | None = None) -> dict:
    """Delete a material (a project keeps at least one)."""

    handle = ws.get(project_id)
    p = handle.project
    index, m = get_material(p, material)
    if len(p.materials) == 1:
        raise Conflict("A project keeps at least one material.", hint="Add another material first, or edit this one.")
    p.selected = p.remove(index)
    return {"deleted": m.name, **project_summary(handle)}


@operation("material_duplicate", toolset="material", mutates=True)
def material_duplicate(ws, project_id: str | None = None, material: str | None = None) -> dict:
    """Duplicate a material (with its data and tests) under a new name."""

    p = ws.get(project_id).project
    index, _ = get_material(p, material)
    new = p.duplicate(index)
    p.selected = new
    return material_detail(p, new)


@operation("material_compute", toolset="material")
def material_compute(ws, project_id: str | None = None, material: str | None = None, points: int = 11) -> dict:
    """Derived values (mb, s, a, sigt, sigc, sigcm, equivalent c/phi, Erm...) and the envelope, in kPa."""

    p = ws.get(project_id).project
    index, m = get_material(p, material)
    points = int(number("points", points, lo=2, hi=500))
    try:
        computed = kpa_dict(mr.computed(m.criterion, m.parameters, m.sig3max_mpa))
        principal, shear = ce.envelopes(m.criterion, m.parameters, m.sig3max_mpa)
    except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
        raise InvalidArgument(f"{m.name}: cannot compute with these parameters ({exc}).") from None
    out = {"index": index, "name": m.name, "criterion": m.criterion, "sig3max_kpa": m.sig3max_mpa * MPA_TO_KPA,
           "application": m.application.mode, "computed": computed}
    if principal is not None:
        s3, s1 = sample(*principal, points)
        out["principal_envelope"] = {"sigma3_kpa": s3, "sigma1_kpa": s1}
    if shear is not None:
        sn, tau = sample(*shear, points)
        out["shear_envelope"] = {"normal_kpa": sn, "shear_kpa": tau}
    if principal is None and shear is None:
        out["note"] = "this criterion has no strength envelope (parameters only)."
    return out


@operation("material_copy", toolset="material")
def material_copy(ws, project_id: str | None = None, material: str | None = None, format: str = "ogr") -> dict:
    """The text Copy Material / Copy Data put on the clipboard: 'ogr' (contract for Slip2D/FEM2D) or 'tabular'."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    choice("format", format, ("ogr", "tabular"))
    computed = mr.ghb_computed(m.criterion, m.parameters, m.sig3max_mpa)
    if format == "ogr":
        text = clipboard.material_text(m.name or get_criterion(m.criterion).label, m.criterion, m.parameters, computed)
    else:
        text = clipboard.tabular_data(m.criterion, m.parameters, computed)
    return {"format": format, "text": text}


@operation("material_paste", toolset="material", mutates=True)
def material_paste(ws, text: str, project_id: str | None = None) -> dict:
    """Add a material from clipboard text of the OGR material contract (OGR-DATA-MATERIAL:...)."""

    p = ws.get(project_id).project
    try:
        payload = clipboard.parse_material(text)
    except ValueError as exc:
        raise InvalidArgument(str(exc)) from None
    if payload is None:
        raise InvalidArgument(f"The text is not an OGR material: it must start with {clipboard.PREFIX!r}.")
    params = validate_parameters(payload.criterion, {k: v for k, v in payload.parameters.items()
                                                     if k in defaults(payload.criterion)})
    index = p.append(Material(name=payload.name or "Pasted", criterion=payload.criterion, parameters=params))
    p.selected = index
    return material_detail(p, index)


@operation("material_import_roc", toolset="material", mutates=True)
def material_import_roc(ws, path: str, project_id: str | None = None) -> dict:
    """Import a RocData file (.roc) as a new material of the project."""

    p = ws.get(project_id).project
    f = ws.resolve(path)
    if not f.is_file():
        raise NotFound(f"{f} does not exist.")
    try:
        roc = roc_import.parse_roc(f)
    except (ValueError, OSError) as exc:
        raise InvalidArgument(f"{f.name}: {exc}") from None
    index = p.append(factory.from_roc(roc))
    p.selected = index
    return material_detail(p, index)
