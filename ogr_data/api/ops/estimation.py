"""Estimation without tests (specs 003, 018, 022): GSI, tables, USCS, Barton scaling."""

from __future__ import annotations

from ...core import barton
from ...core import gsi as qgsi
from ...core import gsi_charts
from ...core import material_factory as factory
from ...core import tables
from ...core import uscs
from ..errors import InvalidArgument, choice
from . import operation
from .catalog import TABLES
from ._common import material_detail, number

RATINGS = ("persistence", "aperture", "roughness", "infilling", "weathering")


@operation("gsi_quantified", toolset="estimation")
def gsi_quantified(ws, rqd: float | None = None, discontinuities_per_m: float | None = None, jv: float | None = None,
                   jv_equation: str = "palmstrom_2005", jcond89: float | None = None, jcond89_ratings: dict | None = None,
                   jcond76: float | None = None, jr: float | None = None, ja: float | None = None) -> dict:
    """GSI from RQD and joint condition (Hoek, Carter & Diederichs 2013, eqs. 1-6): give one RQD source and one joint condition."""

    sources = [k for k, v in (("rqd", rqd), ("discontinuities_per_m", discontinuities_per_m), ("jv", jv)) if v is not None]
    if len(sources) != 1:
        raise InvalidArgument("give exactly one of rqd, discontinuities_per_m (lambda) or jv.")
    if rqd is not None:
        rqd_used, how = number("rqd", rqd, lo=0.0, hi=100.0), "RQD given"
    elif discontinuities_per_m is not None:
        rqd_used, how = qgsi.rqd_from_lambda(number("discontinuities_per_m", discontinuities_per_m, lo=0.0)), "eq. 4 (Priest & Hudson 1976)"
    else:
        choice("jv_equation", jv_equation, ("palmstrom_2005", "palmstrom_1982"))
        rqd_used = qgsi.rqd_from_jv(number("jv", jv, lo=0.0), palmstrom_2005=jv_equation == "palmstrom_2005")
        how = "eq. 6 (Palmstrom 2005)" if jv_equation == "palmstrom_2005" else "eq. 5 (Palmstrom 1982)"
    conditions = [k for k, v in (("jcond89", jcond89), ("jcond89_ratings", jcond89_ratings), ("jcond76", jcond76),
                                 ("jr/ja", jr if jr is not None or ja is not None else None)) if v is not None]
    if len(conditions) != 1:
        raise InvalidArgument("give exactly one joint condition: jcond89, jcond89_ratings, jcond76 or jr + ja.")
    try:
        if jcond89_ratings is not None:
            missing = [k for k in RATINGS if k not in jcond89_ratings]
            extra = set(jcond89_ratings) - set(RATINGS)
            if missing or extra:
                raise InvalidArgument(f"jcond89_ratings has the five ratings {', '.join(RATINGS)} (0-6 each).")
            jcond89 = qgsi.jcond89_from_ratings(*(number(k, jcond89_ratings[k]) for k in RATINGS))
        if jcond89 is not None:
            value, formula = qgsi.gsi_from_jcond89(number("jcond89", jcond89), rqd_used), "GSI = 1.5 JCond89 + RQD/2 (eq. 1)"
            extra_out = {"jcond89": float(jcond89)}
        elif jcond76 is not None:
            value, formula = qgsi.gsi_from_jcond76(number("jcond76", jcond76), rqd_used), "GSI = 2 JCond76 + RQD/2 (eq. 2)"
            extra_out = {"jcond76": float(jcond76)}
        else:
            if jr is None or ja is None:
                raise InvalidArgument("the Q-system route needs both jr and ja.")
            value = qgsi.gsi_from_jr_ja(number("jr", jr, positive=True), number("ja", ja, positive=True), rqd_used)
            formula = "GSI = 52 (Jr/Ja)/(1 + Jr/Ja) + RQD/2 (eq. 3)"
            extra_out = {"jr_ja": jr / ja}
    except ValueError as exc:
        raise InvalidArgument(str(exc)) from None
    return {"gsi": value, "rqd_used": rqd_used, "rqd_from": how, "formula": formula, **extra_out,
            "source": tables.gsi_quantified()["source"]}


@operation("gsi_chart", toolset="estimation")
def gsi_chart(ws, chart: str = "general_2000", u: float | None = None, v: float | None = None,
              rock_type: str | None = None, language: str = "en") -> dict:
    """GSI read on a digitized chart (general 2000, flysch 2000, heterogeneous Marinos 2007) at (u, v) or at a rock-mass type."""

    choice("chart", chart, gsi_charts.CHART_IDS)
    choice("language", language, gsi_charts.LANGUAGES)
    if rock_type is not None:
        if u is not None or v is not None:
            raise InvalidArgument("give either rock_type or (u, v), not both.")
        choice("rock_type", rock_type, gsi_charts.chart_types(chart) or ["(this chart has no types)"])
        u, v = gsi_charts.type_center(chart, rock_type)
    elif u is None or v is None:
        raise InvalidArgument("give u and v (0-1 each), or a rock_type.",
                              hint="u: 0 = VERY GOOD edge .. 1 = VERY POOR edge; v: 0 = top row .. 1 = bottom row.")
    pick = gsi_charts.pick(chart, number("u", u), number("v", v))
    t = gsi_charts.texts(chart, language)
    out = {"chart": chart, "u": pick.u, "v": pick.v, "gsi": pick.gsi, "how": pick.how, "summary": pick.summary(language),
           "column": pick.column, "row": pick.row, "types": pick.types,
           "type_split_inferred": pick.type_inferred, "type_fringe_only": pick.type_fringe,
           "source": gsi_charts.chart(chart)["citation"],
           "accuracy": f'digitized; max. error {gsi_charts.chart(chart)["quality"]["max_abs_error_gsi"]} GSI at the control points'}
    if pick.column:
        out["column_description"] = t["columns"][pick.column]["description"]
    if pick.types and t.get("type_descriptions", {}).get(pick.types[0]):
        out["type_description"] = t["type_descriptions"][pick.types[0]]
    elif pick.row and t["rows"][pick.row].get("description"):
        out["row_description"] = t["rows"][pick.row]["description"]
    return out


def _rows(name: str) -> tuple[list[dict], str]:
    if name == "sigci_grades":
        d = tables.rock_strength_grades()
        return d["grades"], d["source"]
    if name == "gsi_2000_ranges":
        d = tables.gsi_chart()
        rows = []
        for s in d["structures"]:
            for f in d["surfaces"]:
                cell = d["cells"].get(f'{s["key"]}|{f["key"]}')
                rows.append({"structure": s["label"], "surface": f["label"], "gsi_lo": cell[0] if cell else None,
                             "gsi_hi": cell[1] if cell else None})
        return rows, d["source"]
    if name == "soil_field_strength":
        d = tables.soil_field_strength()
        return d["grades"], d["source"]
    loader = {"mi_values": tables.mi_values, "disturbance_factor": tables.disturbance_factor,
              "modulus_ratio": tables.modulus_ratio, "basic_friction_angle": tables.basic_friction_angle,
              "uscs_compacted_properties": tables.uscs_compacted_properties}[name]
    d = loader()
    return d["values"], d["source"]


@operation("table_get", toolset="estimation")
def table_get(ws, table: str, query: str | None = None) -> dict:
    """Rows of a bibliographic table (sigci grades, mi, GSI ranges, D, MR, phi_b, soil grades, USCS), filtered by words."""

    choice("table", table, TABLES)
    rows, source = _rows(table)
    if query:
        words = str(query).lower().split()
        rows = [r for r in rows if all(any(w in str(v).lower() for v in r.values()) for w in words)]
    return {"table": table, "description": TABLES[table], "rows": rows, "count": len(rows), "source": source,
            "units": "ucs_*_mpa in MPa (as the source); others as named"}


@operation("classify_uscs", toolset="estimation", mutates=True)
def classify_uscs(ws, fines_pct: float, sand_pct: float, cu: float | None = None, cc: float | None = None,
                  ll: float | None = None, pi: float | None = None, organic_ratio: float | None = None,
                  highly_organic: bool = False, create_material: bool = False, saturated: bool = True,
                  project_id: str | None = None) -> dict:
    """USCS classification (ASTM D2487) with the typical properties; optionally add the Mohr-Coulomb material of the group (UFC 3-220-01N)."""

    try:
        inp = uscs.UsCSInput(fines_pct=number("fines_pct", fines_pct), sand_pct=number("sand_pct", sand_pct),
                             cu=cu, cc=cc, ll=ll, pi=pi, organic_ratio=organic_ratio, highly_organic=bool(highly_organic))
        result = uscs.classify(inp)
    except ValueError as exc:
        raise InvalidArgument(str(exc)) from None
    out = {"symbol": result.symbol, "group": result.group, "notes": list(result.notes),
           "properties": uscs.uscs_properties(result.symbol), "properties_source": uscs.uscs_properties_source()}
    try:
        out["mohr_coulomb"] = barton.mohr_coulomb_from_symbol(result.symbol, saturated=saturated)
        out["mohr_coulomb_source"] = "UFC 3-220-01N (2005) Table 8-3.1, effective envelope; c' " + ("saturated" if saturated else "as compacted")
    except ValueError as exc:
        out["mohr_coulomb"] = None
        out["mohr_coulomb_note"] = str(exc)
    if create_material:
        if out["mohr_coulomb"] is None:
            raise InvalidArgument(f"no material: {out['mohr_coulomb_note']}")
        p = ws.get(project_id).project
        sig3max = p.materials[p.selected].sig3max_mpa if p.materials else None
        index = p.append(factory.from_uscs(result.symbol, out["mohr_coulomb"], *(() if sig3max is None else (sig3max,))))
        p.selected = index
        out["new_material"] = material_detail(p, index)
    return out


@operation("barton_estimate", toolset="estimation")
def barton_estimate(ws, jrc0: float | None = None, jcs0_kpa: float | None = None, block_length_m: float | None = None,
                    lab_length_m: float = barton.LAB_SCALE_M, phi_b_deg: float | None = None,
                    schmidt_r: float | None = None, schmidt_big_r: float | None = None) -> dict:
    """Barton-Bandis inputs: phi_r from Schmidt rebounds and the JRC / JCS scale correction to the block size."""

    out = {}
    try:
        if phi_b_deg is not None or schmidt_r is not None or schmidt_big_r is not None:
            if None in (phi_b_deg, schmidt_r, schmidt_big_r):
                raise InvalidArgument("phi_r needs phi_b_deg, schmidt_r (weathered joint wall) and schmidt_big_r (fresh rock).")
            out["phi_r_deg"] = barton.phi_r_from_schmidt(number("phi_b_deg", phi_b_deg), number("schmidt_r", schmidt_r),
                                                         number("schmidt_big_r", schmidt_big_r))
        if jrc0 is not None or jcs0_kpa is not None:
            if block_length_m is None or jrc0 is None:
                raise InvalidArgument("the scale correction needs jrc0 and block_length_m (jcs0_kpa for JCS).")
            out["jrc_n"] = barton.jrc_scaled(number("jrc0", jrc0), number("block_length_m", block_length_m), number("lab_length_m", lab_length_m))
            if jcs0_kpa is not None:
                out["jcs_n_kpa"] = barton.jcs_scaled(number("jcs0_kpa", jcs0_kpa), jrc0, block_length_m, lab_length_m)
    except ValueError as exc:
        raise InvalidArgument(str(exc)) from None
    if not out:
        raise InvalidArgument("give phi_b_deg + schmidt_r + schmidt_big_r, and/or jrc0 + block_length_m (+ jcs0_kpa).")
    out["source"] = "Hoek, Practical Rock Engineering (2023), shear strength of discontinuities, eqs. 5-7 (Barton and Bandis 1982)"
    return out

