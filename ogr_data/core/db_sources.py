"""Built-in database records from open official sources (spec 010).

The tables were transcribed value by value from the page images of the
original reports (files in ogr_data/data/db_sources, provenance in its
README) and cross-checked: CANMET Tables 1 and 2 share sigma_t and Qu,
and the few cells where the two printed tables disagree are kept as
printed and reported in the record notes.

- CANMET 1995: Jackson, R., Gorski, B. & Gyenge, M. Geotechnical
  Properties of Rock. CANMET, Natural Resources Canada (Government of
  Canada). 77 data sheets of Canadian mine rocks: Table 1 (physical
  properties) and Table 2 (Hoek and Brown constants, intact and residual).
- MnDOT 2018: Folta, B., Sharpe, J., Hu, C. & Labuz, J. Development of a
  Rock Strength Database. Minnesota Department of Transportation, report
  MN/RC 2018-19 (University of Minnesota): individual uniaxial and
  triaxial tests.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from importlib import resources

G = 9.81  # m/s2: unit weight (MN/m3) = density (Mg/m3) x g / 1000

PROVINCES = {
    "P.Q.": "Quebec", "Ont.": "Ontario", "B.C.": "British Columbia", "N.S.": "Nova Scotia",
    "Man.": "Manitoba", "Sask.": "Saskatchewan", "Nfld.": "Newfoundland", "NFLD.": "Newfoundland",
    "N.W.T.": "Northwest Territories", "N.B.": "New Brunswick", "Alta.": "Alberta",
}


def _csv(name: str) -> list[dict]:
    text = resources.files("ogr_data.data").joinpath(f"db_sources/{name}").read_text(encoding="utf-8")
    return list(csv.DictReader(text.splitlines()))


def _num(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _place(origin: str, province: str) -> tuple[str, str, str]:
    """(country, place, region) from the printed origin and province."""

    province = province.strip()
    if province == "U.S.A.":
        return "United States", origin, "North America"
    if "," in province:  # e.g. "Val d'Or, P.Q."
        town, abbr = (p.strip() for p in province.rsplit(",", 1))
        return "Canada", f"{origin}, {town}, {PROVINCES.get(abbr, abbr)}", "North America"
    return "Canada", f"{origin}, {PROVINCES.get(province, province)}", "North America"


CANMET_REFERENCE = {
    "type": "Book",
    "title": "Geotechnical Properties of Rock",
    "author": "R. Jackson, B. Gorski, M. Gyenge",
    "publisher": "CANMET, Natural Resources Canada (Government of Canada)",
    "year": 1995,
    "pages": "",
    "volume": "",
    "isbn": "",
    "edition": "",
}


@lru_cache(maxsize=None)
def canmet_records() -> tuple[dict, ...]:
    from .database import empty_record

    t1 = _csv("canmet_1995_table1.csv")
    t2 = _csv("canmet_1995_table2.csv")
    refs = {r["ref"]: r["citation"] for r in _csv("canmet_1995_table3.csv")}
    out = []
    for a, b in zip(t1, t2):  # same rows, same order (cross-checked)
        record = empty_record()
        record["origin"] = "builtin"
        name = a["rock_type"].strip()
        qualifier = a["rock_qualifier"].strip()
        record["rock_name"] = name[:1].upper() + name[1:] + (f" ({qualifier})" if qualifier else "")
        country, place, region = _place(a["origin"], a["province"])
        record["location"].update({"region": region, "country": country, "place": place})
        notes = ["Mean values of the CANMET laboratory tests (Mining Research Laboratories)."]
        if name == "siltsone":
            record["rock_name"] = "Siltstone" + (f" ({qualifier})" if qualifier else "")
            notes.append('Rock type printed "siltsone" in Table 1 (typo).')
        density = _num(a["density_mg_m3"])
        if a["density_mg_m3"].strip() and density is None:
            notes.append(f'Table 1 density cell reads "{a["density_mg_m3"].strip()}" (not a density; left empty).')
        if density is not None:
            record["density_mg_m3"] = density
            record["unit_weight_mn_m3"] = round(density * G / 1000.0, 5)
        if a["porosity_pct"].strip():
            record["porosity_pct"] = _num(a["porosity_pct"]) if _num(a["porosity_pct"]) is not None else a["porosity_pct"].strip()
        comp = {}
        for key, col, scale in (("ucs_mpa", "ucs_mpa", 1.0), ("e50_mpa", "e_gpa", 1000.0), ("poisson", "poisson", 1.0)):
            value = _num(a[col])
            if value is not None:
                comp[key] = round(value * scale, 6)
        s3min, s3max = _num(b["sigma3_min_mpa"]), _num(b["sigma3_max_mpa"])
        if s3min is not None and s3max is not None:
            comp["confining_stress_mpa"] = f"{s3min:g}-{s3max:g} (triaxial tests)"
        if comp:
            comp["test_type"] = "Uniaxial and triaxial (laboratory)"
            record["tests"]["compression"] = comp
        tensile = _num(a["tensile_mpa"])
        if tensile is not None:
            record["tests"]["tensile"] = {"tensile_strength_mpa": abs(tensile)}
        velocity = {}
        for key, col in (("vp_m_s", "vp_sat_km_s"), ("vp_dry_m_s", "vp_dry_km_s")):
            value = _num(a[col])
            if value is not None:
                velocity[key] = round(value * 1000.0, 3)
        if velocity:
            record["tests"]["velocity"] = velocity
        hb = {}
        for key, col in (("sigci_mpa", "qc_mpa"), ("mi", "m"), ("s", "s"), ("r2", "r2"),
                         ("m_residual", "mr"), ("s_residual", "sr"), ("r2_residual", "r2_residual")):
            value = _num(b[col])
            if value is not None:
                hb[key] = value
        if s3min is not None and s3max is not None:
            hb["confining_range_mpa"] = f"{s3min:g}-{s3max:g}"
        if hb:
            record["tests"]["hoek_brown"] = hb
        # disagreements between the two printed tables
        for label, c1, c2 in (("sigma_t", "tensile_mpa", "tensile_mpa"), ("Qu", "ucs_mpa", "ucs_mpa")):
            v1, v2 = _num(a[c1]), _num(b[c2])
            if v1 is not None and v2 is not None and abs(v1 - v2) > 1e-6:
                notes.append(f"Table 2 prints {label} = {b[c2]} (Table 1: {a[c1]}).")
        if a["data_sheet"] != b["data_sheet"]:
            notes.append(f"Table 2 prints data sheet {b['data_sheet']} (misprint; Table 1 and Table 3 give {a['data_sheet']}).")
        notes.append("Hoek-Brown sigci = Qc, the UCS predicted by the fitted criterion; tensile strength printed negative (tension) in the source.")
        record["notes"] = " ".join(notes)
        record["reference"].update(CANMET_REFERENCE)
        cite = refs.get(a["ref"], "")
        record["reference"]["location_in_source"] = (
            f"Tables 1 and 2, data sheet {a['data_sheet']}; MRL report ref. {a['ref']}" + (f" ({cite})" if cite else "")
        )
        out.append(record)
    return tuple(out)


MNDOT_REFERENCE = {
    "type": "Report",
    "title": "Development of a Rock Strength Database (MnDOT report MN/RC 2018-19)",
    "author": "B. Folta, J. Sharpe, C. Hu, J. Labuz",
    "publisher": "Minnesota Department of Transportation / University of Minnesota",
    "year": 2018,
    "pages": "",
    "volume": "",
    "isbn": "",
    "edition": "",
}
MNDOT_METHOD = (
    "ASTM D2938 (UCS = peak load / original area), D3148 (E = slope of the axial stress-strain curve "
    "between 30 and 50 % of UCS), D2845 (P-wave velocity), D2664 (triaxial)."
)


def _hole(specimen_hole: str) -> str:
    import re

    match = re.match(r"^(SD-\d+|DBA-\d+[aA]?|IDH-\d+)", specimen_hole.strip())
    return match.group(1).upper() if match else specimen_hole.strip()


def _mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


@lru_cache(maxsize=None)
def mndot_records() -> tuple[dict, ...]:
    from .database import empty_record

    borings = {r["point_id"].strip().upper(): r for r in _csv("mndot_2018_borings.csv") if r["point_id"].strip()}
    groups: dict[str, list[dict]] = {}
    for row in _csv("mndot_2018_ucs.csv"):
        groups.setdefault(_hole(row["borehole"]), []).append(row)
    out = []
    for hole, rows in sorted(groups.items()):
        record = empty_record()
        record["origin"] = "builtin"
        record["rock_name"] = "Rock core, TH 53 (lithology not stated)"
        record["location"].update({"region": "North America", "country": "United States", "place": f"Minnesota, TH 53 relocation, borehole {hole}"})
        notes = [
            "Uniaxial tests on cores of the TH 53 highway relocation (United Taconite Thunderbird Mine expansion); "
            "the report calls the rock 'hard rock' and does not state its lithology.",
            MNDOT_METHOD,
        ]
        boring = borings.get(hole)
        if boring:
            notes.append(
                f"Table 4.1: UTM N {boring['utm_n']} / E {boring['utm_e']}, elevation {boring['elevation']} "
                "(coordinate system, zone and units not stated in the report; latitude/longitude not derived)."
            )
        specimens, used = [], []
        for r in rows:
            ucs, e = _num(r["ucs_mpa"]), _num(r["e_gpa"])
            doubtful = r["assigned_id"].strip() == "120"
            specimen = {
                "id": r["assigned_id"], "depth_ft": f"{r['depth_from_ft']}-{r['depth_to_ft']}",
                "density_g_cm3": _num(r["density_g_cm3"]), "vp_m_s": _num(r["vp_m_s"]),
                "e_gpa": e, "sigma3_mpa": 0.0 if ucs is not None else None, "sigma1_mpa": ucs,
                "note": (r["doubt"] or r["notes"] or "").strip(),
                "exclude": doubtful,
            }
            specimens.append(specimen)
            if ucs is not None and not doubtful:
                used.append(specimen)
            if doubtful:
                notes.append("Specimen 120: printed UCS 107.4 MPa / E 53.8 GPa disagree with the report's US-unit table and plot; excluded from the means.")
        record["specimens"] = specimens
        ucs_values = [s["sigma1_mpa"] for s in used]
        comp = {"test_type": "Uniaxial compression (laboratory)", "n_specimens": len(used)}
        if ucs_values:
            comp["ucs_mpa"] = _mean(ucs_values)
            comp["ucs_range_mpa"] = f"{min(ucs_values):g}-{max(ucs_values):g}"
        e_mean = _mean([s["e_gpa"] for s in used])
        if e_mean is not None:
            comp["e_mpa"] = round(e_mean * 1000.0, 1)
        diameters = [_num(r["diameter_mm"]) for r in rows]
        if _mean(diameters) is not None:
            comp["core_diameter_mm"] = _mean(diameters)
        record["tests"]["compression"] = comp
        density = _mean([s["density_g_cm3"] for s in used])
        if density is not None:
            record["density_mg_m3"] = density
            record["unit_weight_mn_m3"] = round(density * G / 1000.0, 5)
        vp = _mean([s["vp_m_s"] for s in used])
        if vp is not None:
            record["tests"]["velocity"] = {"vp_m_s": vp}
        notes.append(f"Means of {len(used)} specimens with valid UCS; individual specimens listed below.")
        record["notes"] = " ".join(notes)
        record["reference"].update(MNDOT_REFERENCE)
        record["reference"]["location_in_source"] = "Tables 4.1-4.4 (SI units), Appendix A (stress-strain plots)"
        out.append(record)

    # triaxial sets
    sets: dict[str, list[dict]] = {}
    for row in _csv("mndot_2018_triaxial.csv"):
        if row["table"] == "5.1/5.2":
            key = "Glenwood Shale" if "Glenwood" in row["formation_or_stratigraphy"] else "Platteville Formation"
        else:
            key = "Cretaceous sediments"
        sets.setdefault(key, []).append(row)
    places = {
        "Platteville Formation": ("SP2782-334, hole T06", "Tables 5.1-5.2"),
        "Glenwood Shale": ("SP2782-334, hole T06", "Tables 5.1-5.2"),
        "Cretaceous sediments": ("SP804-81", "Tables 5.3-5.4"),
    }
    for key, rows in sets.items():
        record = empty_record()
        record["origin"] = "builtin"
        record["rock_name"] = key + (" (rock type not stated)" if key == "Cretaceous sediments" else "")
        place, tables_ref = places[key]
        record["location"].update({"region": "North America", "country": "United States", "place": f"Minnesota, project {place} (location not stated)"})
        specimens = []
        for r in rows:
            specimens.append({
                "id": r["sample_id"], "group": r["group"], "member": r["member"],
                "depth_ft": f"{r['depth_from_ft']}-{r['depth_to_ft']}",
                "density_g_cm3": _num(r["density_g_cm3"]), "vp_m_s": _num(r["vp_m_s"]),
                "sigma3_mpa": _num(r["sigma3_mpa"]), "sigma1_mpa": _num(r["sigma1_mpa"]),
                "friction_deg_group": _num(r["friction_deg"]), "note": (r["doubt"] or "").strip(),
            })
        record["specimens"] = specimens
        s3 = [s["sigma3_mpa"] for s in specimens if s["sigma3_mpa"] is not None]
        record["tests"]["compression"] = {
            "test_type": "Triaxial compression (laboratory)",
            "n_specimens": len(specimens),
            "confining_stress_mpa": f"{min(s3):g}-{max(s3):g}" if s3 else "",
        }
        density = _mean([s["density_g_cm3"] for s in specimens])
        if density is not None:
            record["density_mg_m3"] = density
            record["unit_weight_mn_m3"] = round(density * G / 1000.0, 5)
        vp = _mean([s["vp_m_s"] for s in specimens])
        if vp is not None:
            record["tests"]["velocity"] = {"vp_m_s": vp}
        notes = [f"Individual triaxial tests (sigma3, sigma1) of {tables_ref}; use them as a failure state.", MNDOT_METHOD]
        if key == "Cretaceous sediments":
            notes.append(
                "Friction angles per group as printed (Table 5.4); the printed 52.1 deg of group 3 disagrees with its "
                "Fig. 5.5 fit (about 34.9 deg). Specimens 17 and 21: sigma3 = 0 because the confining pressure leaked."
            )
        else:
            notes.append("Members: " + ", ".join(sorted({s['member'] for s in specimens if s['member']})) + ".")
        record["notes"] = " ".join(notes)
        record["reference"].update(MNDOT_REFERENCE)
        record["reference"]["location_in_source"] = tables_ref + ", Appendices B-C (stress-strain plots)"
        out.append(record)
    return tuple(out)
