"""Test data and fitting: failure states, stress paths, fit to data, calibration (specs 006, 012, 014)."""

from __future__ import annotations

import numpy as np

from ...core import calibration as cal
from ...core import fitting
from ...core import material_factory as factory
from ...core import material_results as mr
from ...core import states as st
from ...core.models import defaults
from ..errors import InvalidArgument, choice
from . import operation
from ._common import (MPA_TO_KPA, get_material, kpa_dict, material_detail, named, number, validate_parameters)


def _points(points, test_type: str) -> list[st.TestPoint]:
    out = []
    for row in points or []:
        if not isinstance(row, (list, tuple)) or len(row) not in (2, 3):
            raise InvalidArgument(f"each point is [x, y] or [x, y, exclude]; got {row!r}.")
        x, y = number("point x", row[0]), number("point y", row[1])
        if test_type == "triaxial" and x > y:
            raise InvalidArgument(f"triaxial point with sigma3 > sigma1: {row!r}.", hint="Points are [sigma3, sigma1] in kPa.")
        out.append(st.TestPoint(x, y, bool(row[2]) if len(row) == 3 else False))
    return out


@operation("failure_state_set", toolset="data", mutates=True)
def failure_state_set(ws, name: str, project_id: str | None = None, material: str | None = None,
                      test_type: str | None = None, points: list | None = None, tensors: list | None = None,
                      color: str | None = None, visible: bool | None = None) -> dict:
    """Create or replace a failure state (peak test data) of a material: triaxial, direct shear or general."""

    p = ws.get(project_id).project
    index, m = get_material(p, material)
    names = [s.name for s in m.failure_states]
    existing = m.failure_states[names.index(name)] if name in names else None
    tt = choice("test_type", test_type, st.FAILURE_TEST_TYPES) if test_type is not None else (existing.test_type if existing else "triaxial")
    state = st.FailureState.from_dict(existing.to_dict()) if existing else st.FailureState(
        name=name, color=st.next_color(s.color for s in m.failure_states))
    state.test_type = tt
    if points is not None:
        if tt == "general":
            raise InvalidArgument("a general failure state takes tensors, not points.")
        state.points = _points(points, tt)
    if tensors is not None:
        if tt != "general":
            raise InvalidArgument("tensors are for test_type='general'.")
        rows = []
        for row in tensors:
            if not isinstance(row, (list, tuple)) or len(row) != 6:
                raise InvalidArgument(f"each tensor is [{', '.join(st.GENERAL_COLUMNS)}] (kPa); got {row!r}.")
            rows.append(tuple(number("tensor component", v) for v in row))
        state.tensors = rows
    if color is not None:
        state.color = str(color)
    if visible is not None:
        state.visible = bool(visible)
    if existing:
        m.failure_states[names.index(name)] = state
    else:
        m.failure_states.append(state)
    return {"material": m.name, "failure_state": state.to_dict(), "columns": list(state.columns),
            "states": [s.name for s in m.failure_states], "index": index}


@operation("failure_state_delete", toolset="data", mutates=True)
def failure_state_delete(ws, name: str, project_id: str | None = None, material: str | None = None) -> dict:
    """Delete a failure state of a material."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    del m.failure_states[named(m.failure_states, name, "failure state")]
    return {"material": m.name, "states": [s.name for s in m.failure_states]}


@operation("stress_path_set", toolset="data", mutates=True)
def stress_path_set(ws, name: str, project_id: str | None = None, material: str | None = None,
                    test_type: str | None = None, seepage: str | None = None, loading: str | None = None,
                    strain_type: str | None = None, lateral_stress_kpa: float | None = None, k0: float | None = None,
                    steps: list | None = None, color: str | None = None, visible: bool | None = None) -> dict:
    """Create or replace a stress path (measured test path) of a material; answers the step columns."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    names = [s.name for s in m.stress_paths]
    existing = m.stress_paths[names.index(name)] if name in names else None
    data = existing.to_dict() if existing else {"name": name, "color": st.next_color(s.color for s in m.stress_paths)}
    if test_type is not None:
        data["test_type"] = choice("test_type", test_type, st.PATH_TEST_TYPES)
    if seepage is not None:
        data["seepage"] = choice("seepage", seepage, st.SEEPAGE_CONDITIONS)
    if loading is not None:
        data["loading"] = choice("loading", loading, st.LOADING_DIRECTIONS)
    if strain_type is not None:
        data["strain_type"] = choice("strain_type", strain_type, st.STRAIN_TYPES)
    if lateral_stress_kpa is not None:
        data["lateral_stress"] = number("lateral_stress_kpa", lateral_stress_kpa)
    if k0 is not None:
        data["k0"] = number("k0", k0, positive=True)
    if color is not None:
        data["color"] = str(color)
    if visible is not None:
        data["visible"] = bool(visible)
    path = st.StressPath.from_dict(data)
    if steps is not None:
        width = len(path.columns())
        rows = []
        for row in steps:
            if not isinstance(row, (list, tuple)) or len(row) != width:
                raise InvalidArgument(f"each step has {width} values ({', '.join(path.columns())}); got {row!r}.")
            rows.append([number("step value", v) for v in row])
        path.steps = rows
    if existing:
        m.stress_paths[names.index(name)] = path
    else:
        m.stress_paths.append(path)
    return {"material": m.name, "stress_path": path.to_dict(), "columns": list(path.columns()),
            "paths": [s.name for s in m.stress_paths]}


@operation("stress_path_delete", toolset="data", mutates=True)
def stress_path_delete(ws, name: str, project_id: str | None = None, material: str | None = None) -> dict:
    """Delete a stress path of a material."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    del m.stress_paths[named(m.stress_paths, name, "stress path")]
    return {"material": m.name, "paths": [s.name for s in m.stress_paths]}


@operation("fit_data", toolset="data", mutates=True)
def fit_data(ws, criterion: str, data_kind: str, x: list, y: list, method: str = fitting.LINEAR,
             sigci_kpa: float | None = None, disturbance: float | None = None, phi_b_deg: float | None = None,
             apply_to: str | None = None, project_id: str | None = None) -> dict:
    """Fit a criterion to test data (Fit to Data, spec 006); optionally write the result into a material."""

    choice("criterion", criterion, sorted({c for c, _ in fitting.FITS}))
    choice("data_kind", data_kind, fitting.available_fits(criterion))
    choice("method", method, (fitting.LINEAR, fitting.LEVENBERG_MARQUARDT, fitting.SIMPLEX))
    if not isinstance(x, list) or not isinstance(y, list) or len(x) != len(y):
        raise InvalidArgument("x and y are lists of the same length (kPa).")
    xs = np.array([number("x", v) for v in x]) / MPA_TO_KPA
    ys = np.array([number("y", v) for v in y]) / MPA_TO_KPA
    fixed: dict[str, float] = {}
    if criterion == "generalized_hoek_brown":
        if sigci_kpa is None:
            raise InvalidArgument("the rock-mass GHB fit needs sigci_kpa (and disturbance, default 0).")
        fixed = {"sigci_mpa": number("sigci_kpa", sigci_kpa, positive=True) / MPA_TO_KPA,
                 "disturbance": number("disturbance", disturbance or 0.0, lo=0.0, hi=1.0)}
    if criterion == "barton_bandis":
        if phi_b_deg is None:
            raise InvalidArgument("the Barton-Bandis fit needs phi_b_deg (basic friction angle).")
        fixed = {"phi_b_deg": number("phi_b_deg", phi_b_deg)}
    try:
        result = fitting.fit(criterion, data_kind, xs, ys, method, fixed)
    except (ValueError, KeyError) as exc:
        raise InvalidArgument(f"fit failed: {exc}") from None
    target, values = mr.fit_to_parameters(result)
    out = {"criterion": criterion, "data_kind": data_kind, "method": result.method,
           "parameters": kpa_dict(result.parameters), "residuals_kpa2": result.residuals * MPA_TO_KPA**2,
           "applies_as": {"criterion": target, "parameters": values}}
    if criterion == "generalized_hoek_brown":
        out["note"] = "the GHB rock-mass fit (mb, s) fills classic Hoek-Brown (a = 0.5 there), as the window."
    if apply_to is not None:
        p = ws.get(project_id).project
        index, m = get_material(p, apply_to)
        if m.criterion != target:
            m.criterion = target
            m.parameters = defaults(target)
        m.parameters.update(validate_parameters(target, values))
        out["applied_to"] = material_detail(p, index)
    return out


@operation("calibrate", toolset="data", mutates=True)
def calibrate(ws, project_id: str | None = None, material: str | None = None, states: list | None = None,
              strength_type: str = "generalized_hoek_brown", algorithm: str = fitting.LEVENBERG_MARQUARDT,
              error_type: str = "Absolute", data_type: str = "Lab Data", sigci_kpa: float | None = None,
              disturbance: float | None = None, phi_b_deg: float | None = None, new_material_name: str | None = None) -> dict:
    """Calibrate a criterion to failure states of a material (Calibration, spec 014); optionally add the result as a new material."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    choice("strength_type", strength_type, cal.STRENGTH_TYPES)
    choice("algorithm", algorithm, cal.ALGORITHMS)
    choice("error_type", error_type, cal.ERROR_TYPES)
    choice("data_type", data_type, cal.DATA_TYPES)
    chosen = m.failure_states if states is None else [m.failure_states[named(m.failure_states, s, "failure state")] for s in states]
    if not chosen:
        raise InvalidArgument(f"{m.name} has no failure states to calibrate.", hint="Add one with failure_state_set.")
    settings = cal.CalibrationSettings(strength_type=strength_type, algorithm=algorithm, error_type=error_type, data_type=data_type)
    if sigci_kpa is not None:
        settings.sigci_kpa = number("sigci_kpa", sigci_kpa, positive=True)
    if disturbance is not None:
        settings.disturbance = number("disturbance", disturbance, lo=0.0, hi=1.0)
    if phi_b_deg is not None:
        settings.phi_b_deg = number("phi_b_deg", phi_b_deg)
    try:
        result = cal.calibrate(chosen, settings)
    except ValueError as exc:
        raise InvalidArgument(f"calibration failed: {exc}") from None
    out = {"criterion": result.criterion, "parameters": result.parameters, "fitted": kpa_dict(result.fitted),
           "data_kind": result.data_kind, "points": result.n_points, "error_type": error_type,
           "states": [s.name for s in chosen]}
    if error_type == "Absolute":  # residuals of the core are MPa
        out.update(rms_kpa=result.rms * MPA_TO_KPA, ssr_kpa2=result.ssr * MPA_TO_KPA**2)
    else:
        out.update(rms_relative=result.rms, ssr_relative=result.ssr)
    if result.method_note:
        out["note"] = result.method_note
    if new_material_name is not None:
        index = p.append(factory.from_calibration(new_material_name, result, m.sig3max_mpa))
        p.selected = index
        out["new_material"] = material_detail(p, index)
    return out
