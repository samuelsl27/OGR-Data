"""Errors an operation raises on purpose, each with a stable code.

Same codes and wording rules as OGR-Slip2D's ``ogr_api.errors`` (same
owner; the suite shares the pattern): the reader is often a language
model, so every error says WHAT was wrong and, where possible, what to do
instead; an unknown name carries the closest known names.
"""

from __future__ import annotations

import difflib
from typing import Iterable


class OgrApiError(Exception):
    """Base class: ``[CODE] message Hint: hint``."""

    code = "E_INTERNAL"

    def __init__(self, message: str, *, hint: str | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" + (f" Hint: {self.hint}" if self.hint else "")

    def to_dict(self) -> dict:
        out = {"code": self.code, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        if self.details:
            out["details"] = self.details
        return out


class NotFound(OgrApiError):
    """A handle, name or index that does not exist."""

    code = "E_NOT_FOUND"


class InvalidArgument(OgrApiError):
    """A value of the wrong type, out of range, or not one of the choices."""

    code = "E_INVALID_ARGUMENT"


class Conflict(OgrApiError):
    """A valid request the current state does not allow."""

    code = "E_CONFLICT"


def internal_error(exc: BaseException) -> OgrApiError:
    """An exception no operation turned into an OgrApiError, with its type."""

    return OgrApiError(f"{type(exc).__name__}: {exc}")


def did_you_mean(word: str, options: Iterable[str], n: int = 3) -> str:
    opts = [str(o) for o in options]
    close = difflib.get_close_matches(str(word), opts, n=n, cutoff=0.55)
    if not close:
        lowered = {o.lower(): o for o in opts}
        close = [lowered[c] for c in difflib.get_close_matches(str(word).lower(), list(lowered), n=n, cutoff=0.55)]
    if not close:
        return ""
    if len(close) == 1:
        return f"Did you mean '{close[0]}'?"
    return "Did you mean " + ", ".join(f"'{c}'" for c in close[:-1]) + f" or '{close[-1]}'?"


def unknown(kind: str, word, options: Iterable[str]) -> NotFound:
    """NotFound for ``word`` among ``options``, with suggestions and the list."""

    options = [str(o) for o in options]
    hint = did_you_mean(str(word), options)
    listing = ", ".join(repr(o) for o in options[:40]) + ("" if len(options) <= 40 else f" (+{len(options) - 40} more)")
    return NotFound(f"Unknown {kind} {word!r}.", hint=(hint + " " if hint else "") + f"Known: {listing}.")


def choice(kind: str, value, options: Iterable[str]):
    """``value`` if it is one of ``options``; InvalidArgument with suggestions otherwise."""

    options = list(options)
    if value in options:
        return value
    hint = did_you_mean(str(value), options)
    raise InvalidArgument(f"{kind} must be one of {', '.join(repr(o) for o in options)}; got {value!r}.", hint=hint or None)
