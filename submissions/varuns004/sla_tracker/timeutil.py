"""Timezone and timestamp parsing at the I/O boundary.

Internally every datetime is naive local wall-clock time in the policy zone.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import ConfigError

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_MAX_TS_LEN = 40


def parse_timezone(value: object) -> tzinfo:
    """Accept 'UTC', a fixed offset like '+05:30', or an IANA name."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("policy.timezone must be a non-empty string")
    name = value.strip()
    if name.upper() in {"UTC", "Z"}:
        return timezone.utc
    match = _OFFSET_RE.match(name)
    if match:
        sign, hh, mm = match.groups()
        hours, minutes = int(hh), int(mm)
        if hours > 14 or minutes > 59:
            raise ConfigError(f"invalid UTC offset {name!r}")
        delta = timedelta(hours=hours, minutes=minutes)
        return timezone(-delta if sign == "-" else delta)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigError(
            f"unknown timezone {name[:40]!r}: use an offset like '+05:30' or an "
            "IANA name (on Windows IANA names need `pip install tzdata`)"
        ) from None


def parse_timestamp(value: object, tz: tzinfo, field: str) -> datetime:
    """Parse ISO-8601 into naive local time in ``tz``.

    Naive inputs are interpreted as already being in ``tz``. Sub-second
    precision is dropped so all arithmetic is in whole seconds.
    """
    if not isinstance(value, str) or not value or len(value) > _MAX_TS_LEN:
        raise ValueError(f"{field} must be an ISO-8601 timestamp string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} is not a valid ISO-8601 timestamp: {value!r}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz).replace(tzinfo=None, microsecond=0)


def to_iso(local: datetime, tz: tzinfo) -> str:
    return local.replace(tzinfo=tz).isoformat()

