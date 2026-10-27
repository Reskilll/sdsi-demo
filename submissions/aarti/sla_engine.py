"""SLA Breach Computation Engine.

Computes SLA breaches for support tickets per the rules:
  M1 – SLA targets by priority (P1=4h, P2=8h, P3=24h, P4=72h), business hours only
  M2 – Holidays excluded from SLA time
  M3 – SLA clock paused while ticket status is ON_HOLD
  M4 – Per-ticket: elapsed business minutes, due-by, breach yes/no, breach minutes
  M5 – Summary: breach % per priority and per assignee group
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, date, time, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)
TERMINAL_STATUSES = {"RESOLVED", "CLOSED", "CANCELLED"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parse_dt(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string (naive datetime)."""
    return datetime.fromisoformat(ts)


def is_business_day(d: date, holidays: set[date]) -> bool:
    """Return True if *d* is a weekday (Mon–Fri) and not a holiday."""
    return d.weekday() < 5 and d not in holidays


def next_business_day_start(dt: datetime, holidays: set[date]) -> datetime:
    """Return the *next* business-day 09:00 strictly after *dt*."""
    d = dt.date() + timedelta(days=1)
    while not is_business_day(d, holidays):
        d += timedelta(days=1)
    return datetime.combine(d, BUSINESS_START)


def business_minutes_in_interval(
    start: datetime,
    end: datetime,
    holidays: set[date],
) -> float:
    """Count business minutes in the half-open interval [start, end)."""
    if start >= end:
        return 0.0

    total = 0.0
    cur = start
    while cur < end:
        if is_business_day(cur.date(), holidays):
            day_end = datetime.combine(cur.date(), BUSINESS_END)
            day_start = datetime.combine(cur.date(), BUSINESS_START)
            effective_start = max(cur, day_start)
            effective_end = min(end, day_end)
            if effective_start < effective_end:
                total += (effective_end - effective_start).total_seconds() / 60.0
            cur = day_end
        else:
            # Jump to start of next day
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0))
    return total


def add_business_minutes(
    start: datetime,
    minutes_to_add: float,
    holidays: set[date],
) -> datetime:
    """Return the wall-clock datetime after adding *minutes_to_add* business
    minutes to *start*, skipping non-business hours and holidays."""
    remaining = minutes_to_add
    cur = start
    while remaining > 0:
        if is_business_day(cur.date(), holidays):
            day_end = datetime.combine(cur.date(), BUSINESS_END)
            day_start = datetime.combine(cur.date(), BUSINESS_START)
            effective_start = max(cur, day_start)
            available = (day_end - effective_start).total_seconds() / 60.0
            if effective_start >= day_end:
                available = 0.0
            if available >= remaining:
                return effective_start + timedelta(minutes=remaining)
            remaining -= max(available, 0.0)
        cur = next_business_day_start(cur, holidays)
    return cur


# ---------------------------------------------------------------------------
# Build active intervals (M3 – exclude ON_HOLD periods)
# ---------------------------------------------------------------------------

def build_active_intervals(
    status_history: list[dict[str, str]],
    resolution_dt: datetime | None,
) -> list[tuple[datetime, datetime]]:
    """Walk the status history and return a list of (start, end) intervals
    during which the SLA clock was running (i.e. all statuses except ON_HOLD).

    If the ticket is not in a terminal state at the end of the history, the
    last interval extends to *now*.
    """
    intervals: list[tuple[datetime, datetime]] = []
    active_start: datetime | None = None
    on_hold_start: datetime | None = None

    for entry in status_history:
        status = entry["status"]
        ts = parse_dt(entry["timestamp"])

        if status == "ON_HOLD":
            if active_start is not None:
                intervals.append((active_start, ts))
                active_start = None
            on_hold_start = ts
        else:
            if on_hold_start is not None:
                # Coming out of ON_HOLD
                active_start = ts
                on_hold_start = None
            elif active_start is None:
                active_start = ts

            if status in TERMINAL_STATUSES:
                intervals.append((active_start, ts))
                active_start = None

    # Still active (ticket not resolved yet) → extend to resolution_dt or now
    if active_start is not None:
        end = resolution_dt if resolution_dt is not None else datetime.now()
        intervals.append((active_start, end))

    return intervals


# ---------------------------------------------------------------------------
# Per-ticket computation (M4)
# ---------------------------------------------------------------------------

def compute_ticket(
    ticket: dict,
    sla_policy: dict,
    holidays: set[date],
    now: datetime,
) -> dict:
    ticket_id = ticket["ticket_id"]
    priority = ticket["priority"]
    target_hours = float(sla_policy[priority]["target_hours"])
    target_minutes = target_hours * 60.0

    # Determine resolution time (if any)
    resolution_dt: datetime | None = None
    for entry in ticket["status_history"]:
        if entry["status"] in TERMINAL_STATUSES:
            resolution_dt = parse_dt(entry["timestamp"])

    # Build active (non-ON_HOLD) intervals
    active_intervals = build_active_intervals(
        ticket["status_history"], resolution_dt
    )

    # Sum business minutes across all active intervals
    elapsed_minutes = sum(
        business_minutes_in_interval(s, e, holidays) for s, e in active_intervals
    )

    # Due-by = creation + target business hours (static deadline)
    created_dt = parse_dt(ticket["created_at"])
    due_by = add_business_minutes(created_dt, target_minutes, holidays)

    # Breach determination
    breached = elapsed_minutes > target_minutes
    breach_minutes = max(0.0, elapsed_minutes - target_minutes)

    return {
        "ticket_id": ticket_id,
        "priority": priority,
        "assignee_group": ticket["assignee_group"],
        "created_at": ticket["created_at"],
        "target_minutes": target_minutes,
        "elapsed_business_minutes": round(elapsed_minutes, 1),
        "due_by": due_by.isoformat(),
        "breach": breached,
        "breach_minutes": round(breach_minutes, 1),
        "status": (
            "RESOLVED"
            if resolution_dt is not None
            else ticket["status_history"][-1]["status"]
        ),
    }


# ---------------------------------------------------------------------------
# Summary (M5)
# ---------------------------------------------------------------------------

def compute_summary(results: list[dict]) -> dict:
    by_priority: dict[str, dict[str, int]] = {}
    by_group: dict[str, dict[str, int]] = {}

    for r in results:
        prio = r["priority"]
        grp = r["assignee_group"]

        for bucket, key in [(by_priority, prio), (by_group, grp)]:
            if key not in bucket:
                bucket[key] = {"total": 0, "breached": 0}
            bucket[key]["total"] += 1
            if r["breach"]:
                bucket[key]["breached"] += 1

    def pct(b: dict) -> float:
        return round(b["breached"] / b["total"] * 100, 1) if b["total"] else 0.0

    return {
        "by_priority": {
            k: {"total": v["total"], "breached": v["breached"], "breach_pct": pct(v)}
            for k, v in sorted(by_priority.items())
        },
        "by_assignee_group": {
            k: {"total": v["total"], "breached": v["breached"], "breach_pct": pct(v)}
            for k, v in sorted(by_group.items())
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(data_dir: Path | None = None) -> dict:
    """Entry point matching the agent-template contract."""
    base = data_dir or Path(__file__).resolve().parent

    tickets = load_json(base / "tickets.json")
    sla_policy = load_json(base / "sla_policy.json")
    holidays_raw: list[str] = load_json(base / "holidays.json")
    holidays: set[date] = {date.fromisoformat(h) for h in holidays_raw}

    now = datetime.now()

    per_ticket = [compute_ticket(t, sla_policy, holidays, now) for t in tickets]
    summary = compute_summary(per_ticket)

    return {
        "plan": [
            "Load tickets, sla_policy, holidays",
            "For each ticket: build active intervals (exclude ON_HOLD) → count business minutes (exclude holidays + weekends) → compare to SLA target",
            "Aggregate breach percentages by priority and assignee group",
        ],
        "result": {
            "per_ticket": per_ticket,
            "summary": summary,
        },
        "escalated": any(t["breach"] for t in per_ticket),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    output = run(data_dir)
    print(json.dumps(output["result"], indent=2, default=str))