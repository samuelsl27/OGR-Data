"""Material properties database (spec 010), the OGR equivalent of RocProp.

Same record model as Rocscience's RocProp (captures 36-37 of the RSData
analysis): rock name and prefix, unit weight, fabric, notes; location
(region, country, town/city/state, latitude, longitude, depth); reference
(type, title, author, publisher, year, pages, volume, ISBN, edition); and
test data blocks Compression, Tensile, Hoek-Brown and Velocity, each with
an Information Quality (1-10).

The RocProp data are proprietary and are NOT used. OGR's built-in records
are generated from the sourced tables of the program (Hoek's mi table,
the MR table of Practical Rock Engineering 2023 and the field estimates of
UCS); user records live in a separate JSON file. Every record needs a
reference: a record without source is not saved.

Search (as RocProp): key words must all match (AND), case-insensitive;
a plain word matches whole words, "*" matches any characters inside a
word (gran* -> granite, granodiorite), "double quotes" match an exact
phrase.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable

from . import tables

FORMAT = "ogr-data-materials-db/1"
PAGE_SIZE = 14  # RocProp shows 14 results per page

TEST_BLOCKS = ("compression", "tensile", "hoek_brown", "velocity")
TEST_LABELS = {"compression": "Compression", "tensile": "Tensile", "hoek_brown": "Hoek-Brown", "velocity": "Velocity"}

# fields of each block (key, label, unit); all optional
COMPRESSION_FIELDS = (
    ("test_type", "Test Type", ""),
    ("core_diameter_mm", "Core Diameter", "mm"),
    ("core_length_mm", "Core Length", "mm"),
    ("confining_stress_mpa", "Confining Stress", "MPa"),
    ("angle_to_fabric_deg", "Angle to Fabric Normal", "deg"),
    ("ucs_mpa", "Compressive Strength", "MPa"),
    ("ucs_range_mpa", "Compressive Strength range", "MPa"),
    ("e50_mpa", "Young's Modulus, Tangent at 50%", "MPa"),
    ("poisson", "Poisson Ratio", ""),
    ("information_quality", "Information Quality (1-10)", ""),
)
TENSILE_FIELDS = (
    ("test_type", "Test Type", ""),
    ("tensile_strength_mpa", "Tensile Strength", "MPa"),
    ("information_quality", "Information Quality (1-10)", ""),
)
HOEK_BROWN_FIELDS = (
    ("sigci_mpa", "sigci", "MPa"),
    ("mi", "mi", ""),
    ("mi_std", "mi ±", ""),
    ("modulus_ratio", "Modulus ratio MR (Ei/sigci)", ""),
    ("information_quality", "Information Quality (1-10)", ""),
)
VELOCITY_FIELDS = (
    ("vp_m_s", "P-wave velocity", "m/s"),
    ("vs_m_s", "S-wave velocity", "m/s"),
    ("information_quality", "Information Quality (1-10)", ""),
)
BLOCK_FIELDS = {
    "compression": COMPRESSION_FIELDS,
    "tensile": TENSILE_FIELDS,
    "hoek_brown": HOEK_BROWN_FIELDS,
    "velocity": VELOCITY_FIELDS,
}
LOCATION_FIELDS = (
    ("region", "Region"), ("country", "Country"), ("place", "Town/City/State"),
    ("latitude", "Latitude"), ("longitude", "Longitude"), ("depth_m", "Depth (m)"),
)
REFERENCE_FIELDS = (
    ("type", "Reference Type"), ("title", "Title"), ("author", "Author"), ("publisher", "Publisher"),
    ("year", "Year Published"), ("pages", "Pages"), ("volume", "Volume"), ("isbn", "ISBN"), ("edition", "Edition"),
    ("location_in_source", "Table / figure"),
)


def empty_record() -> dict[str, Any]:
    return {
        "record_id": None,
        "origin": "user",
        "rock_name": "",
        "rock_name_prefix": "",
        "unit_weight_mn_m3": None,
        "fabric": "",
        "notes": "",
        "location": {key: "" for key, _ in LOCATION_FIELDS},
        "reference": {key: "" for key, _ in REFERENCE_FIELDS},
        "tests": {},
    }


def validate(record: dict) -> None:
    """A record needs a rock name and a reference (title and author)."""

    if not str(record.get("rock_name", "")).strip():
        raise ValueError("the record needs a rock name")
    ref = record.get("reference") or {}
    if not str(ref.get("title", "")).strip() or not str(ref.get("author", "")).strip():
        raise ValueError("a record without source is not saved: enter the reference title and author")
    quality = [b.get("information_quality") for b in record.get("tests", {}).values()]
    for q in quality:
        if q not in (None, "") and not 1 <= float(q) <= 10:
            raise ValueError("Information Quality must be between 1 and 10")


def available_tests(record: dict) -> list[str]:
    tests = record.get("tests", {})
    return [TEST_LABELS[k] for k in TEST_BLOCKS if any(v not in (None, "") for v in tests.get(k, {}).values())]


def title(record: dict) -> str:
    """RocProp-style headline: "Granite, Canada, Blue Beach North, Newfoundland"."""

    loc = record.get("location", {})
    parts = [record.get("rock_name_prefix", "") + " " + record.get("rock_name", "")]
    parts += [loc.get("country", ""), loc.get("place", "")]
    return ", ".join(p.strip() for p in parts if str(p).strip())


# ---------------------------------------------------------------- search


def _terms(query: str) -> list[str]:
    phrases = re.findall(r'"([^"]+)"', query)
    rest = re.sub(r'"[^"]*"', " ", query)
    return [p.strip() for p in phrases if p.strip()] + rest.split()


def _pattern(term: str) -> re.Pattern:
    words = term.split()
    pieces = []
    for word in words:
        pieces.append(r"\w*".join(re.escape(part) for part in word.split("*")))
    body = r"\s+".join(pieces)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def _haystack(record: dict) -> str:
    loc = record.get("location", {})
    ref = record.get("reference", {})
    fields = [
        record.get("rock_name", ""), record.get("rock_name_prefix", ""), record.get("fabric", ""), record.get("notes", ""),
        *(str(loc.get(k, "")) for k, _ in LOCATION_FIELDS),
        ref.get("title", ""), ref.get("author", ""), ref.get("publisher", ""), str(ref.get("year", "")),
    ]
    return " | ".join(str(f) for f in fields if f)


def matches(record: dict, query: str) -> bool:
    text = _haystack(record)
    return all(_pattern(term).search(text) for term in _terms(query))


# --------------------------------------------------------------- storage


class MaterialDatabase:
    """Built-in records (read-only) + user records (JSON file)."""

    def __init__(self, user_path: str | Path | None = None, builtin: Iterable[dict] | None = None) -> None:
        self.user_path = Path(user_path) if user_path else None
        self.builtin = [copy.deepcopy(r) for r in (builtin if builtin is not None else builtin_records())]
        self.user: list[dict] = []
        if self.user_path and self.user_path.exists():
            data = json.loads(self.user_path.read_text(encoding="utf-8"))
            if data.get("format") != FORMAT:
                raise ValueError(f"unsupported materials database {data.get('format')!r}")
            self.user = list(data.get("records", []))

    @property
    def records(self) -> list[dict]:
        return self.builtin + self.user

    def get(self, record_id: int) -> dict | None:
        return next((r for r in self.records if r.get("record_id") == record_id), None)

    def search(self, query: str = "") -> list[dict]:
        query = query.strip()
        return [r for r in self.records if not query or matches(r, query)]

    @staticmethod
    def page(results: list[dict], page: int, size: int = PAGE_SIZE) -> list[dict]:
        return results[page * size:(page + 1) * size]

    @staticmethod
    def page_count(results: list[dict], size: int = PAGE_SIZE) -> int:
        return max(1, -(-len(results) // size))

    def _next_id(self) -> int:
        return max([r.get("record_id") or 0 for r in self.records] + [0]) + 1

    def save_record(self, record: dict) -> dict:
        """Add or update a user record (validated); returns the stored record."""

        validate(record)
        record = copy.deepcopy(record)
        if record.get("origin") == "builtin" or any(r.get("record_id") == record.get("record_id") for r in self.builtin):
            raise ValueError("built-in records are read-only: use Copy to New Record")
        record["origin"] = "user"
        if record.get("record_id") is None:
            record["record_id"] = self._next_id()
            self.user.append(record)
        else:
            index = next((i for i, r in enumerate(self.user) if r["record_id"] == record["record_id"]), None)
            if index is None:
                self.user.append(record)
            else:
                self.user[index] = record
        self._write()
        return record

    def delete(self, record_id: int) -> None:
        if any(r.get("record_id") == record_id for r in self.builtin):
            raise ValueError("built-in records cannot be deleted")
        self.user = [r for r in self.user if r.get("record_id") != record_id]
        self._write()

    def _write(self) -> None:
        if self.user_path is None:
            return
        self.user_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"format": FORMAT, "records": self.user}
        self.user_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------- conversions


def to_material_parameters(record: dict) -> dict:
    """GHB parameters (kPa) from a record: sigci (Hoek-Brown block or UCS) and mi."""

    hb = record.get("tests", {}).get("hoek_brown", {})
    comp = record.get("tests", {}).get("compression", {})
    params = {}
    sigci = hb.get("sigci_mpa") if hb.get("sigci_mpa") not in (None, "") else comp.get("ucs_mpa")
    if sigci not in (None, ""):
        params["sigci"] = float(sigci) * 1000.0
    if hb.get("mi") not in (None, ""):
        params["mi"] = float(hb["mi"])
        params["mi_residual"] = float(hb["mi"])
    if not params:
        raise ValueError("the record has no sigci / UCS or mi to use")
    return params


def clipboard_text(record: dict) -> str:
    """Tab-separated listing of a record (RocProp "Copy to Clipboard")."""

    lines = [f"Record ID\t{record.get('record_id')}", f"Rock Name\t{record.get('rock_name', '')}"]
    for key, label in (("rock_name_prefix", "Rock Name Prefix"), ("unit_weight_mn_m3", "Unit Weight (MN/m3)"), ("fabric", "Fabric"), ("notes", "Notes")):
        if record.get(key) not in (None, ""):
            lines.append(f"{label}\t{record[key]}")
    for key, label in LOCATION_FIELDS:
        value = record.get("location", {}).get(key)
        if value not in (None, ""):
            lines.append(f"{label}\t{value}")
    for key, label in REFERENCE_FIELDS:
        value = record.get("reference", {}).get(key)
        if value not in (None, ""):
            lines.append(f"{label}\t{value}")
    for block in TEST_BLOCKS:
        data = record.get("tests", {}).get(block, {})
        for key, label, unit in BLOCK_FIELDS[block]:
            if data.get(key) not in (None, ""):
                lines.append(f"{TEST_LABELS[block]}: {label}{f' ({unit})' if unit else ''}\t{data[key]}")
    return "\n".join(lines)


# ------------------------------------------------------- built-in records


def builtin_records() -> list[dict]:
    """Records generated from the sourced tables of OGR-Data."""

    out: list[dict] = []
    mi = tables.mi_values()
    mr = {v["rock"].lower(): v for v in tables.modulus_ratio()["values"]}
    mr_source = tables.modulus_ratio()["source"]
    for v in mi["values"]:
        record = empty_record()
        record["origin"] = "builtin"
        record["rock_name"] = v["rock"]
        record["fabric"] = v["texture"] or ""
        record["notes"] = ", ".join(x for x in (v["rock_type"], v["class"], v["group"]) if x)
        hb = {"mi": float(v["mi"]), "mi_std": float(v["std"])}
        if v["estimated"]:
            record["notes"] += "; mi estimated (in brackets in the source table)"
        ratio = mr.get(v["rock"].lower())
        ref_title = "Practical Rock Engineering, chapter 11: Rock mass properties"
        where = "Table 3: values of the constant mi for intact rock"
        if ratio is not None:
            hb["modulus_ratio"] = f'{ratio["mr_lo"]:g}' + ("" if ratio["mr_hi"] is None else f'-{ratio["mr_hi"]:g}')
            where += "; MR: Practical Rock Engineering (2023) Figure 13"
        record["tests"]["hoek_brown"] = hb
        record["reference"].update({"type": "Book section", "title": ref_title, "author": "E. Hoek", "publisher": "Rocscience", "location_in_source": where})
        out.append(record)
    grades = tables.rock_strength_grades()
    for g in grades["grades"]:
        record = empty_record()
        record["origin"] = "builtin"
        record["rock_name"] = f'Field estimate {g["grade"]} ({g["term"]})'
        record["notes"] = f'{g["field_estimate"]}. Examples: {g["examples"]}.'
        hi = g["ucs_hi_mpa"]
        record["tests"]["compression"] = {
            "test_type": "Field estimate",
            "ucs_mpa": g["ucs_pick_mpa"],
            "ucs_range_mpa": f'{g["ucs_lo_mpa"]:g}-{hi:g}' if hi else f'>{g["ucs_lo_mpa"]:g}',
        }
        record["reference"].update({
            "type": "Book section", "title": "Practical Rock Engineering, chapter 11: Rock mass properties",
            "author": "E. Hoek", "publisher": "Rocscience",
            "location_in_source": "Table 2: field estimates of uniaxial compressive strength (grades after Brown 1981)",
        })
        out.append(record)
    for i, record in enumerate(out, start=1):
        record["record_id"] = i
    return out
