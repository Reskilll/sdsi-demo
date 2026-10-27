"""Very basic SLA-breach POC.

Business-time accrual: start at the next business instant, add business minutes
skipping nights/weekends/holidays, subtract ON_HOLD pauses, compare to the
priority target. Interval math, no per-minute simulation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

DAY = timedelta(days=1)
WEEKEND = {5, 6}  # Monday = 0


def parse_ts(text: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp; reject anything with an offset."""
    if not text.endswith("Z"):
        raise ValueError(f"timestamp must be ISO-8601 UTC ending in 'Z': {text!r}")
    try:
        stamp = datetime.fromisoformat(text[:-1]).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp {text!r}: {exc}") from exc
    return stamp


class BusinessCalendar:
    """Business hours [09:00, 18:00) Mon-Fri, minus holidays."""

    def __init__(self, policy: dict, holidays: dict) -> None:
        hours = policy["business_hours"]
        self.days = set(hours["days"])
        self.start = self._clock(hours["start"])
        self.end = self._clock(hours["end"])
        self.holidays = {self._date(h["date"]) for h in holidays["holidays"]}
        if self.start >= self.end:
            raise ValueError("business_hours.start must be before end")

    @staticmethod
    def _clock(text: str) -> timedelta:
        hh, mm = text.split(":")
        return timedelta(hours=int(hh), minutes=int(mm))

    @staticmethod
    def _date(text: str):
        return datetime.fromisoformat(text).date()

    def is_business_day(self, day) -> bool:
        # Policy `days` uses ISO weekday numbers (Mon=1..Sun=7); date.weekday() is
        # Mon=0..Sun=6, so using it here would silently make Saturday a workday.
        return day.isoweekday() in self.days and day not in self.holidays

    def hours_on(self, day) -> list[tuple[datetime, datetime]]:
        if not self.is_business_day(day):
            return []
        base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        return [(base + self.start, base + self.end)]

    def next_start(self, moment: datetime) -> datetime:
        """First business instant at or after ``moment``."""
        day = moment.date()
        for _ in range(400):  # holidays can stack; a year of cover is plenty
            for begin, end in self.hours_on(day):
                if moment <= begin:
                    return begin
                if moment < end:
                    return moment  # inside business hours already
            day += DAY
        raise ValueError(f"no business hours found after {moment.isoformat()}")

    @staticmethod
    def _subtract(start, end, exclusions, index):
        """Split [start, end) around merged ``exclusions``; return segments + next index."""
        segments = []
        cursor = start
        while index < len(exclusions) and exclusions[index][1] <= cursor:
            index += 1
        while index < len(exclusions) and exclusions[index][0] < end:
            low, high = exclusions[index]
            if low > cursor:
                segments.append((cursor, min(low, end)))
            cursor = max(cursor, high)
            if cursor >= end:
                return segments, index
            index += 1
        if cursor < end:
            segments.append((cursor, end))
        return segments, index

    def accrue(self, begin: datetime, budget: timedelta, exclude=()) -> datetime:
        """Instant reached once ``budget`` of business time accrues from ``begin``.

        ``exclude`` holds merged pause intervals; they postpone the instant, which
        is what makes a paused clock push its deadline out.
        """
        exclusions = list(exclude)
        remaining = budget
        cursor = self.next_start(begin)
        if remaining <= timedelta(0):
            return cursor
        index = 0
        day = cursor.date()
        limit = day + timedelta(days=366 * 100)  # guard against an empty `days` list
        while day <= limit:
            for start, end in self.hours_on(day):
                if end <= cursor:
                    continue
                segments, index = self._subtract(max(start, cursor), end, exclusions, index)
                for seg_start, seg_end in segments:
                    window = seg_end - seg_start
                    if window >= remaining:
                        return seg_start + remaining
                    remaining -= window
            day += DAY
        raise ValueError(f"no business time available after {begin.isoformat()}")

    def business_between(self, begin: datetime, end: datetime) -> timedelta:
        """Business time inside [begin, end). Zero when the range is empty."""
        if end <= begin:
            return timedelta(0)
        total = timedelta(0)
        day = begin.date()
        while day <= end.date():
            for start, stop in self.hours_on(day):
                overlap = min(stop, end) - max(start, begin)
                if overlap > timedelta(0):
                    total += overlap
            day += DAY
        return total


def hold_intervals(history: list[dict], as_of: datetime) -> list[tuple[datetime, datetime]]:
    """ON_HOLD spans from status history, sorted and merged (overlaps/nesting)."""
    spans: list[tuple[datetime, datetime, datetime | None]] = []
    open_at: datetime | None = None
    for event in sorted(history, key=lambda e: parse_ts(e["changed_at"])):
        moment = parse_ts(event["changed_at"])
        if event["status"] == "ON_HOLD":
            open_at = moment
        elif open_at is not None:
            spans.append((open_at, moment, None))
            open_at = None
    if open_at is not None:
        spans.append((open_at, as_of, None))  # still on hold at --as-of

    merged: list[list[datetime]] = []
    for start, end, _ in sorted(s for s in spans if s[1] > s[0]):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def evaluate(ticket: dict, calendar: BusinessCalendar, policy: dict, as_of: datetime) -> dict:
    """M4 metrics for one ticket."""
    created = parse_ts(ticket["created_at"])
    resolved = parse_ts(ticket["resolved_at"]) if ticket.get("resolved_at") else None
    if resolved is not None and resolved < created:
        raise ValueError(f"{ticket['id']}: resolved_at is before created_at")

    stop = min(resolved, as_of) if resolved else as_of
    targets = policy["targets_minutes"]
    if ticket["priority"] not in targets:
        raise ValueError(
            f"{ticket['id']}: priority {ticket['priority']!r} is not in the policy "
            f"(known: {', '.join(sorted(targets))})"
        )
    target = timedelta(minutes=targets[ticket["priority"]])

    holds = hold_intervals(ticket.get("status_history", []), as_of)
    gross = calendar.business_between(created, stop)
    paused = min(
        sum(
            (calendar.business_between(start, min(end, stop)) for start, end in holds),
            timedelta(0),
        ),
        gross,
    )
    elapsed = gross - paused

    # Paused time postpones the deadline too: §5 only reconciles at 18:00 this way.
    due = calendar.accrue(created, target, holds)
    breached = elapsed > target  # resolving exactly at due-by is not a breach
    return {
        "ticket_id": ticket["id"],
        "priority": ticket["priority"],
        "assignee_group": ticket.get("assignee_group") or "UNASSIGNED",
        "open": resolved is None,
        "elapsed_minutes": int(elapsed.total_seconds() // 60),
        "due_by": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "breach": breached,
        "breach_minutes": int(max(timedelta(0), elapsed - target).total_seconds() // 60),
    }


def summarize(rows: list[dict], field: str) -> dict:
    """Breach percentage per bucket, 1 decimal; None for an empty bucket."""
    buckets: dict[str, list[bool]] = {}
    for row in rows:
        buckets.setdefault(row[field], []).append(row["breach"])
    return {
        key: round(100.0 * sum(flags) / len(flags), 1)
        for key, flags in sorted(buckets.items())
    }


def load(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sla_poc")
    parser.add_argument("--tickets", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--holidays", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--format", choices=("table", "json"), default="table")
    args = parser.parse_args(argv)

    try:
        policy = load(args.policy)
        calendar = BusinessCalendar(policy, load(args.holidays))
        as_of = parse_ts(args.as_of)
        rows = [
            evaluate(ticket, calendar, policy, as_of)
            for ticket in load(args.tickets)["tickets"]
        ]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = {
        "as_of": args.as_of,
        "tickets": rows,
        "summary": {
            "by_priority": summarize(rows, "priority"),
            "by_assignee_group": summarize(rows, "assignee_group"),
        },
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{'ID':<8}{'PRI':<5}{'GROUP':<12}{'ELAPSED':>9}{'DUE BY':>21}{'BREACH':>8}")
        for row in rows:
            print(
                f"{row['ticket_id']:<8}{row['priority']:<5}{row['assignee_group']:<12}"
                f"{row['elapsed_minutes']:>9}{row['due_by']:>21}"
                f"{'yes' if row['breach'] else 'no':>8}"
            )
        print("\nbreach % by priority:      ", result["summary"]["by_priority"])
        print("breach % by assignee group:", result["summary"]["by_assignee_group"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
