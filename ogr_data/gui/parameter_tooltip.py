# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tooltip of a material parameter: definition, unit, typical range, source (spec 025f RF-1)."""

from __future__ import annotations

import html

from ..core.numbers import symbols
from ..core.parameter_help import help_for
from . import i18n
from .i18n import tr


def parameter_tooltip(criterion: str, key: str, label: str, unit: str = "") -> str:
    """Rich-text tooltip, or "" if the parameter has no sourced help yet (see parameter_help.json, pending)."""

    entry = help_for(criterion, key)
    if entry is None:
        return ""
    language = i18n.current_language()
    lines = [f"<b>{html.escape(symbols(label))}</b>", html.escape(symbols(entry.definition.get(language, entry.definition["en"])))]
    if unit:
        lines.append(f"{tr('Unit')}: {html.escape(symbols(' ' + unit).strip())}")
    if entry.range:
        lines.append(f"{tr('Typical range')}: {html.escape(symbols(entry.range.get(language, entry.range.get('en', ''))))}")
    lines.append(f"{tr('Source')}: {html.escape('; '.join(entry.citations(language)))}")
    # <qt> makes Qt wrap the tooltip instead of one very long line
    return "<qt>" + "<br>".join(lines) + "</qt>"
