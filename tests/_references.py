# SPDX-License-Identifier: AGPL-3.0-or-later
"""Files of the private suite references (../Referencias) used by some tests.

Spec 027: the folders there are named after the programs they document, so
the tests find the files by searching for them instead of writing the path.
"""

from __future__ import annotations

from pathlib import Path

# the suite layout: Data/OGR-Data/tests -> Data/Referencias
REFERENCES = Path(__file__).resolve().parents[2] / "Referencias"


def roc_examples() -> Path:
    """Folder that holds the official .roc examples (the one with the most .roc files).

    Without the references it returns a folder that does not exist, so the
    tests that need the examples behave as they did with the old fixed path.
    """

    counts: dict[Path, int] = {}
    if REFERENCES.is_dir():
        for path in REFERENCES.rglob("*.roc"):
            counts[path.parent] = counts.get(path.parent, 0) + 1
    if not counts:
        return REFERENCES / "roc-examples-not-found"
    return max(counts, key=lambda folder: (counts[folder], str(folder)))
