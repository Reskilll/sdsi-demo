"""Smoke tests for the POC: golden example plus the one interesting boundary."""

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from sla_poc import BusinessCalendar, evaluate, hold_intervals, parse_ts, summarize

DATA = Path(__file__).parent / "data"


@pytest.fixture
def ctx():
    policy = json.loads((DATA / "sla_policy.json").read_text(encoding="utf-8"))
    holidays = json.loads((DATA / "holidays.json").read_text(encoding="utf-8"))
    tickets = json.loads((DATA / "tickets.json").read_text(encoding="utf-8"))["tickets"]
    as_of = parse_ts("2026-10-28T00:00:00Z")
    return BusinessCalendar(policy, holidays), policy, tickets, as_of


def test_golden_section_5(ctx):
    """Spec §5: 450 gross, 90 paused, 360 elapsed, due exactly at 18:00 -> no breach."""
    calendar, policy, tickets, as_of = ctx
    row = evaluate(next(t for t in tickets if t["id"] == "T-1001"), calendar, policy, as_of)
    assert row["elapsed_minutes"] == 360
    assert row["due_by"] == "2026-10-27T18:00:00Z"
    assert row["breach"] is False
    assert row["breach_minutes"] == 0


def test_resolution_exactly_at_due_by_is_not_a_breach(ctx):
    """T-1003: P2 target 480 min lands exactly on 18:00, resolved exactly then."""
    calendar, policy, tickets, as_of = ctx
    row = evaluate(next(t for t in tickets if t["id"] == "T-1003"), calendar, policy, as_of)
    assert row["elapsed_minutes"] == 480
    assert row["due_by"] == "2026-10-20T18:00:00Z"
    assert row["breach"] is False


def test_hold_outside_business_hours_pauses_nothing(ctx):
    """T-1007: first hold is 20:00->09:00 (all outside hours) -> only the 17:00->18:00 hour counts."""
    calendar, policy, tickets, as_of = ctx
    row = evaluate(next(t for t in tickets if t["id"] == "T-1007"), calendar, policy, as_of)
    spans = hold_intervals(
        next(t for t in tickets if t["id"] == "T-1007")["status_history"], as_of
    )
    assert spans == [
        (datetime(2026, 10, 26, 20, 0, tzinfo=timezone.utc),
         datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)),
        (datetime(2026, 10, 27, 17, 0, tzinfo=timezone.utc),
         datetime(2026, 10, 27, 18, 30, tzinfo=timezone.utc)),
    ]
    # 60 min of the second hold is business time; the first contributes nothing.
    # Gross = 44h business (8h + three 9h days + holiday 0 + 9h), minus the 1h pause.
    assert row["elapsed_minutes"] == 44 * 60 - 60


def test_open_ticket_accrues_to_as_of_and_unassigned(ctx):
    calendar, policy, tickets, as_of = ctx
    row = evaluate(next(t for t in tickets if t["id"] == "T-1006"), calendar, policy, as_of)
    assert row["open"] is True
    assert row["assignee_group"] == "UNASSIGNED"


def test_saturday_is_not_a_business_day(ctx):
    """Policy days are ISO numbers (Mon=1..Sun=7) -- a classic off-by-one trap."""
    calendar, policy, _, _ = ctx
    assert calendar.is_business_day(date(2026, 10, 24)) is False  # Saturday
    assert calendar.is_business_day(date(2026, 10, 25)) is False  # Sunday
    assert calendar.is_business_day(date(2026, 10, 23)) is True  # Friday


def test_due_by_never_lands_outside_business_hours(ctx):
    calendar, policy, tickets, as_of = ctx
    for ticket in tickets:
        row = evaluate(ticket, calendar, policy, as_of)
        due = parse_ts(row["due_by"])
        assert calendar.is_business_day(due.date()), row
        assert calendar.hours_on(due.date())[0][0] < due <= calendar.hours_on(due.date())[0][1]


def test_summary_has_one_decimal_and_no_zero_division(ctx):
    calendar, policy, tickets, as_of = ctx
    rows = [evaluate(t, calendar, policy, as_of) for t in tickets]
    assert summarize(rows, "priority")["P2"] == 50.0  # T-1006, T-1007 breached
    assert summarize(rows, "assignee_group")["UNASSIGNED"] == 100.0
    assert summarize([], "priority") == {}  # empty bucket: no ZeroDivisionError
