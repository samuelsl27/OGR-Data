"""Test simulations (spec 013): define, delete and run element tests on a material."""

from __future__ import annotations

import numpy as np

from ...core import simulation as sm
from ...core import states as st
from ..errors import Conflict, InvalidArgument, choice
from . import operation
from ._common import get_material, named, number


@operation("test_simulation_set", toolset="simulation", mutates=True)
def test_simulation_set(ws, name: str, project_id: str | None = None, material: str | None = None,
                        test_type: str | None = None, seepage: str | None = None, loading: str | None = None,
                        max_strain: float | None = None, steps: int | None = None, cyclic: bool | None = None,
                        cycles: int | None = None, confining_kpa: float | None = None, k0: float | None = None,
                        strain_ratio: list | None = None, color: str | None = None, visible: bool | None = None) -> dict:
    """Create or replace a test simulation of a material (uniaxial, triaxial, biaxial, simple shear, general)."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    names = [t.name for t in m.test_simulations]
    existing = m.test_simulations[names.index(name)] if name in names else None
    data = existing.to_dict() if existing else {"name": name, "color": st.next_color(t.color for t in m.test_simulations)}
    if test_type is not None:
        data["test_type"] = choice("test_type", test_type, sm.TEST_TYPES)
    if seepage is not None:
        data["seepage"] = choice("seepage", seepage, sm.SEEPAGE)
    if loading is not None:
        data["loading"] = choice("loading", loading, sm.LOADING)
    if max_strain is not None:
        data["max_strain"] = number("max_strain", max_strain, positive=True, hi=1.0)
    if steps is not None:
        data["steps"] = int(number("steps", steps, lo=1, hi=100000))
    if cyclic is not None:
        data["cyclic"] = bool(cyclic)
    if cycles is not None:
        data["cycles"] = int(number("cycles", cycles, lo=1, hi=1000))
    if confining_kpa is not None:
        data["confining"] = number("confining_kpa", confining_kpa, lo=0.0)
    if k0 is not None:
        data["k0"] = number("k0", k0, positive=True)
    if strain_ratio is not None:
        if not isinstance(strain_ratio, list) or len(strain_ratio) != 6:
            raise InvalidArgument(f"strain_ratio has 6 components ({', '.join(sm.STRAIN_COMPONENTS)}).")
        data["strain_ratio"] = [number("strain_ratio", v) for v in strain_ratio]
    if color is not None:
        data["color"] = str(color)
    if visible is not None:
        data["visible"] = bool(visible)
    test = sm.TestSimulation.from_dict(data)
    if existing:
        m.test_simulations[names.index(name)] = test
    else:
        m.test_simulations.append(test)
    return {"material": m.name, "test_simulation": test.to_dict(), "tests": [t.name for t in m.test_simulations],
            "units": "confining in kPa (initial effective lateral stress); axial = lateral / k0"}


@operation("test_simulation_delete", toolset="simulation", mutates=True)
def test_simulation_delete(ws, name: str, project_id: str | None = None, material: str | None = None) -> dict:
    """Delete a test simulation of a material."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    del m.test_simulations[named(m.test_simulations, name, "test simulation")]
    return {"material": m.name, "tests": [t.name for t in m.test_simulations]}


def _pick(values: np.ndarray, idx: np.ndarray) -> list[float]:
    return [float(v) for v in np.asarray(values)[idx]]


@operation("test_simulation_run", toolset="simulation")
def test_simulation_run(ws, name: str, project_id: str | None = None, material: str | None = None,
                        samples: int = 21) -> dict:
    """Run a test simulation: peak and final state, first yield, and sampled curves (kPa, strains as fractions)."""

    p = ws.get(project_id).project
    _, m = get_material(p, material)
    test = m.test_simulations[named(m.test_simulations, name, "test simulation")]
    if m.criterion not in sm.SIMULATED_CRITERIA:
        raise Conflict(f"{m.criterion} has no constitutive model for test simulation.",
                       hint=f"Simulated criteria: {', '.join(sm.SIMULATED_CRITERIA)}.")
    try:
        r = sm.simulate_material(m, test)
    except (sm.SimulationError, ValueError) as exc:
        raise InvalidArgument(f"{m.name} / {test.name}: {exc}") from None
    n = len(r.q)
    idx = np.unique(np.linspace(0, n - 1, max(2, int(number("samples", samples, lo=2, hi=2000)))).round().astype(int))
    peak = int(np.argmax(r.q))
    yielded = np.flatnonzero(r.yielded)
    shear = test.test_type == "simple_shear"
    out = {
        "material": m.name, "criterion": m.criterion, "test": test.to_dict(), "steps_computed": n - 1,
        "peak": {"step": peak, "q_kpa": float(r.q[peak]), "p_kpa": float(r.p[peak]),
                 "axial_strain": float(r.axial_strain[peak])},
        "final": {"q_kpa": float(r.q[-1]), "p_kpa": float(r.p[-1]), "axial_stress_kpa": float(r.axial_stress[-1]),
                  "volumetric_strain": float(r.eps_v[-1]), "pore_pressure_kpa": float(r.pore_pressure[-1])},
        "first_yield_step": int(yielded[0]) if len(yielded) else None,
        "curves": {
            "step": [int(i) for i in idx],
            "axial_strain": _pick(r.axial_strain, idx),
            "axial_stress_kpa": _pick(r.axial_stress, idx),
            "p_kpa": _pick(r.p, idx),
            "q_kpa": _pick(r.q, idx),
            "volumetric_strain": _pick(r.eps_v, idx),
            "deviatoric_strain": _pick(r.eps_q, idx),
            "pore_pressure_kpa": _pick(r.pore_pressure, idx),
        },
        "sign_convention": "compression positive (as the reference program)",
    }
    if shear:
        out["curves"]["shear_strain"] = _pick(r.shear_strain, idx)
        out["curves"]["shear_stress_kpa"] = _pick(r.shear_stress, idx)
    if test.test_type in ("uniaxial", "triaxial") and test.seepage == "Drained" and test.loading == "Compression" \
            and m.criterion in ("mohr_coulomb", "hoek_brown", "generalized_hoek_brown"):
        try:
            out["analytic_failure_q_kpa"] = float(sm.failure_deviator(m.criterion, m.parameters, test))
        except (ValueError, sm.SimulationError):
            pass
    return out
