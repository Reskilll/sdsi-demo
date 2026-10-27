"""Core SLA calculation unit tests — M1-M4."""

import unittest
from datetime import datetime, timezone

from sla_tracker.models import Ticket, StatusTransition, SLAPolicy, TicketSLAResult
from sla_tracker.calendar import HolidayCalendar
from sla_tracker.engine import compute_ticket_sla


POLICY = SLAPolicy(targets={"P1": 240, "P2": 480, "P3": 1440, "P4": 4320})
NO_HOLIDAYS = HolidayCalendar()


class TestSimpleSLA(unittest.TestCase):
    """M1: Basic SLA calculation without pauses."""

    def test_p1_within_sla(self):
        ticket = Ticket(
            ticket_id="T-001",
            priority="P1",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 11, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        self.assertEqual(result.elapsed_business_minutes, 120)
        self.assertFalse(result.is_breached)
        self.assertEqual(result.breach_minutes, 0)

    def test_p1_breached(self):
        ticket = Ticket(
            ticket_id="T-002",
            priority="P1",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 15, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        self.assertEqual(result.elapsed_business_minutes, 360)
        self.assertTrue(result.is_breached)
        self.assertEqual(result.breach_minutes, 120)

    def test_p4_within_sla(self):
        ticket = Ticket(
            ticket_id="T-003",
            priority="P4",
            assignee_group="App Support",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 27, 12, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Mon 09-18 (540) + Tue 09-12 (180) = 720 min
        self.assertEqual(result.elapsed_business_minutes, 720)
        self.assertFalse(result.is_breached)


class TestOnHoldPause(unittest.TestCase):
    """M3: Pause SLA while ticket is ON_HOLD."""

    def test_simple_on_hold(self):
        ticket = Ticket(
            ticket_id="T-010",
            priority="P2",
            assignee_group="Infrastructure",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 9, 30), "IN_PROGRESS"),
                StatusTransition(datetime(2026, 10, 26, 10, 0), "ON_HOLD"),
                StatusTransition(datetime(2026, 10, 26, 11, 0), "IN_PROGRESS"),
                StatusTransition(datetime(2026, 10, 26, 14, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Active: 09:00-09:30 (30) + 09:30-10:00 (30) + 11:00-14:00 (180) = 240
        # Paused: 10:00-11:00 (60 min wall clock, excluded from business)
        self.assertEqual(result.elapsed_business_minutes, 240)
        self.assertEqual(result.total_paused_minutes, 60)

    def test_ec3_on_hold_over_weekend(self):
        """Ticket paused Friday 17:00 and resumed Monday 10:00.
        Wall clock elapsed = 65 hrs, business pause = 2 hrs (1h Fri + 1h Mon)."""
        ticket = Ticket(
            ticket_id="T-020",
            priority="P3",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 30, 9, 0), "CREATED"),   # Fri
                StatusTransition(datetime(2026, 10, 30, 9, 30), "IN_PROGRESS"),
                StatusTransition(datetime(2026, 10, 30, 17, 0), "ON_HOLD"),   # Fri 17:00
                StatusTransition(datetime(2026, 11, 2, 10, 0), "IN_PROGRESS"), # Mon 10:00
                StatusTransition(datetime(2026, 11, 2, 11, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Active: 09:00-09:30 (30) + 09:30-17:00 (450) + 10:00-11:00 Mon (60) = 540 min
        self.assertEqual(result.elapsed_business_minutes, 540)
        self.assertFalse(result.is_breached)

    def test_ec6_created_on_hold(self):
        ticket = Ticket(
            ticket_id="T-030",
            priority="P2",
            assignee_group="Security Team",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 9, 1), "ON_HOLD"),
                StatusTransition(datetime(2026, 10, 26, 12, 0), "IN_PROGRESS"),
                StatusTransition(datetime(2026, 10, 26, 14, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Active: only 12:00-14:00 = 120 min
        self.assertEqual(result.elapsed_business_minutes, 121)  # 09:00→09:01 (1) + 12:00→14:00 (120)
        self.assertEqual(result.total_paused_minutes, 179)  # 09:01→12:00 wall clock


class TestEdgeCaseCreatedResolved(unittest.TestCase):
    """EC1, EC2: Created/resolved outside business hours."""

    def test_ec1_created_weekend(self):
        ticket = Ticket(
            ticket_id="T-040",
            priority="P2",
            assignee_group="DB Admin",
            transitions=[
                StatusTransition(datetime(2026, 10, 25, 14, 0), "CREATED"),  # Sunday
                StatusTransition(datetime(2026, 10, 26, 11, 0), "RESOLVED"),  # Monday
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Active: Sunday 14:00 → Monday 11:00. Business time: Mon 09-11 = 120 min
        self.assertEqual(result.elapsed_business_minutes, 120)
        self.assertFalse(result.is_breached)

    def test_ec2_resolved_weekend(self):
        ticket = Ticket(
            ticket_id="T-041",
            priority="P3",
            assignee_group="App Support",
            transitions=[
                StatusTransition(datetime(2026, 10, 30, 14, 0), "CREATED"),  # Friday
                StatusTransition(datetime(2026, 10, 31, 12, 0), "RESOLVED"),  # Saturday
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Active: Fri 14:00→18:00 = 240 min. Sat = 0 business min.
        self.assertEqual(result.elapsed_business_minutes, 240)
        self.assertFalse(result.is_breached)

    def test_created_after_hours_weekday(self):
        ticket = Ticket(
            ticket_id="T-042",
            priority="P1",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 21, 0), "CREATED"),  # Monday night
                StatusTransition(datetime(2026, 10, 27, 10, 0), "RESOLVED"),  # Tuesday
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        # Active: Tue 09-10 = 60 min
        self.assertEqual(result.elapsed_business_minutes, 60)


class TestOpenTicket(unittest.TestCase):
    """EC5: Open / in-flight tickets."""

    def test_open_ticket_not_breached(self):
        ticket = Ticket(
            ticket_id="T-050",
            priority="P4",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 10, 0), "IN_PROGRESS"),
            ],
        )
        as_of = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS, as_of=as_of)
        # Active: 09:00→12:00 = 180 min
        self.assertEqual(result.elapsed_business_minutes, 180)
        self.assertFalse(result.is_breached)
        self.assertIsNone(result.resolved_at)

    def test_open_ticket_already_breached(self):
        ticket = Ticket(
            ticket_id="T-051",
            priority="P1",
            assignee_group="DB Admin",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
            ],
        )
        as_of = datetime(2026, 10, 26, 16, 0, tzinfo=timezone.utc)
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS, as_of=as_of)
        # Active: 09:00→16:00 = 420 min, P1 target = 240
        self.assertTrue(result.is_breached)
        self.assertEqual(result.breach_minutes, 180)

    def test_ec7_unassigned_missing_group(self):
        ticket = Ticket(
            ticket_id="T-052",
            priority="P2",
            assignee_group=None,
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 12, 0), "RESOLVED"),
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS)
        self.assertEqual(result.assignee_group, "Unassigned")


class TestDueBy(unittest.TestCase):
    """M4: Due-by time projection."""

    def test_due_by_same_day(self):
        ticket = Ticket(
            ticket_id="T-100",
            priority="P1",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
            ],
        )
        as_of = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS, as_of=as_of)
        # P1 = 240 min from 09:00 = 13:00 same day
        self.assertEqual(result.due_by.hour, 13)
        self.assertEqual(result.due_by.minute, 0)

    def test_due_by_with_pause(self):
        ticket = Ticket(
            ticket_id="T-101",
            priority="P1",
            assignee_group="Network Ops",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),
                StatusTransition(datetime(2026, 10, 26, 10, 0), "ON_HOLD"),
                StatusTransition(datetime(2026, 10, 26, 11, 0), "IN_PROGRESS"),
            ],
        )
        as_of = datetime(2026, 10, 26, 11, 0, tzinfo=timezone.utc)
        result = compute_ticket_sla(ticket, POLICY, NO_HOLIDAYS, as_of=as_of)
        # Active only: 09:00-10:00 (60 min), P1=240 → 180 min remaining
        # Pause: 10:00-11:00 wall clock (60 min) shifts due-by
        # Base due: 09:00 + 240 business min → 13:00
        # Shift: 13:00 + 60 min → 14:00
        self.assertEqual(result.due_by.hour, 14)


class TestHolidayIntegration(unittest.TestCase):
    """M2: Holiday exclusion."""

    def test_holiday_excludes_business_time(self):
        holidays = HolidayCalendar(["2026-10-27"])  # Tuesday
        ticket = Ticket(
            ticket_id="T-200",
            priority="P2",
            assignee_group="Infrastructure",
            transitions=[
                StatusTransition(datetime(2026, 10, 26, 9, 0), "CREATED"),  # Monday
                StatusTransition(datetime(2026, 10, 28, 12, 0), "RESOLVED"),  # Wednesday
            ],
        )
        result = compute_ticket_sla(ticket, POLICY, holidays)
        # Mon full (540) + Tue holiday (0) + Wed 09-12 (180) = 720
        self.assertEqual(result.elapsed_business_minutes, 720)
        self.assertTrue(result.is_breached)  # P2 target = 480


if __name__ == "__main__":
    unittest.main()