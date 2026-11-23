"""Interface language (spec 024): English (reference) and Spanish.

``tr("English text")`` returns the text in the active language; English is
the key, so the English interface is exactly the text in the code. The
Spanish dictionaries live in ``es_<zone>.py`` (``ES = {...}``) and are
merged here; a key with two different translations is an error.

Same design as OGR-Slip2D's ``ogr_gui/i18n`` (pure-Python dictionaries,
no Qt Linguist). The core never imports this module: what the core labels
(criteria, parameters, test types, report sections) is translated here by
its English label.
"""

from __future__ import annotations

import importlib
from typing import Callable

LANGUAGES: dict[str, str] = {"en": "English", "es": "Español"}
ZONES = ("main", "dialogs", "estimation", "registry", "report", "history")

_LANG = "en"
_DICTS: dict[str, dict[str, str]] = {"en": {}}


def _load_spanish() -> dict[str, str]:
    merged: dict[str, str] = {}
    for zone in ZONES:
        try:
            module = importlib.import_module(f"{__name__}.es_{zone}")
        except ModuleNotFoundError:
            continue
        for key, value in module.ES.items():
            if key in merged and merged[key] != value:
                raise ValueError(f"i18n: {key!r} translated twice ({merged[key]!r} / {value!r})")
            merged[key] = value
    return merged


def spanish() -> dict[str, str]:
    if "es" not in _DICTS:
        _DICTS["es"] = _load_spanish()
    return _DICTS["es"]


def set_language(code: str) -> None:
    global _LANG
    if code not in LANGUAGES:
        raise ValueError(f"unknown language {code!r}")
    if code == "es":
        spanish()
    _LANG = code


def current_language() -> str:
    return _LANG


def tr(text: str) -> str:
    """``text`` (English) in the active language; English if there is no translation."""

    return _DICTS.get(_LANG, {}).get(text, text)


def translator(code: str | None = None) -> Callable[[str], str]:
    """A function translating into ``code`` (default: the active language), for the core (report)."""

    code = code or _LANG
    table = spanish() if code == "es" else {}
    return lambda text: table.get(text, text)


def system_default() -> str:
    """Spanish if the system language is Spanish, English otherwise (first start)."""

    from PySide6.QtCore import QLocale

    return "es" if QLocale.system().name().lower().startswith("es") else "en"


def saved_language(settings) -> str:
    code = settings.value("language", None)
    return str(code) if code in LANGUAGES else system_default()


_QT_TRANSLATOR = None


def install_qt_translator(app, code: str) -> None:
    """Qt's own texts (OK / Cancel, Save / Discard, line-edit menus) in the language."""

    global _QT_TRANSLATOR
    from PySide6.QtCore import QLibraryInfo, QTranslator

    if _QT_TRANSLATOR is not None:
        app.removeTranslator(_QT_TRANSLATOR)
        _QT_TRANSLATOR = None
    if code == "en":
        return
    translator_ = QTranslator(app)
    if translator_.load(f"qtbase_{code}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(translator_)
        _QT_TRANSLATOR = translator_
