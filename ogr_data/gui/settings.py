# SPDX-License-Identifier: AGPL-3.0-or-later
"""The program's saved settings (theme, stress unit, language, window state).

Every ``QSettings`` of OGR Data comes from :func:`app_settings` (spec 025b).
It uses the application-wide default format: the native store on a normal
start (the Windows registry, as before), and whatever the test runner sets
— an INI file in a temporary folder — so the suite never writes the user's
settings.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORGANIZATION = "OpenGeoRock"
APPLICATION = "OGR-Data"


def app_settings() -> QSettings:
    return QSettings(QSettings.defaultFormat(), QSettings.Scope.UserScope, ORGANIZATION, APPLICATION)


def isolate_for_tests(folder: str) -> None:
    """Send every later :func:`app_settings` to an INI file under ``folder``."""

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, folder)
