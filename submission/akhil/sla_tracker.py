"""Calculate support-ticket SLA time using a configurable business calendar."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class SLAInputError(ValueError):
    """Raised when input data cannot be interpreted safely."""


@dataclass(frozen=True)
class Policy:
    timezone: ZoneInfo
    business_start: time
    business_end: time
    business_days: frozenset[int]
    priority_hours: dict[str, int]


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise SLAInputError(f"{field} must be an ISO-8601 timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SLAInputError(f"{field} is not a valid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SLAInputError(f"{field} must include a timezone offset")
    return parsed


def parse_clock(value: Any, field: str) -> time:
    if not isinstance(value, str):
        raise SLAInputError(f"{field} must be a time in HH:MM format")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise SLAInputError(f"{field} is not a valid time: {value!r}") from exc
    if parsed.tzinfo is not None or parsed.second or parsed.microsecond:
        raise SLAInputError(f"{field} must be a local HH:MM time without an offset")
    return parsed


def parse_policy(data: Any) -> Policy:
    if not isinstance(data, dict):
        raise SLAInputError("sla_policy.json must contain a JSON object")

    timezone_name = data.get("timezone", "UTC")
    if not isinstance(timezone_name, str):
        raise SLAInputError("policy timezone must be a string")
    try:
        timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise SLAInputError(f"unknown policy timezone: {timezone_name!r}") from exc

    business_hours = data.get("business_hours", {})
    if not isinstance(business_hours, dict):
        raise SLAInputError("business_hours must be an object")
    start = parse_clock(business_hours.get("start", "09:00"), "business_hours.start")
    end = parse_clock(business_hours.get("end", "18:00"), "business_hours.end")
    if start >= end:
        raise SLAInputError("business_hours.start must be earlier than business_hours.end")

    days = data.get("business_days", [0, 1, 2, 3, 4])
    if (
        not isinstance(days, list)
        or not days
        or any(type(day) is not int or day < 0 or day > 6 for day in days)
        or len(set(days)) != len(days)
    ):
        raise SLAInputError("business_days must be a non-empty list of unique weekday numbers (0=Monday)")

    priority_hours = data.get("priority_hours")
    if not isinstance(priority_hours, dict):
        raise SLAInputError("priority_hours must be an object")
    required = {"P1", "P2", "P3", "P4"}
    missing = required - priority_hours.keys()
    if missing:
        raise SLAInputError(f"priority_hours is missing: {', '.join(sorted(missing))}")
    for priority, hours in priority_hours.items():
        if not isinstance(priority, str) or type(hours) is not int or hours <= 0:
            raise SLAInputError("priority_hours must map priority names to positive integer hours")

    return Policy(timezone, start, end, frozenset(days), priority_hours)


def parse_holidays(data: Any) -> frozenset[date]:
    values = data.get("holidays") if isinstance(data, dict) else data
    if not isinstance(values, list):
        raise SLAInputError("holidays.json must be a list of dates or an object with a holidays list")
    holidays: set[date] = set()
    for value in values:
        if not isinstance(value, str):
            raise SLAInputError("holiday entries must be YYYY-MM-DD strings")
        try:
            holidays.add(date.fromisoformat(value))
        except ValueError as exc:
            raise SLAInputError(f"invalid holiday date: {value!r}") from exc
    return frozenset(holidays)


def parse_tickets(data: Any) -> list[dict[str, Any]]:
    tickets = data.get("tickets") if isinstance(data, dict) else data
    if not isinstance(tickets, list) or any(not isinstance(ticket, dict) for ticket in tickets):
        raise SLAInputError("tickets.json must be a list of ticket objects")
    return tickets


class BusinessCalendar:
    def __init__(self, policy: Policy, holidays: frozenset[date]):
        self.policy = policy
        self.holidays = holidays

    def _windows(self, start: datetime, end: datetime | None) -> Iterator[tuple[datetime, datetime]]:
        first_day = start.astimezone(self.policy.timezone).date()
        last_day = end.astimezone(self.policy.timezone).date() if end is not None else None
        for offset in range(36600):
            day = first_day + timedelta(days=offset)
            if last_day is not None and day > last_day:
                return
            if day.weekday() not in self.policy.business_days or day in self.holidays:
                continue
            window_start = datetime.combine(day, self.policy.business_start, self.policy.timezone)
            window_end = datetime.combine(day, self.policy.business_end, self.policy.timezone)
            clipped_start = max(start, window_start)
            clipped_end = min(end, window_end) if end is not None else window_end
            if clipped_start < clipped_end:
                yield clipped_start, clipped_end
        raise SLAInputError("date range exceeds the supported 100-year calculation horizon")

    @staticmethod
    def _subtract_holds(
        window_start: datetime,
        window_end: datetime,
        holds: list[tuple[datetime, datetime]],
    ) -> Iterator[tuple[datetime, datetime]]:
        cursor = window_start
        for hold_start, hold_end in holds:
            if hold_end <= cursor:
                continue
            if hold_start >= window_end:
                break
            if hold_start > cursor:
                yield cursor, min(hold_start, window_end)
            cursor = max(cursor, hold_end)
            if cursor >= window_end:
                return
        if cursor < window_end:
            yield cursor, window_end

    def elapsed(self, start: datetime, end: datetime, holds: list[tuple[datetime, datetime]]) -> timedelta:
        total = timedelta()
        for window_start, window_end in self._windows(start, end):
            for available_start, available_end in self._subtract_holds(window_start, window_end, holds):
                total += available_end - available_start
        return total

    def add_minutes(
        self,
        start: datetime,
        minutes: int,
        holds: list[tuple[datetime, datetime]],
    ) -> datetime:
        remaining = timedelta(minutes=minutes)
        for window_start, window_end in self._windows(start, None):
            for available_start, available_end in self._subtract_holds(window_start, window_end, holds):
                available = available_end - available_start
                if remaining <= available:
                    return available_start + remaining
                remaining -= available
        raise SLAInputError("could not find a due-by time within the supported 100-year horizon")


def _status_history(
    ticket: dict[str, Any], start: datetime, end: datetime, policy: Policy
) -> tuple[list[tuple[datetime, datetime]], datetime | None]:
    history = ticket.get("status_history", [])
    if not isinstance(history, list):
        raise SLAInputError(f"ticket {ticket.get('ticket_id', ticket.get('id', '?'))}: status_history must be a list")

    parsed: list[tuple[datetime, str, str | None]] = []
    for index, event in enumerate(history):
        if not isinstance(event, dict):
            raise SLAInputError(f"status_history[{index}] must be an object")
        timestamp = parse_timestamp(event.get("timestamp", event.get("at")), f"status_history[{index}].timestamp")
        status_value = event.get("status", event.get("to"))
        if not isinstance(status_value, str) or not status_value.strip():
            raise SLAInputError(f"status_history[{index}] must include a non-empty status or to field")
        from_value = event.get("from")
        if from_value is not None and (not isinstance(from_value, str) or not from_value.strip()):
            raise SLAInputError(f"status_history[{index}].from must be a non-empty string")
        parsed.append((timestamp.astimezone(policy.timezone), status_value.strip().upper(), from_value.upper() if from_value else None))

    for previous, current in zip(parsed, parsed[1:]):
        if current[0] < previous[0]:
            raise SLAInputError("status_history events must be in chronological order")
    if any(timestamp < start or timestamp > end for timestamp, _, _ in parsed):
        raise SLAInputError("status_history timestamps must fall between created_at and the ticket end time")

    first_from = parsed[0][2] if parsed else None
    if "initial_status" in ticket:
        initial_status = ticket["initial_status"]
    elif first_from:
        initial_status = first_from
    elif not parsed:
        initial_status = ticket.get("status", "OPEN")
    else:
        initial_status = "OPEN"
    if not isinstance(initial_status, str) or not initial_status.strip():
        raise SLAInputError("initial_status must be a non-empty string")
    current_status = initial_status.strip().upper()

    holds: list[tuple[datetime, datetime]] = []
    hold_start: datetime | None = start if current_status == "ON_HOLD" else None
    terminal_time: datetime | None = None
    for timestamp, next_status, from_status in parsed:
        if from_status is not None and from_status != current_status:
            raise SLAInputError(f"status history expected {current_status}, got from={from_status}")
        if current_status == "ON_HOLD" and next_status != "ON_HOLD" and hold_start is not None:
            if hold_start < timestamp:
                holds.append((hold_start, timestamp))
            hold_start = None
        elif current_status != "ON_HOLD" and next_status == "ON_HOLD":
            hold_start = timestamp
        if terminal_time is None and next_status in {"RESOLVED", "CLOSED"}:
            terminal_time = timestamp
        current_status = next_status
    if hold_start is not None and hold_start < end:
        holds.append((hold_start, end))
    return holds, terminal_time


def _format_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def evaluate(
    tickets: Iterable[dict[str, Any]],
    policy: Policy,
    holidays: frozenset[date],
    as_of: datetime,
) -> dict[str, Any]:
    calendar = BusinessCalendar(policy, holidays)
    evaluation_time = as_of.astimezone(policy.timezone)
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, ticket in enumerate(tickets):
        ticket_id = ticket.get("ticket_id", ticket.get("id"))
        if not isinstance(ticket_id, str) or not ticket_id.strip():
            raise SLAInputError(f"ticket at index {index} must have a non-empty ticket_id")
        ticket_id = ticket_id.strip()
        if ticket_id in seen_ids:
            raise SLAInputError(f"duplicate ticket_id: {ticket_id}")
        seen_ids.add(ticket_id)

        priority = ticket.get("priority")
        if not isinstance(priority, str) or priority.upper() not in policy.priority_hours:
            raise SLAInputError(f"ticket {ticket_id}: priority must match a key in priority_hours")
        priority = priority.upper()

        created_at = parse_timestamp(ticket.get("created_at"), f"ticket {ticket_id}.created_at").astimezone(policy.timezone)
        explicit_end_value = ticket.get("resolved_at") or ticket.get("closed_at")
        explicit_end = (
            parse_timestamp(explicit_end_value, f"ticket {ticket_id}.resolved_at").astimezone(policy.timezone)
            if explicit_end_value is not None
            else None
        )

        history = ticket.get("status_history", [])
        if not isinstance(history, list):
            raise SLAInputError(f"ticket {ticket_id}: status_history must be a list")
        terminal_candidates: list[datetime] = []
        for event_index, event in enumerate(history):
            if not isinstance(event, dict):
                raise SLAInputError(f"ticket {ticket_id}: status_history[{event_index}] must be an object")
            status_value = event.get("status", event.get("to"))
            if isinstance(status_value, str) and status_value.strip().upper() in {"RESOLVED", "CLOSED"}:
                terminal_candidates.append(
                    parse_timestamp(
                        event.get("timestamp", event.get("at")),
                        f"ticket {ticket_id}.status_history[{event_index}].timestamp",
                    ).astimezone(policy.timezone)
                )
        history_end = min(terminal_candidates) if terminal_candidates else None
        if explicit_end is not None and history_end is not None and explicit_end != history_end:
            raise SLAInputError(f"ticket {ticket_id}: resolved_at must match its first RESOLVED/CLOSED history event")
        end = explicit_end or history_end or evaluation_time
        if end < created_at:
            raise SLAInputError(f"ticket {ticket_id}: end time must not be earlier than created_at")
        if explicit_end is None and history_end is None and created_at > evaluation_time:
            raise SLAInputError(f"ticket {ticket_id}: created_at is later than the evaluation time")

        holds, _ = _status_history(ticket, created_at, end, policy)
        elapsed = calendar.elapsed(created_at, end, holds)
        elapsed_minutes = int(elapsed.total_seconds() // 60)
        target_minutes = policy.priority_hours[priority] * 60
        due_by = calendar.add_minutes(created_at, target_minutes, holds)
        breached = elapsed_minutes > target_minutes
        assignee_group = ticket.get("assignee_group") or "Unassigned"
        if not isinstance(assignee_group, str):
            raise SLAInputError(f"ticket {ticket_id}: assignee_group must be a string")

        results.append(
            {
                "ticket_id": ticket_id,
                "priority": priority,
                "assignee_group": assignee_group,
                "elapsed_business_minutes": elapsed_minutes,
                "due_by": _format_timestamp(due_by),
                "breached": breached,
                "breach_minutes": max(0, elapsed_minutes - target_minutes),
            }
        )

    return {
        "as_of": _format_timestamp(evaluation_time),
        "timezone": policy.timezone.key,
        "tickets": results,
        "summary": _summarize(results, policy.priority_hours),
    }


def _summarize(results: list[dict[str, Any]], priority_hours: dict[str, int]) -> dict[str, Any]:
    def group_metrics(key: str, values: Iterable[str]) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for value in sorted(set(values)):
            matching = [item for item in results if item[key] == value]
            count = len(matching)
            breach_count = sum(item["breached"] for item in matching)
            summary[value] = {
                "ticket_count": count,
                "breach_count": breach_count,
                "breach_percent": round(breach_count * 100 / count, 2) if count else 0.0,
            }
        return summary

    priority_values = [f"P{number}" for number in range(1, 5)]
    priority_summary: dict[str, Any] = {}
    for priority in priority_values:
        matching = [item for item in results if item["priority"] == priority]
        count = len(matching)
        breach_count = sum(item["breached"] for item in matching)
        priority_summary[priority] = {
            "ticket_count": count,
            "breach_count": breach_count,
            "breach_percent": round(breach_count * 100 / count, 2) if count else 0.0,
        }
    return {
        "by_priority": priority_summary,
        "by_assignee_group": group_metrics(
            "assignee_group", (item["assignee_group"] for item in results)
        ),
    }


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as source:
            return json.load(source)
    except json.JSONDecodeError as exc:
        raise SLAInputError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
    except OSError as exc:
        raise SLAInputError(f"cannot read {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Calculate business-time SLA for support tickets.")
    parser.add_argument("--tickets", type=Path, default=base / "tickets.json")
    parser.add_argument("--policy", type=Path, default=base / "sla_policy.json")
    parser.add_argument("--holidays", type=Path, default=base / "holidays.json")
    parser.add_argument("--as-of", help="ISO-8601 timestamp for active tickets; defaults to current time")
    parser.add_argument("--output", type=Path, help="write report JSON to this path instead of stdout")
    args = parser.parse_args(argv)

    try:
        policy = parse_policy(_read_json(args.policy))
        holidays = parse_holidays(_read_json(args.holidays))
        tickets = parse_tickets(_read_json(args.tickets))
        as_of = parse_timestamp(args.as_of, "--as-of") if args.as_of else datetime.now(policy.timezone)
        report = evaluate(tickets, policy, holidays, as_of)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (SLAInputError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())