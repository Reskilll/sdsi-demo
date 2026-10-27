"""Sanitization helpers for untrusted input.

All user-controlled strings — user ids, SKUs, names, file paths — are treated
as untrusted.  Before they become dict *keys* they are cleaned for identity
(stripped of control characters, never truncated); before they are echoed into
``plan``, log, or ``result`` fields they are cleaned for safe *display*
(stripped + truncated).  Nothing from untrusted input is ever executed.
"""
from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

_IDENT_MAX = 128
_DISPLAY_MAX = 80


def clean_identifier(value: object, max_len: int = _IDENT_MAX) -> str:
    """Validate and clean a string used as a dict key.

    Strips control characters and surrounding whitespace, then truncates to
    ``max_len`` (generous — preserves identity for any realistic identifier
    while bounding memory).  Raises ``ValueError`` for non-strings or strings
    that become empty once cleaned.
    """
    if not isinstance(value, str):
        raise ValueError(f"expected a string, got {type(value).__name__}")
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    if not cleaned:
        raise ValueError("value must be a non-empty string after sanitization")
    return cleaned[:max_len]


def clean_display(value: object, max_len: int = _DISPLAY_MAX) -> str:
    """Clean and truncate a string for safe inclusion in plans, logs, or results.

    Never raises — non-strings are ``str()``-cast — so it is safe to call on
    any value when building an audit-friendly message.
    """
    text = value if isinstance(value, str) else str(value)
    return _CONTROL_CHARS.sub("", text).strip()[:max_len]