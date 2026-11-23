# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 025b: the main window with the results in view.

T1 — the suite never writes the user's settings. Before 025b the tests
wrote theme, stress unit and language into the real
``HKCU\\Software\\OpenGeoRock\\OGR-Data`` (rule 5 of AGENTS.md), and 025b
adds the saved window state. Invariants:

- every ``QSettings`` of the program comes from ``gui.settings.app_settings``;
- under ``tests/_runner.py`` that is an INI file in a temporary folder,
  never the registry (these tests only hold under the runner).
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_suite_settings_live_in_a_temporary_ini_file() -> None:
    from PySide6.QtCore import QSettings

    from ogr_data.gui.settings import app_settings

    settings = app_settings()
    assert settings.format() == QSettings.Format.IniFormat
    path = Path(settings.fileName()).resolve()
    assert path.is_relative_to(Path(tempfile.gettempdir()).resolve()), path
    assert "HKEY" not in settings.fileName()


def test_main_window_uses_the_program_settings() -> None:
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.main_window import MainWindow
    from ogr_data.gui.settings import app_settings

    QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert w._settings.fileName() == app_settings().fileName()
    finally:
        w.deleteLater()


def test_no_settings_are_built_anywhere_else() -> None:
    """A QSettings built by hand would go back to the registry."""

    offenders = []
    for folder in ("ogr_data", "tests"):
        for path in (ROOT / folder).rglob("*.py"):
            if path.name == "settings.py" and path.parent.name == "gui":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if name == "QSettings":
                        offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not offenders, offenders
