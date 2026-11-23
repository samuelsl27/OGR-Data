"""Material Database (spec 010, RocProp style): search, read a record, use it."""

from __future__ import annotations

from ...core import database as mdb
from ...core import material_factory as factory
from ..errors import InvalidArgument, NotFound, choice
from . import operation
from ._common import get_material, material_detail, number


def _record(ws, record_id: int) -> dict:
    record = ws.database().get(int(number("record_id", record_id)))
    if record is None:
        raise NotFound(f"No database record {record_id}.", hint="Find ids with database_search.")
    return record


@operation("database_search", toolset="database")
def database_search(ws, query: str = "", page: int = 1) -> dict:
    """Search the materials database (all words must match; gran* wildcards; "exact phrase")."""

    db = ws.database()
    results = db.search(query or "")
    pages = max(1, mdb.MaterialDatabase.page_count(results))
    page = int(number("page", page, lo=1))
    if page > pages:
        raise InvalidArgument(f"page {page} of {pages}.")
    rows = mdb.MaterialDatabase.page(results, page - 1)
    return {"query": query, "results": len(results), "page": page, "pages": pages,
            "records": [{"record_id": r.get("record_id"), "title": mdb.title(r), "tests": mdb.available_tests(r),
                         "specimens": len(mdb.specimen_points(r))} for r in rows]}


@operation("database_get", toolset="database")
def database_get(ws, record_id: int) -> dict:
    """One database record: rock, location, reference and test blocks (MPa as stored)."""

    record = _record(ws, record_id)
    return {"title": mdb.title(record), "record": record}


@operation("database_use", toolset="database", mutates=True)
def database_use(ws, record_id: int, use: str = "material", project_id: str | None = None,
                 material: str | None = None) -> dict:
    """Use a record: 'material' adds a GHB material (sigci, mi); 'failure_state' adds its specimens to a material."""

    choice("use", use, ("material", "failure_state"))
    record = _record(ws, record_id)
    p = ws.get(project_id).project
    try:
        if use == "material":
            sig3max = p.materials[p.selected].sig3max_mpa
            index = p.append(factory.from_record(record, sig3max))
            p.selected = index
            return {"new_material": material_detail(p, index),
                    "note": "GSI and D keep their defaults: set them for the rock mass."}
        index, m = get_material(p, material)
        state = factory.state_from_record(record, m.failure_states)
    except ValueError as exc:
        raise InvalidArgument(f"record {record_id}: {exc}") from None
    m.failure_states.append(state)
    return {"material": m.name, "failure_state": state.to_dict(), "states": [s.name for s in m.failure_states]}
