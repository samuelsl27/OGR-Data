# SPDX-License-Identifier: AGPL-3.0-or-later
"""Alt accelerators for the menus (spec 025c).

Assigned by code once the menus are built, so both languages get one
without writing ``&`` into every translation: the first free letter that
starts a word, else any free letter, never repeated inside one menu. An
entry that already has one keeps it, so a second pass changes nothing and
a renamed entry (Undo "…", Recent Projects) can be marked again alone.
"""

from __future__ import annotations


def plain(text: str) -> str:
    """The text as shown: without the accelerator mark."""

    return text.replace("&&", "\0").replace("&", "").replace("\0", "&")


def _marked_letter(text: str) -> str | None:
    index = 0
    while True:
        index = text.find("&", index)
        if index < 0 or index + 1 >= len(text):
            return None
        if text[index + 1] == "&":
            index += 2
            continue
        return text[index + 1].lower()


def _candidates(text: str):
    """Positions to try: word initials first, then every other letter."""

    initials = [i for i, ch in enumerate(text) if ch.isalpha() and (i == 0 or not text[i - 1].isalnum())]
    others = [i for i, ch in enumerate(text) if ch.isalpha() and i not in initials]
    return initials + others


def assign(container) -> None:
    """Give every entry of a QMenu or QMenuBar (and its submenus) an accelerator."""

    actions = [a for a in container.actions() if not a.isSeparator() and a.text()]
    used = {letter for a in actions if (letter := _marked_letter(a.text()))}
    for action in actions:
        text = action.text()
        if _marked_letter(text) is None:
            for i in _candidates(text):
                if text[i].lower() not in used:
                    used.add(text[i].lower())
                    action.setText(text[:i] + "&" + text[i:])
                    break
        if action.menu() is not None:
            assign(action.menu())
