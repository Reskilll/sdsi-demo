"""Loading and strict validation of policy, holiday and ticket files.

Config problems (policy/holidays/unreadable files) are fatal ``ConfigError``s.
Individual bad tickets are collected as ``TicketError``s so one malformed
record never hides the results for the rest.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .models import (
    INITIAL_STATUS,
    ConfigError,
    SlaPolicy,
    StatusEvent,
    Ticket,
    TicketError,
)
from .timeutil import parse_timestamp, parse_timezone

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_HISTORY_EVENTS = 10_000
MAX_HOLIDAYS = 10_000
MAX_TARGET_HOURS = 24 * 365

DEFAULT_TARGETS_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}
DEFAULT_RUNNING = ("NEW", "OPEN", "ASSIGNED", "IN_PROGRESS", "REOPENED")
DEFAULT_PAUSED = ("ON_HOLD",)
DEFAULT_STOPPED = ("RESOLVED", "CLOSED")
DEFAULT_WORKING_DAYS = ("MON", "TUE", "WED", "THU", "FRI")

_DAY_INDEX = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_STATUS_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_MAX_GROUP_LEN = 100


# --------------------------------------------------------------------------- files
def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-standard JSON constant {name}")


def read_json(path: str | Path) -> Any:
    """Read a JSON file with size limits and user-safe error messages."""
    p = Path(path)
    label = p.name or str(path)
    try:
        if not p.is_file():
            raise ConfigError(f"input file not found: {label}")
        if p.stat().st_size > MAX_FILE_BYTES:
            raise ConfigError(f"{label}: file exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB limit")
        text = p.read_text(encoding="utf-8-sig")
        return json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno}") from None
    except UnicodeDecodeError:
        raise ConfigError(f"{label}: file is not valid UTF-8") from None
    except (ValueError, RecursionError) as exc:
        raise ConfigError(f"{label}: unsupported JSON content ({type(exc).__name__})") from None
    except OSError:
        raise ConfigError(f"{label}: file could not be read") from None


# --------------------------------------------------------------------------- policy
def _parse_hhmm(value: object, field: str) -> time:
    if not isinstance(value, str) or not _HHMM_RE.match(value):
        raise ConfigError(f"{field} must be 'HH:MM' (24h)")
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def _status_set(value: object, field: str) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{field} must be a non-empty list of status names")
    out = set()
    for item in value:
        if not isinstance(item, str) or not _STATUS_RE.match(item.strip().upper()):
            raise ConfigError(f"{field} contains an invalid status name")
        out.add(item.strip().upper())
    return frozenset(out)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_policy(data: object) -> SlaPolicy:
    if not isinstance(data, dict):
        raise ConfigError("policy must be a JSON object")

    tz_name = data.get("timezone", "UTC")
    tz = parse_timezone(tz_name)

    hours = data.get("business_hours", {"start": "09:00", "end": "18:00"})
    if not isinstance(hours, dict):
        raise ConfigError("business_hours must be an object with 'start' and 'end'")
    day_start = _parse_hhmm(hours.get("start"), "business_hours.start")
    day_end = _parse_hhmm(hours.get("end"), "business_hours.end")
    if day_start >= day_end:
        raise ConfigError("business_hours.start must be before business_hours.end")

    days_raw = data.get("working_days", list(DEFAULT_WORKING_DAYS))
    if not isinstance(days_raw, list) or not days_raw:
        raise ConfigError("working_days must be a non-empty list like ['MON', 'TUE']")
    try:
        working_days = frozenset(_DAY_INDEX[str(d).strip().upper()[:3]] for d in days_raw)
    except KeyError:
        raise ConfigError("working_days contains an unknown day name") from None

    targets_raw = data.get("targets_hours", DEFAULT_TARGETS_HOURS)
    if not isinstance(targets_raw, dict) or not targets_raw:
        raise ConfigError("targets_hours must be a non-empty object, e.g. {'P1': 4}")
    targets: dict[str, int] = {}
    for key, hours_value in targets_raw.items():
        name = str(key).strip().upper()
        if not _STATUS_RE.match(name):
            raise ConfigError("targets_hours has an invalid priority name")
        if not _is_number(hours_value) or not 0 < hours_value <= MAX_TARGET_HOURS:
            raise ConfigError(f"targets_hours.{name} must be a number in (0, {MAX_TARGET_HOURS}]")
        minutes = round(hours_value * 60)
        if minutes < 1:
            raise ConfigError(f"targets_hours.{name} must be at least one minute")
        targets[name] = minutes

    running = _status_set(data.get("running_statuses", list(DEFAULT_RUNNING)), "running_statuses")
    running |= {INITIAL_STATUS}
    paused = _status_set(data.get("paused_statuses", list(DEFAULT_PAUSED)), "paused_statuses")
    stopped = _status_set(data.get("stopped_statuses", list(DEFAULT_STOPPED)), "stopped_statuses")
    if running & paused or running & stopped or paused & stopped:
        raise ConfigError("running/paused/stopped status lists must not overlap")

    ratio = data.get("at_risk_ratio", 0.8)
    if not _is_number(ratio) or not 0 < ratio <= 1:
        raise ConfigError("at_risk_ratio must be a number in (0, 1]")

    return SlaPolicy(
        timezone=tz,
        timezone_name=str(tz_name).strip(),
        day_start=day_start,
        day_end=day_end,
        working_days=working_days,
        targets_minutes=MappingProxyType(dict(sorted(targets.items()))),
        running_statuses=running,
        paused_statuses=paused,
        stopped_statuses=stopped,
        at_risk_ratio=float(ratio),
    )


# --------------------------------------------------------------------------- holidays
def parse_holidays(data: object) -> frozenset[date]:
    """Accept ``[...]`` or ``{"holidays": [...]}``; items are 'YYYY-MM-DD' or {"date": ...}."""
    items = data.get("holidays") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ConfigError("holidays must be a list (or an object with a 'holidays' list)")
    if len(items) > MAX_HOLIDAYS:
        raise ConfigError(f"too many holidays (max {MAX_HOLIDAYS})")
    out = set()
    for idx, item in enumerate(items):
        raw = item.get("date") if isinstance(item, dict) else item
        if not isinstance(raw, str) or len(raw) != 10:
            raise ConfigError(f"holidays[{idx}] must be a 'YYYY-MM-DD' date")
        try:
            out.add(date.fromisoformat(raw))
        except ValueError:
            raise ConfigError(f"holidays[{idx}] is not a valid date: {raw!r}") from None
    return frozenset(out)


# --------------------------------------------------------------------------- tickets
def _ticket_ref(raw: object, idx: int) -> str:
    if isinstance(raw, dict):
        tid = raw.get("id")
        if isinstance(tid, (str, int)) and not isinstance(tid, bool) and _ID_RE.match(str(tid)):
            return str(tid)
    return f"#{idx}"


def _parse_ticket(raw: object, policy: SlaPolicy, as_of: datetime) -> Ticket:
    if not isinstance(raw, dict):
        raise ValueError("ticket must be a JSON object")

    tid = raw.get("id")
    if isinstance(tid, int) and not isinstance(tid, bool):
        tid = str(tid)
    if not isinstance(tid, str) or not _ID_RE.match(tid):
        raise ValueError("id is required: 1-64 chars of [A-Za-z0-9._:-]")

    priority = raw.get("priority")
    if not isinstance(priority, str) or priority.strip().upper() not in policy.targets_minutes:
        allowed = ", ".join(policy.targets_minutes)
        raise ValueError(f"priority {str(priority)[:16]!r} is not one of: {allowed}")
    priority = priority.strip().upper()

    group = raw.get("assignee_group")
    if group is None or (isinstance(group, str) and not group.strip()):
        group = "UNASSIGNED"
    if not isinstance(group, str) or len(group.strip()) > _MAX_GROUP_LEN or not group.isprintable():
        raise ValueError(f"assignee_group must be printable text up to {_MAX_GROUP_LEN} chars")
    group = group.strip()

    created = parse_timestamp(raw.get("created_at"), policy.timezone, "created_at")
    if created > as_of:
        raise ValueError("created_at is after the evaluation time (as_of)")

    history_raw = raw.get("status_history", [])
    if not isinstance(history_raw, list):
        raise ValueError("status_history must be a list")
    if len(history_raw) > MAX_HISTORY_EVENTS:
        raise ValueError(f"status_history exceeds {MAX_HISTORY_EVENTS} events")

    events = []
    for j, ev in enumerate(history_raw):
        if not isinstance(ev, dict):
            raise ValueError(f"status_history[{j}] must be an object")
        status = ev.get("status")
        status = status.strip().upper() if isinstance(status, str) else None
        if status not in policy.known_statuses:
            raise ValueError(f"status_history[{j}].status is not a known status")
        at = parse_timestamp(ev.get("at"), policy.timezone, f"status_history[{j}].at")
        if at < created:
            raise ValueError(f"status_history[{j}].at is before created_at")
        events.append(StatusEvent(status, at))
    events.sort(key=lambda e: e.at)  # stable: equal timestamps keep file order

    return Ticket(tid, priority, group, created, tuple(events))


def parse_tickets(
    data: object, policy: SlaPolicy, as_of: datetime
) -> tuple[list[Ticket], list[TicketError]]:
    items = data.get("tickets") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ConfigError("tickets must be a list (or an object with a 'tickets' list)")
    tickets: list[Ticket] = []
    errors: list[TicketError] = []
    seen: set[str] = set()
    for idx, raw in enumerate(items):
        ref = _ticket_ref(raw, idx)
        try:
            ticket = _parse_ticket(raw, policy, as_of)
        except ValueError as exc:
            errors.append(TicketError(ref, str(exc)))
            continue
        if ticket.ticket_id in seen:
            errors.append(TicketError(f"{ref} (#{idx})", "duplicate ticket id"))
            continue
        seen.add(ticket.ticket_id)
        tickets.append(ticket)
    return tickets, errors


# --------------------------------------------------------------------------- facade
def load_policy(path: str | Path) -> SlaPolicy:
    return parse_policy(read_json(path))


def load_holidays(path: str | Path | None) -> frozenset[date]:
    return frozenset() if path is None else parse_holidays(read_json(path))


def load_tickets(
    path: str | Path, policy: SlaPolicy, as_of: datetime
) -> tuple[list[Ticket], list[TicketError]]:
    return parse_tickets(read_json(path), policy, as_of)

