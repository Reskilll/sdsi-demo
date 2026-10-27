"""Input validation and data loading.

Every function that reads external data first validates structure, types, and
semantic constraints before the data enters the domain model layer.  This ensures
that bugs in the input files cannot cause silent miscalculations downstream.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sla_tracker.models import Priority, StatusEntry, Ticket, TicketStatus


class ValidationError(ValueError):
    """Raised when input data fails structural or semantic validation."""


# ── ticket validation ────────────────────────────────────────────────────────


def validate_ticket(raw: dict[str, Any]) -> Ticket:
    """Validate a single ticket dict and return a ``Ticket`` domain object."""
    if not isinstance(raw, dict):
        raise ValidationError("Each ticket must be a JSON object")

    # Required top-level keys
    for key in ("ticket_id", "priority", "assignee", "assignee_group", "created_at"):
        if key not in raw:
            raise ValidationError(f"Ticket is missing required key: {key!r}")

    # ticket_id
    ticket_id = str(raw["ticket_id"]).strip()
    if not ticket_id:
        raise ValidationError("ticket_id must be non-empty")

    # priority
    try:
        priority = Priority(int(raw["priority"]))
    except (ValueError, TypeError) as exc:
        raise ValidationError(
            f"Ticket {ticket_id!r}: invalid priority {raw['priority']!r}. "
            f"Must be 1–4."
        ) from exc

    # assignee
    assignee = str(raw.get("assignee", "unassigned")).strip() or "unassigned"

    # assignee_group
    assignee_group = str(raw.get("assignee_group", "unknown")).strip() or "unknown"

    # created_at
    created_at = _parse_utc_datetime(raw["created_at"], "created_at", ticket_id)

    # status_history (optional — defaults to single OPEN entry at creation)
    status_history: list[StatusEntry] = []
    raw_history = raw.get("status_history")
    if raw_history is not None:
        if not isinstance(raw_history, list):
            raise ValidationError(
                f"Ticket {ticket_id!r}: status_history must be a list"
            )
        status_history = _validate_status_history(raw_history, ticket_id, created_at)

    return Ticket(
        ticket_id=ticket_id,
        priority=priority,
        assignee=assignee,
        assignee_group=assignee_group,
        created_at=created_at,
        status_history=status_history,
    )


def _validate_status_history(
    raw: list[dict[str, Any]], ticket_id: str, created_at: datetime
) -> list[StatusEntry]:
    """Validate and sort the status-history ledger."""
    entries: list[tuple[datetime, StatusEntry]] = []

    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValidationError(
                f"Ticket {ticket_id!r}: status_history[{i}] must be an object"
            )

        if "status" not in item:
            raise ValidationError(
                f"Ticket {ticket_id!r}: status_history[{i}] missing 'status'"
            )
        if "at" not in item:
            raise ValidationError(
                f"Ticket {ticket_id!r}: status_history[{i}] missing 'at'"
            )

        # Status
        try:
            status = TicketStatus(str(item["status"]).upper())
        except ValueError as exc:
            raise ValidationError(
                f"Ticket {ticket_id!r}: status_history[{i}] invalid status "
                f"{item['status']!r}"
            ) from exc

        # Timestamp
        at = _parse_utc_datetime(item["at"], f"status_history[{i}].at", ticket_id)

        entries.append((at, StatusEntry(status=status, at=at)))

    # Sort chronologically
    entries.sort(key=lambda e: e[0])
    return [e[1] for e in entries]


# ── SLA policy validation ────────────────────────────────────────────────────


def validate_sla_policy(raw: dict[str, Any]) -> dict[Priority, int]:
    """Validate SLA policy dict and return mapping of Priority → business minutes."""
    if not isinstance(raw, dict):
        raise ValidationError("SLA policy must be a JSON object")

    targets: dict[Priority, int] = {}

    for p in Priority:
        key = p.name  # "P1", "P2", …
        if key not in raw:
            raise ValidationError(f"SLA policy is missing priority: {key}")
        val = raw[key]
        try:
            minutes = int(val)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                f"SLA policy {key}: expected integer, got {val!r}"
            ) from exc
        if minutes <= 0:
            raise ValidationError(
                f"SLA policy {key}: must be positive, got {minutes}"
            )
        targets[p] = minutes

    return targets


# ── holiday validation ───────────────────────────────────────────────────────


def validate_holidays(raw: list[str]) -> set[date]:
    """Validate holiday list and return a ``set`` of ``date`` objects."""
    if not isinstance(raw, list):
        raise ValidationError("Holidays file must be a JSON array of ISO-8601 date strings")

    holidays: set[date] = set()
    for i, item in enumerate(raw):
        date_str = str(item).strip()
        try:
            d = date.fromisoformat(date_str)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                f"Holidays[{i}]: invalid date string {item!r}"
            ) from exc
        holidays.add(d)
    return holidays


# ── helpers ──────────────────────────────────────────────────────────────────


def _parse_utc_datetime(value: Any, field_name: str, ticket_id: str) -> datetime:
    """Parse an ISO-8601 datetime string into a timezone-aware UTC datetime."""
    raw_str = str(value).strip()

    # Handle "Z" suffix
    if raw_str.endswith("Z"):
        raw_str = raw_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(raw_str)
    except (ValueError, TypeError) as exc:
        raise ValidationError(
            f"Ticket {ticket_id!r}: {field_name}={value!r} is not a valid ISO-8601 datetime"
        ) from exc

    # Force to UTC (naive datetimes are treated as UTC)
    dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

    return dt


def _parse_date(value: str, field_name: str) -> date:
    """Parse an ISO-8601 date string."""
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid date for {field_name}: {value!r}") from exc
