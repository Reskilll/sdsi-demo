"""Tests for the SLA Tracker — run with `python -m pytest tests/ -v`."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

# Make the submission directory importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sla_tracker.calendar import add_business_minutes, business_minutes_between
from sla_tracker.models import SlaPolicy, StatusEntry, Ticket
from sla_tracker.reporter import build_summary
from sla_tracker.sla_calculator import compute_all_tickets
from sla_tracker.validation import parse_holidays, parse_policy, parse_tickets


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

EMPTY_HOLIDAYS: set[date] = set()
DEFAULT_POLICY = SlaPolicy(
    targets={"P1": 240, "P2": 480, "P3": 1440, "P4": 4320},
    business_days={0, 1, 2, 3, 4},
    business_start="09:00",
    business_end="18:00",
)


# =================================== M1 ===================================
class TestBusinessMinutes:
    """M1: business-hours-only counting."""

    def test_same_day_fully_inside(self):
        # Mon 10:00–12:00 = 120 min
        result = business_minutes_between(
            datetime(2026, 10, 19, 10, 0),
            datetime(2026, 10, 19, 12, 0),
            EMPTY_HOLIDAYS,
        )
        assert result == 120

    def test_crosses_business_day_end(self):
        # Mon 17:00 → Tue 10:00 = 60 (Mon) + 60 (Tue) = 120
        result = business_minutes_between(
            datetime(2026, 10, 19, 17, 0),
            datetime(2026, 10, 20, 10, 0),
            EMPTY_HOLIDAYS,
        )
        assert result == 120

    def test_weekend_is_excluded(self):
        # Fri 17:00 → Mon 10:00 = 60 (Fri) + 60 (Mon) = 120
        result = business_minutes_between(
            datetime(2026, 10, 23, 17, 0),
            datetime(2026, 10, 26, 10, 0),
            EMPTY_HOLIDAYS,
        )
        assert result == 120

    def test_before_business_hours(self):
        # Mon 07:00 → Mon 11:00 = 120 min (only 09:00-11:00)
        result = business_minutes_between(
            datetime(2026, 10, 19, 7, 0),
            datetime(2026, 10, 19, 11, 0),
            EMPTY_HOLIDAYS,
        )
        assert result == 120

    def test_full_week_no_holidays(self):
        # Mon 00:00 → Sat 00:00 = 5 * 9h * 60 = 2700
        result = business_minutes_between(
            datetime(2026, 10, 19, 0, 0),
            datetime(2026, 10, 25, 0, 0),
            EMPTY_HOLIDAYS,
        )
        assert result == 2700


class TestAddBusinessMinutes:
    """M1/M2: forward projection of business minutes."""

    def test_same_day(self):
        due = add_business_minutes(
            datetime(2026, 10, 19, 9, 30), 240, EMPTY_HOLIDAYS
        )
        assert due == datetime(2026, 10, 19, 13, 30)

    def test_spans_next_day(self):
        # 480 min from Mon 10:00 → Mon 18:00 (8h=480) exactly
        due = add_business_minutes(
            datetime(2026, 10, 19, 10, 0), 480, EMPTY_HOLIDAYS
        )
        assert due == datetime(2026, 10, 19, 18, 0)

    def test_zero_minutes(self):
        dt = datetime(2026, 10, 19, 10, 0)
        assert add_business_minutes(dt, 0, EMPTY_HOLIDAYS) == dt

    def test_negative_raises(self):
        import pytest

        with pytest.raises(ValueError, match="non-negative"):
            add_business_minutes(datetime(2026, 10, 19, 10, 0), -1, EMPTY_HOLIDAYS)


# =================================== M2 ===================================
class TestHolidayExclusion:
    """M2: holidays are excluded from SLA time."""

    def test_holiday_not_counted(self):
        # Thu 2026-11-26 is a holiday
        holidays = {date(2026, 11, 26)}
        # Tue 16:00 → Thu 12:00 (Thu is holiday, so only Tue+Wed):
        # Tue 16-18 = 120, Wed 09-12 = 180 → 300
        result = business_minutes_between(
            datetime(2026, 11, 24, 16, 0),
            datetime(2026, 11, 26, 12, 0),
            holidays,
        )
        assert result == 300

    def test_add_business_minutes_skips_holiday(self):
        holidays = {date(2026, 11, 26)}
        # 480 min from Tue 16:00:
        # Tue: 120 (16-18). Rem: 360.
        # Wed: 540, but 360 ≤ 540 → Wed 15:00
        due = add_business_minutes(
            datetime(2026, 11, 24, 16, 0), 480, holidays
        )
        assert due == datetime(2026, 11, 25, 15, 0)


# =================================== M3 ===================================
class TestOnHoldPause:
    """M3: ON_HOLD status pauses the SLA clock."""

    def test_on_hold_excluded(self):
        ticket = Ticket(
            id="T-HOLD",
            priority="P2",
            assignee_group="Infra",
            created=datetime(2026, 10, 19, 10, 0),
            resolved=datetime(2026, 10, 19, 16, 0),
            status_history=[
                StatusEntry("IN_PROGRESS", datetime(2026, 10, 19, 10, 0)),
                StatusEntry("ON_HOLD", datetime(2026, 10, 19, 12, 0)),
                StatusEntry("IN_PROGRESS", datetime(2026, 10, 19, 14, 0)),
            ],
        )
        results = compute_all_tickets([ticket], DEFAULT_POLICY, EMPTY_HOLIDAYS)
        # Active: 10-12 (120) + 14-16 (120) = 240 min
        assert len(results) == 1
        assert results[0].elapsed_business_minutes == 240

    def test_no_history_full_active(self):
        ticket = Ticket(
            id="T-NOHIST",
            priority="P4",
            assignee_group="HR",
            created=datetime(2026, 10, 19, 9, 0),
            resolved=datetime(2026, 10, 19, 11, 0),
            status_history=[],
        )
        results = compute_all_tickets([ticket], DEFAULT_POLICY, EMPTY_HOLIDAYS)
        assert len(results) == 1
        assert results[0].elapsed_business_minutes == 120


# =================================== M4 ===================================
class TestTicketResult:
    """M4: per-ticket fields."""

    def test_fields_present(self):
        ticket = Ticket(
            id="T-M4",
            priority="P1",
            assignee_group="Net",
            created=datetime(2026, 10, 19, 9, 0),
            resolved=datetime(2026, 10, 19, 13, 0),
            status_history=[
                StatusEntry("OPEN", datetime(2026, 10, 19, 9, 0)),
            ],
        )
        results = compute_all_tickets([ticket], DEFAULT_POLICY, EMPTY_HOLIDAYS)
        r = results[0]
        assert r.ticket_id == "T-M4"
        assert r.elapsed_business_minutes == 240
        assert r.target_minutes == 240
        assert r.due_by == datetime(2026, 10, 19, 13, 0)
        assert not r.breached
        assert r.breach_minutes == 0

    def test_breach_detected(self):
        ticket = Ticket(
            id="T-BREACH",
            priority="P1",
            assignee_group="Net",
            created=datetime(2026, 10, 19, 9, 0),
            resolved=datetime(2026, 10, 19, 17, 0),
            status_history=[
                StatusEntry("OPEN", datetime(2026, 10, 19, 9, 0)),
            ],
        )
        results = compute_all_tickets([ticket], DEFAULT_POLICY, EMPTY_HOLIDAYS)
        r = results[0]
        assert r.breached
        assert r.breach_minutes == 240  # 480 elapsed - 240 target


# =================================== M5 ===================================
class TestSummary:
    """M5: breach % per priority and per group."""

    def test_summary(self):
        tickets = [
            Ticket("T1", "P1", "G1", datetime(2026, 10, 19, 9, 0),
                   datetime(2026, 10, 19, 13, 0),
                   [StatusEntry("OPEN", datetime(2026, 10, 19, 9, 0))]),
            Ticket("T2", "P1", "G1", datetime(2026, 10, 19, 9, 0),
                   datetime(2026, 10, 19, 17, 0),
                   [StatusEntry("OPEN", datetime(2026, 10, 19, 9, 0))]),
            Ticket("T3", "P2", "G2", datetime(2026, 10, 19, 9, 0),
                   datetime(2026, 10, 19, 18, 0),
                   [StatusEntry("OPEN", datetime(2026, 10, 19, 9, 0))]),
        ]
        results = compute_all_tickets(tickets, DEFAULT_POLICY, EMPTY_HOLIDAYS)
        s = build_summary(results)

        # P1: 1/2 breached = 50%
        assert s["by_priority"]["P1"]["breach_pct"] == 50.0
        # P2: 1/1 breached = 100%
        assert s["by_priority"]["P2"]["breach_pct"] == 100.0
        # G1: 1/2 = 50%
        assert s["by_group"]["G1"]["breach_pct"] == 50.0


# =================================== validation ===========================
class TestValidation:
    """Input parsing and validation."""

    def test_parse_tickets_valid(self):
        raw = [
            {
                "id": "T1",
                "priority": "P1",
                "assignee_group": "Net",
                "created": "2026-10-19T09:00:00",
                "resolved": "2026-10-19T10:00:00",
                "status_history": [
                    {"status": "OPEN", "at": "2026-10-19T09:00:00"}
                ],
            }
        ]
        tickets = parse_tickets(raw)
        assert len(tickets) == 1
        assert tickets[0].id == "T1"

    def test_parse_policy_valid(self):
        raw = {
            "priorities": {
                "P1": {"target_hours": 4},
                "P2": {"target_hours": 8},
            },
            "business_hours": {
                "days": [0, 1, 2, 3, 4],
                "start": "09:00",
                "end": "18:00",
            },
        }
        policy = parse_policy(raw)
        assert policy.targets["P1"] == 240

    def test_parse_holidays(self):
        raw = ["2026-01-01", "2026-12-25"]
        h = parse_holidays(raw)
        assert date(2026, 1, 1) in h
        assert date(2026, 12, 25) in h

    def test_invalid_ticket_raises(self):
        import pytest

        raw = [{"id": 123}]  # id must be string
        with pytest.raises(ValueError):
            parse_tickets(raw)


class TestTicketT06Holiday:
    """T06 spans a holiday — integration check."""

    def test_t06_elapsed(self):
        """Tue 16:00 to Fri 12:00 with Thu as holiday.
        Active: Tue 16-18 (120) + Wed 9-18 (540) + Fri 9-12 (180) = 840"""
        ticket = Ticket(
            id="T06",
            priority="P2",
            assignee_group="Infrastructure",
            created=datetime(2026, 11, 24, 16, 0),
            resolved=datetime(2026, 11, 27, 12, 0),
            status_history=[
                StatusEntry("IN_PROGRESS", datetime(2026, 11, 24, 16, 0)),
            ],
        )
        holidays = {date(2026, 11, 26)}
        results = compute_all_tickets([ticket], DEFAULT_POLICY, holidays)
        r = results[0]
        assert r.elapsed_business_minutes == 840
        assert r.breached  # 840 > 480
        assert r.breach_minutes == 360
        assert r.due_by == datetime(2026, 11, 25, 15, 0)