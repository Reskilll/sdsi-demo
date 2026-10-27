"""Tests for the SLA calculator (status-timeline → breach computation)."""

from __future__ import annotations

from datetime import datetime, timezone

from sla_tracker.business_calendar import BusinessCalendar
from sla_tracker.models import (
    Priority,
    SlaPolicy,
    StatusEntry,
    Ticket,
    TicketStatus,
)
from sla_tracker.sla_calculator import calculate_ticket_sla

UTC = timezone.utc

# A fixed reference "now" for deterministic tests
NOW = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)

POLICY = SlaPolicy(targets={
    Priority.P1: 240,
    Priority.P2: 480,
    Priority.P3: 1440,
    Priority.P4: 4320,
})

NO_HOLIDAYS = BusinessCalendar(holidays=set(), tz="UTC")


def _ticket(
    ticket_id: str = "T",
    priority: Priority = Priority.P1,
    created: datetime | None = None,
    history: list[tuple[str, str]] | None = None,
    group: str = "Net",
) -> Ticket:
    created = created or datetime(2026, 10, 26, 9, 0, tzinfo=UTC)
    entries = [
        StatusEntry(status=TicketStatus(st), at=datetime.fromisoformat(at))
        for (st, at) in (history or [])
    ]
    return Ticket(
        ticket_id=ticket_id,
        priority=priority,
        assignee="a",
        assignee_group=group,
        created_at=created,
        status_history=entries,
    )


class TestSimpleCases:
    def test_meets_sla(self) -> None:
        # P1 = 240 min. Created 09:00, resolved 11:00 → 120 min. No breach.
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("RESOLVED", "2026-10-26T11:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        assert report.elapsed_business_minutes == 120.0
        assert not report.breached
        assert report.breach_minutes == 0.0

    def test_breaches_sla(self) -> None:
        # P1 = 240. Created 09:00, resolved 14:00 → 300 min → breach by 60
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("RESOLVED", "2026-10-26T14:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        assert report.elapsed_business_minutes == 300.0
        assert report.breached
        assert report.breach_minutes == 60.0

    def test_no_history(self) -> None:
        # No status history → single OPEN at created_at, elapsed up to `now`.
        t = _ticket(history=None, created=datetime(2026, 10, 28, 9, 0, tzinfo=UTC))
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS, ref=NOW)
        # 09:00 → 12:00 = 180 min
        assert report.elapsed_business_minutes == 180.0


class TestOnHold:
    def test_single_on_hold(self) -> None:
        # Created 09:00. ON_HOLD 10:00–11:00 (pause). Resolved 12:00.
        # Active: 09:00–10:00 (60) + 11:00–12:00 (60) = 120 min.
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("ON_HOLD", "2026-10-26T10:00:00+00:00"),
                ("IN_PROGRESS", "2026-10-26T11:00:00+00:00"),
                ("RESOLVED", "2026-10-26T12:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        assert report.elapsed_business_minutes == 120.0

    def test_on_hold_over_night(self) -> None:
        # Created Fri 09:00. ON_HOLD Fri 10:00 → Mon 09:00 (resume).
        # Active: Fri 09:00–10:00 (60) + Mon 09:00 onward.
        t = _ticket(
            created=datetime(2026, 10, 23, 9, 0, tzinfo=UTC),
            history=[
                ("OPEN", "2026-10-23T09:00:00+00:00"),
                ("ON_HOLD", "2026-10-23T10:00:00+00:00"),
                ("IN_PROGRESS", "2026-10-26T09:00:00+00:00"),
                ("RESOLVED", "2026-10-26T11:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        # Fri 60 + Mon 120 = 180
        assert report.elapsed_business_minutes == 180.0

    def test_multiple_on_hold(self) -> None:
        # Two ON_HOLD pauses.
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("ON_HOLD", "2026-10-26T09:30:00+00:00"),
                ("IN_PROGRESS", "2026-10-26T10:00:00+00:00"),
                ("ON_HOLD", "2026-10-26T10:30:00+00:00"),
                ("IN_PROGRESS", "2026-10-26T11:00:00+00:00"),
                ("RESOLVED", "2026-10-26T12:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        # Active: 09:00-09:30 (30) + 10:00-10:30 (30) + 11:00-12:00 (60) = 120
        assert report.elapsed_business_minutes == 120.0

    def test_still_on_hold(self) -> None:
        # Created 09:00, ON_HOLD 10:00, never resumed → clock stops at 10:00.
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("ON_HOLD", "2026-10-26T10:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS, ref=NOW)
        assert report.elapsed_business_minutes == 60.0

    def test_resume_midday(self) -> None:
        # Created 09:00, ON_HOLD until 14:00, resolved 15:00.
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("ON_HOLD", "2026-10-26T10:00:00+00:00"),
                ("IN_PROGRESS", "2026-10-26T14:00:00+00:00"),
                ("RESOLVED", "2026-10-26T15:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        # Active: 09:00-10:00 (60) + 14:00-15:00 (60) = 120
        assert report.elapsed_business_minutes == 120.0


class TestNonBusinessCreation:
    def test_created_on_weekend(self) -> None:
        # Created Saturday, resolved Monday 10:00.
        t = _ticket(
            created=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),  # Sat
            history=[
                ("OPEN", "2026-10-24T09:00:00+00:00"),
                ("RESOLVED", "2026-10-26T10:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        # Only Mon 09:00-10:00 counts = 60
        assert report.elapsed_business_minutes == 60.0

    def test_created_after_hours(self) -> None:
        # Created Monday 19:00, resolved Tuesday 10:00.
        t = _ticket(
            created=datetime(2026, 10, 26, 19, 0, tzinfo=UTC),
            history=[
                ("OPEN", "2026-10-26T19:00:00+00:00"),
                ("RESOLVED", "2026-10-27T10:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        # Tue 09:00-10:00 = 60
        assert report.elapsed_business_minutes == 60.0


class TestDueBy:
    def test_due_by_same_day(self) -> None:
        t = _ticket(created=datetime(2026, 10, 26, 9, 0, tzinfo=UTC))
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS, ref=NOW)
        # P1 = 240 min → 09:00 + 4h = 13:00
        assert report.due_by == datetime(2026, 10, 26, 13, 0, tzinfo=UTC)

    def test_due_by_next_day(self) -> None:
        # P2 = 480 min (8h). Created 10:00 → due next day 10:00.
        t = _ticket(
            priority=Priority.P2,
            created=datetime(2026, 10, 26, 10, 0, tzinfo=UTC),
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS, ref=NOW)
        # Mon: 10:00-18:00 = 480 min → exactly due at 18:00 Monday (since 8h = 480)
        # Wait: 10:00 + 480 min = 18:00 same day (8 business hours fit in one day)
        assert report.due_by == datetime(2026, 10, 26, 18, 0, tzinfo=UTC)

    def test_due_by_spans_weekend(self) -> None:
        # P1 = 240. Created Fri 17:00 → due Mon 13:00.
        t = _ticket(
            priority=Priority.P1,
            created=datetime(2026, 10, 23, 17, 0, tzinfo=UTC),
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS, ref=NOW)
        # Fri: 17:00-18:00 = 60; Mon: 09:00-12:00 = 180 → total 240 → due 12:00
        assert report.due_by == datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


class TestBoundary:
    def test_exact_target_not_breach(self) -> None:
        # P1 = 240. Created 09:00, resolved 13:00 = 240 → not breach (strictly >)
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("RESOLVED", "2026-10-26T13:00:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        assert report.elapsed_business_minutes == 240.0
        assert not report.breached
        assert report.breach_minutes == 0.0

    def test_one_minute_over(self) -> None:
        t = _ticket(
            history=[
                ("OPEN", "2026-10-26T09:00:00+00:00"),
                ("RESOLVED", "2026-10-26T13:01:00+00:00"),
            ]
        )
        report = calculate_ticket_sla(t, POLICY, NO_HOLIDAYS)
        assert report.elapsed_business_minutes == 241.0
        assert report.breached
        assert report.breach_minutes == 1.0
