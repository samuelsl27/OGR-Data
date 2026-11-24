# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 027 / rule 9 of AGENTS.md: the vendor of the reference program and
its products are named nowhere in the repository.

The only exceptions are the rule itself (AGENTS.md, spec 027), the format
tag that a .roc file starts with, which the importer has to compare, and
the patterns of the tests that enforce the rule (lines marked ``rule 9:``).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = re.compile(r"rocscience|rocdata|roc\s?data|rsdata|rocprop|rocplane|rocsupport|\brs2\b|\brs3\b|\bslide\s?[23]\b", re.I)  # rule 9: pattern
EXEMPT_FILES = {"AGENTS.md"}
EXEMPT_DIRS = ("spec/features/027-",)
EXEMPT_MARK = "rule 9:"
TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".txt", ".csv", ".cfg", ".ini", ".yml", ".yaml", ".html", ".bat", ""}


def _tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if line]


def test_no_vendor_name_in_the_repository() -> None:
    hits = []
    for path in _tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in EXEMPT_FILES or rel.startswith(EXEMPT_DIRS) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if VENDOR.search(line) and EXEMPT_MARK not in line:
                hits.append(f"{rel}:{number}: {line.strip()[:100]}")
    assert not hits, f"{len(hits)} lines:\n" + "\n".join(hits[:60])
