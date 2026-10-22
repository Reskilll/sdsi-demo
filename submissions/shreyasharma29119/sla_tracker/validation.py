"""Input validation and parsing for all JSON input files."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from .models import SlaPolicy, StatusEntry, Ticket

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _require_str(obj: dict[str, Any], key: str, context: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str):
        raise ValueError(f"{context}: '{key}' must be a string, got {type(val).__name__}")
    return val


def _require_datetime(obj: dict[str, Any], key: str, context: str) -> datetime:
    raw = _require_str(obj, key, context)
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{context}: '{key}' invalid ISO datetime '{raw}'") from exc


def _require_optional_datetime(
    obj: dict[str, Any], key: str, context: str
) -> datetime | None:
    if key not in obj or obj[key] is None:
        return None
    return _require_datetime(obj, key, context)


# ---------------------------------------------------------------------------
# public validators
# ---------------------------------------------------------------------------


def parse_tickets(raw: list[dict[str, Any]]) -> list[Ticket]:
    """Parse and validate a list of ticket dicts into Ticket objects."""
    tickets: list[Ticket] = []
    for i, item in enumerate(raw):
        ctx = f"tickets[{i}]"
        if not isinstance(item, dict):
            raise ValueError(f"{ctx}: expected object, got {type(item).__name__}")

        tid = _require_str(item, "id", ctx)
        priority = _require_str(item, "priority", ctx).upper()
        group = _require_str(item, "assignee_group", ctx)
        created = _require_datetime(item, "created", ctx)
        resolved = _require_optional_datetime(item, "resolved", ctx)

        # Validate status_history
        history: list[StatusEntry] = []
        for j, entry in enumerate(item.get("status_history", [])):
            hctx = f"{ctx}.status_history[{j}]"
            if not isinstance(entry, dict):
                raise ValueError(f"{hctx}: expected object")
            status = _require_str(entry, "status", hctx)
            at = _require_datetime(entry, "at", hctx)
            history.append(StatusEntry(status=status, at=at))

        if resolved is not None and resolved < created:
            raise ValueError(
                f"{ctx}: resolved '{resolved}' is before created '{created}'"
            )

        tickets.append(
            Ticket(
                id=tid,
                priority=priority,
                assignee_group=group,
                created=created,
                resolved=resolved,
                status_history=history,
            )
        )
    return tickets


def parse_policy(raw: dict[str, Any]) -> SlaPolicy:
    """Parse and validate SLA policy JSON into an SlaPolicy object."""
    if not isinstance(raw, dict):
        raise ValueError("sla_policy: expected object")

    # -- priorities -----------------------------------------------------------
    priorities = raw.get("priorities")
    if not isinstance(priorities, dict):
        raise ValueError("sla_policy.priorities: expected object")

    targets: dict[str, int] = {}
    for pri, val in priorities.items():
        if not isinstance(val, dict):
            raise ValueError(f"sla_policy.priorities.{pri}: expected object")
        hours = val.get("target_hours")
        if not isinstance(hours, (int, float)):
            raise ValueError(
                f"sla_policy.priorities.{pri}.target_hours: expected number"
            )
        targets[pri.upper()] = int(hours * 60)

    # -- business hours -------------------------------------------------------
    bh = raw.get("business_hours")
    if not isinstance(bh, dict):
        raise ValueError("sla_policy.business_hours: expected object")

    days_list = bh.get("days")
    if not isinstance(days_list, list) or not all(isinstance(d, int) for d in days_list):
        raise ValueError("sla_policy.business_hours.days: expected list of ints")
    business_days = {d % 7 for d in days_list}  # normalize 7→0

    start = bh.get("start")
    if not isinstance(start, str):
        raise ValueError("sla_policy.business_hours.start: expected string 'HH:MM'")
    time.fromisoformat(start)  # validate

    end = bh.get("end")
    if not isinstance(end, str):
        raise ValueError("sla_policy.business_hours.end: expected string 'HH:MM'")
    time.fromisoformat(end)  # validate

    return SlaPolicy(
        targets=targets,
        business_days=business_days,
        business_start=start,
        business_end=end,
    )


def parse_holidays(raw: list[str]) -> set[date]:
    """Parse a list of 'YYYY-MM-DD' strings into a set of dates."""
    holidays: set[date] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, str):
            raise ValueError(f"holidays[{i}]: expected string, got {type(item).__name__}")
        try:
            holidays.add(date.fromisoformat(item))
        except ValueError as exc:
            raise ValueError(f"holidays[{i}]: invalid date '{item}'") from exc
    return holidays


# ---------------------------------------------------------------------------
# file-level loaders
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Any:
    """Load a JSON file, raising clear errors on failure."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def load_tickets(path: Path) -> list[Ticket]:
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected top-level JSON array")
    return parse_tickets(raw)


def load_policy(path: Path) -> SlaPolicy:
    raw = load_json(path)
    return parse_policy(raw)


def load_holidays(path: Path) -> set[date]:
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected top-level JSON array")
    return parse_holidays(raw)