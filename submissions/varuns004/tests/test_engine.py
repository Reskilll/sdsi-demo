import unittest
from datetime import date

from sla_tracker.engine import evaluate_ticket
from sla_tracker.models import PAUSED, RUNNING, STOPPED

from .helpers import POLICY, calendar, dt, ticket

AS_OF = dt(30, 18)


def run(t, as_of=AS_OF, cal=None):
    return evaluate_ticket(t, POLICY, cal or calendar(), as_of)


class CoreSlaTest(unittest.TestCase):
    def test_resolved_within_target(self):
        r = run(ticket("P1", dt(5, 10), ("RESOLVED", dt(5, 13))))
        self.assertEqual(r.elapsed_seconds, 180 * 60)
        self.assertFalse(r.breached)
        self.assertEqual(r.due_by, dt(5, 14))
        self.assertEqual(r.clock_state, STOPPED)

    def test_breach_across_overnight(self):
        r = run(ticket("P1", dt(5, 16), ("RESOLVED", dt(6, 12))))
        self.assertEqual(r.elapsed_seconds, 300 * 60)
        self.assertTrue(r.breached)
        self.assertEqual(r.breach_seconds, 60 * 60)
        self.assertEqual(r.due_by, dt(6, 11))

    def test_exactly_at_target_is_not_breach(self):
        r = run(ticket("P1", dt(5, 10), ("RESOLVED", dt(5, 14))))
        self.assertFalse(r.breached)
        self.assertEqual(r.breach_seconds, 0)

    def test_one_second_over_is_breach(self):
        r = run(ticket("P1", dt(5, 10), ("RESOLVED", dt(5, 14).replace(second=1))))
        self.assertTrue(r.breached)
        self.assertEqual(r.breach_seconds, 1)

    def test_all_priorities_targets(self):
        for prio, hours in {"P1": 4, "P2": 8, "P3": 24, "P4": 72}.items():
            self.assertEqual(run(ticket(prio, dt(5, 9))).target_seconds, hours * 3600)


class CalendarEdgeTest(unittest.TestCase):
    def test_created_on_weekend(self):
        r = run(ticket("P1", dt(10, 11), ("RESOLVED", dt(12, 12))))
        self.assertEqual(r.elapsed_seconds, 180 * 60)
        self.assertEqual(r.due_by, dt(12, 13))

    def test_created_after_hours(self):
        r = run(ticket("P1", dt(12, 18, 30), ("RESOLVED", dt(13, 12, 30))))
        self.assertEqual(r.elapsed_seconds, 210 * 60)
        self.assertEqual(r.due_by, dt(13, 13))

    def test_holiday_excluded(self):
        cal = calendar(date(2026, 10, 2))
        r = run(ticket("P1", dt(1, 17), ("RESOLVED", dt(5, 10))), cal=cal)
        self.assertEqual(r.elapsed_seconds, 120 * 60)
        self.assertEqual(r.due_by, dt(5, 12))

    def test_holiday_pushes_future_due_date(self):
        cal = calendar(date(2026, 10, 6))
        r = run(ticket("P2", dt(5, 14)), as_of=dt(5, 15), cal=cal)
        self.assertEqual(r.due_by, dt(7, 13))


class OnHoldTest(unittest.TestCase):
    def test_hold_pauses_clock(self):
        r = run(ticket("P1", dt(5, 10), ("ON_HOLD", dt(5, 11)),
                       ("IN_PROGRESS", dt(5, 15)), ("RESOLVED", dt(5, 17))))
        self.assertEqual(r.elapsed_seconds, 180 * 60)
        self.assertEqual(r.paused_seconds, 240 * 60)
        self.assertEqual(r.due_by, dt(5, 18))
        self.assertFalse(r.breached)

    def test_hold_across_weekend(self):
        r = run(ticket("P2", dt(9, 10), ("ON_HOLD", dt(9, 12)),
                       ("IN_PROGRESS", dt(12, 14)), ("RESOLVED", dt(13, 15))))
        self.assertEqual(r.elapsed_seconds, 720 * 60)
        self.assertEqual(r.breach_seconds, 240 * 60)
        self.assertEqual(r.due_by, dt(13, 11))

    def test_repeated_hold_events_are_idempotent(self):
        r = run(ticket("P1", dt(5, 10), ("ON_HOLD", dt(5, 11)), ("ON_HOLD", dt(5, 12)),
                       ("IN_PROGRESS", dt(5, 13)), ("RESOLVED", dt(5, 14))))
        self.assertEqual(r.elapsed_seconds, 120 * 60)

    def test_currently_on_hold_projects_due_from_as_of(self):
        r = run(ticket("P1", dt(5, 10), ("ON_HOLD", dt(5, 12))), as_of=dt(6, 10))
        self.assertEqual(r.clock_state, PAUSED)
        self.assertEqual(r.elapsed_seconds, 120 * 60)
        self.assertEqual(r.due_by, dt(6, 12))

    def test_hold_from_creation(self):
        r = run(ticket("P1", dt(5, 10), ("ON_HOLD", dt(5, 10)),
                       ("IN_PROGRESS", dt(6, 10)), ("RESOLVED", dt(6, 11))))
        self.assertEqual(r.elapsed_seconds, 60 * 60)


class LifecycleTest(unittest.TestCase):
    def test_open_ticket_measured_to_as_of(self):
        r = run(ticket("P3", dt(5, 9)), as_of=dt(7, 12))
        self.assertEqual(r.clock_state, RUNNING)
        self.assertEqual(r.elapsed_seconds, 1260 * 60)
        self.assertEqual(r.remaining_seconds, 180 * 60)
        self.assertEqual(r.due_by, dt(7, 15))
        self.assertTrue(r.at_risk)

    def test_open_ticket_already_breached(self):
        r = run(ticket("P1", dt(5, 9)), as_of=dt(5, 15))
        self.assertTrue(r.breached)
        self.assertFalse(r.at_risk)
        self.assertEqual(r.due_by, dt(5, 13))

    def test_reopen_resumes_clock(self):
        r = run(ticket("P1", dt(5, 10), ("RESOLVED", dt(5, 11)),
                       ("REOPENED", dt(5, 15)), ("RESOLVED", dt(5, 17))))
        self.assertEqual(r.elapsed_seconds, 180 * 60)
        self.assertEqual(r.clock_state, STOPPED)

    def test_events_after_as_of_ignored(self):
        r = run(ticket("P1", dt(5, 10), ("RESOLVED", dt(5, 16))), as_of=dt(5, 12))
        self.assertEqual(r.elapsed_seconds, 120 * 60)
        self.assertEqual(r.clock_state, RUNNING)

    def test_resolved_ticket_not_at_risk(self):
        r = run(ticket("P1", dt(5, 10), ("RESOLVED", dt(5, 13, 50))))
        self.assertFalse(r.at_risk)

    def test_as_of_equal_to_created(self):
        r = run(ticket("P1", dt(5, 10)), as_of=dt(5, 10))
        self.assertEqual(r.elapsed_seconds, 0)
        self.assertEqual(r.due_by, dt(5, 14))


if __name__ == "__main__":
    unittest.main()

