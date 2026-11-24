# SPDX-License-Identifier: AGPL-3.0-or-later
"""Help of every material parameter, with its sources (spec 025f RF-1).

``ogr_data/data/parameter_help.json`` holds, per parameter, a short
definition in English and Spanish, the typical range when a source gives
one, and the bibliographic sources (with the page, table or equation in
``locator``). It was written from the documents of the suite bibliography;
what no reliable source could support is listed under ``pending`` with what
is missing, instead of being invented.

The core does not know languages: it returns both texts and the interface
picks one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class ParameterHelp:
    key: str
    criteria: tuple[str, ...]
    definition: dict[str, str]  # language -> text
    range: dict[str, str]  # language -> text; empty when no source gives one
    source_ids: tuple[str, ...]
    locator: str

    @property
    def sources(self) -> tuple[str, ...]:
        """Short citations in English ("Hoek et al. (2002)")."""

        return self.citations("en")

    def citations(self, language: str) -> tuple[str, ...]:
        """Short citations in ``language`` (a deduction says so in each language)."""

        return tuple(short_citation(s, language) for s in self.source_ids)

    @property
    def deduced(self) -> bool:
        """True if part of the entry is deduced by OGR Data rather than read in a source."""

        return DEDUCTION in self.source_ids


@lru_cache(maxsize=1)
def _data() -> dict:
    text = resources.files("ogr_data.data").joinpath("parameter_help.json").read_text(encoding="utf-8")
    return json.loads(text)


#: Source id of what OGR Data deduced from the model's equations or the program
#: itself because no published source was found (allowed by the owner, 2026-11-24).
DEDUCTION = "ogr_deduction"


def short_citation(source_id: str, language: str = "en") -> str:
    source = _data()["sources"][source_id]
    if language != "en" and source.get(f"short_{language}"):
        return source[f"short_{language}"]
    return source.get("short") or source["citation"]


def sources() -> dict[str, dict]:
    return dict(_data()["sources"])


def entries() -> list[ParameterHelp]:
    out = []
    for raw in _data()["parameters"]:
        out.append(ParameterHelp(
            key=raw["key"],
            criteria=tuple(raw["criteria"]),
            definition={"en": raw["definition_en"], "es": raw["definition_es"]},
            range={k: v for k, v in (("en", raw.get("range_en")), ("es", raw.get("range_es"))) if v},
            source_ids=tuple(raw["sources"]),
            locator=raw.get("locator", ""),
        ))
    return out


def pending() -> list[dict]:
    return list(_data().get("pending", []))


def help_for(criterion: str, key: str) -> ParameterHelp | None:
    """The help of ``key`` in ``criterion``: the entry for that criterion, else the general one ("*")."""

    general = None
    for entry in entries():
        if entry.key != key:
            continue
        if criterion in entry.criteria:
            return entry
        if "*" in entry.criteria:
            general = entry
    return general
