"""Input validation, schema checks, timezone normalization, sanitization."""

from datetime import datetime, timezone
from typing import Any

from .models import Ticket, SLAPolicy, StatusTransition


def validate_tickets(data: list[dict]) -> tuple[list[Ticket], list[str]]:
    """Validate and parse a list of ticket dicts. Returns (valid_tickets, errors)."""
    tickets: list[Ticket] = []
    errors: list[str] = []

    if not isinstance(data, list):
        return tickets, ["tickets data must be a JSON array"]

    for i, raw in enumerate(data):
        idx = raw.get("ticket_id", f"index_{i}")
        try:
            if not isinstance(raw, dict):
                errors.append(f"[{idx}] not a JSON object")
                continue
            if "ticket_id" not in raw or not raw["ticket_id"]:
                errors.append(f"[index_{i}] missing ticket_id")
                continue

            # Validate transitions
            transitions_raw = raw.get("transitions", [])
            if not isinstance(transitions_raw, list):
                errors.append(f"[{raw['ticket_id']}] transitions must be a list")
                continue

            transitions = []
            for j, t in enumerate(transitions_raw):
                if not isinstance(t, dict):
                    errors.append(f"[{raw['ticket_id']}] transition[{j}] not an object")
                    continue
                if "timestamp" not in t:
                    errors.append(f"[{raw['ticket_id']}] transition[{j}] missing timestamp")
                    continue
                if "status" not in t:
                    errors.append(f"[{raw['ticket_id']}] transition[{j}] missing status")
                    continue
                try:
                    transitions.append(StatusTransition.from_dict(t))
                except (ValueError, KeyError) as e:
                    errors.append(f"[{raw['ticket_id']}] transition[{j}] parse error: {e}")
                    continue

            transitions.sort(key=lambda x: x.timestamp)
            ticket = Ticket(
                ticket_id=raw["ticket_id"],
                priority=raw.get("priority", "P4").upper().strip(),
                assignee_group=raw.get("assignee_group") or "Unassigned",
                transitions=transitions,
            )
            tickets.append(ticket)
        except Exception as e:
            errors.append(f"[{idx}] unexpected error: {e}")

    return tickets, errors


def validate_policy(data: dict) -> tuple[SLAPolicy | None, list[str]]:
    """Validate SLA policy dict."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["policy must be a JSON object"]

    targets = data.get("targets", data.get("sla_targets", {}))
    if not isinstance(targets, dict):
        return None, ["targets must be a JSON object mapping priority to minutes"]

    for k, v in targets.items():
        if not isinstance(v, (int, float)) or v <= 0:
            errors.append(f"target '{k}' must be a positive number")

    return SLAPolicy.from_dict(data), errors


def validate_holidays(data: list | dict) -> tuple[list[str], list[str]]:
    """Validate holidays data, returns list of YYYY-MM-DD strings."""
    errors: list[str] = []
    dates: list[str] = []

    if isinstance(data, list):
        raw_dates = data
    elif isinstance(data, dict):
        raw_dates = data.get("holidays", data.get("dates", []))
    else:
        return dates, ["holidays must be a JSON array or object with 'holidays' key"]

    if not isinstance(raw_dates, list):
        return dates, ["holidays list must be a JSON array"]

    for i, d in enumerate(raw_dates):
        if not isinstance(d, str):
            errors.append(f"holiday[{i}] not a string")
            continue
        try:
            # Validate it's a valid date string
            parsed = datetime.strptime(d.strip()[:10], "%Y-%m-%d")
            dates.append(parsed.strftime("%Y-%m-%d"))
        except ValueError:
            errors.append(f"holiday[{i}] '{d}' is not a valid YYYY-MM-DD date")

    return dates, errors