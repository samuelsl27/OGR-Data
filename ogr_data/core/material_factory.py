"""Materials and failure states made from other data (spec 019).

What the window's "create material" buttons build — from a USCS group
(spec 018), a database record (spec 010), a calibration (spec 014) or a
.roc file (spec 007) — as plain functions, so that the window and the
operations layer create exactly the same object.
"""

from __future__ import annotations

from typing import Iterable

from . import database as mdb
from . import states as st
from .models import defaults
from .project import DEFAULT_SIG3MAX_MPA, Material


def from_uscs(symbol: str, parameters: dict, sig3max_mpa: float = DEFAULT_SIG3MAX_MPA) -> Material:
    """Mohr-Coulomb material of a USCS group (UFC 3-220-01N Table 8-3.1); residual = peak."""

    params = defaults("mohr_coulomb")
    params.update(parameters)
    params["residual_cohesion"] = params["peak_cohesion"]
    params["residual_friction"] = params["peak_friction"]
    return Material(name=f"{symbol} (typical compacted, UFC 3-220-01N)", criterion="mohr_coulomb",
                    parameters=params, sig3max_mpa=sig3max_mpa)


def from_record(record: dict, sig3max_mpa: float = DEFAULT_SIG3MAX_MPA) -> Material:
    """Generalized Hoek-Brown material from a database record (sigci, mi); GSI and D keep their defaults."""

    params = defaults("generalized_hoek_brown")
    params.update(mdb.to_material_parameters(record))
    return Material(name=mdb.title(record) or "Material", criterion="generalized_hoek_brown",
                    parameters=params, sig3max_mpa=sig3max_mpa)


def state_from_record(record: dict, existing: Iterable[st.FailureState] = ()) -> st.FailureState:
    """Triaxial failure state with the record's specimens (sigma3, sigma1); flagged ones excluded."""

    points = mdb.specimen_points(record)
    if not points:
        raise ValueError("the record has no specimens with sigma3 and sigma1")
    existing = list(existing)
    return st.FailureState(
        name=st.unique_name(mdb.title(record) or "Database", (s.name for s in existing)),
        color=st.next_color(s.color for s in existing),
        points=[st.TestPoint(s3, s1, exclude) for s3, s1, exclude in points],
    )


def from_calibration(name: str, result, sig3max_mpa: float = DEFAULT_SIG3MAX_MPA) -> Material:
    """New material from a calibration (the source material is not changed)."""

    return Material(name=name.strip() or "Calibrated Material", criterion=result.criterion,
                    parameters=dict(result.parameters), sig3max_mpa=sig3max_mpa)


def from_roc(roc) -> Material:
    """Material of an imported .roc file."""

    return Material(name=roc.title or "Imported", criterion=roc.criterion, parameters=dict(roc.parameters),
                    sig3max_mpa=roc.sig3max_mpa if roc.sig3max_mpa is not None else DEFAULT_SIG3MAX_MPA)
