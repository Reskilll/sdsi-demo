"""Priority and assignee group aggregation tests — M5."""

import unittest
from datetime import datetime

from sla_tracker.models import TicketSLAResult
from sla_tracker.analytics import compute_analytics


def make_result(ticket_id, priority, group, elapsed, target, breached, breach_min=0.0):
    return TicketSLAResult(
        ticket_id=ticket_id,
        priority=priority,
        assignee_group=group,
        sla_target_minutes=target,
        elapsed_business_minutes=elapsed,
        due_by=datetime(2026, 10, 26, 12, 0),
        is_breached=breached,
        breach_minutes=breach_min,
        as_of=datetime(2026, 10, 26, 12, 0),
    )


class TestAnalyticsAggregation(unittest.TestCase):
    def setUp(self):
        self.results = [
            make_result("T1", "P1", "Network Ops", 100, 240, False),
            make_result("T2", "P1", "Network Ops", 300, 240, True, 60),
            make_result("T3", "P1", "Security Team", 400, 240, True, 160),
            make_result("T4", "P2", "Network Ops", 200, 480, False),
            make_result("T5", "P2", "Security Team", 600, 480, True, 120),
        ]

    def test_by_priority(self):
        a = compute_analytics(self.results)
        bp = a.by_priority
        # P1: 3 tickets, 2 breached → 66.67%
        self.assertEqual(bp["P1"]["total"], 3)
        self.assertEqual(bp["P1"]["breached"], 2)
        self.assertAlmostEqual(bp["P1"]["breach_rate_pct"], 66.67, places=1)
        # P2: 2 tickets, 1 breached → 50%
        self.assertEqual(bp["P2"]["total"], 2)
        self.assertEqual(bp["P2"]["breached"], 1)
        self.assertEqual(bp["P2"]["breach_rate_pct"], 50.0)

    def test_by_assignee_group(self):
        a = compute_analytics(self.results)
        bg = a.by_assignee_group
        # Network Ops: 3 tickets, 1 breached → 33.33%
        self.assertEqual(bg["Network Ops"]["total"], 3)
        self.assertEqual(bg["Network Ops"]["breached"], 1)
        self.assertAlmostEqual(bg["Network Ops"]["breach_rate_pct"], 33.33, places=1)
        # Security Team: 2 tickets, 2 breached → 100%
        self.assertEqual(bg["Security Team"]["total"], 2)
        self.assertEqual(bg["Security Team"]["breached"], 2)
        self.assertEqual(bg["Security Team"]["breach_rate_pct"], 100.0)

    def test_overall(self):
        a = compute_analytics(self.results)
        o = a.overall
        self.assertEqual(o["total_tickets"], 5)
        self.assertEqual(o["breached"], 3)
        self.assertEqual(o["breach_rate_pct"], 60.0)
        self.assertGreater(o["avg_elapsed_minutes"], 0)

    def test_empty_results(self):
        a = compute_analytics([])
        self.assertEqual(a.overall["total_tickets"], 0)
        self.assertEqual(a.overall["breach_rate_pct"], 0.0)
        self.assertEqual(a.by_priority, {})
        self.assertEqual(a.by_assignee_group, {})

    def test_max_breach(self):
        a = compute_analytics(self.results)
        # Max breach: T3 with 160 min
        self.assertEqual(a.overall["max_breach_minutes"], 160.0)

    def test_no_breaches(self):
        results = [
            make_result("T1", "P4", "App Support", 100, 4320, False),
        ]
        a = compute_analytics(results)
        self.assertEqual(a.overall["breached"], 0)
        self.assertEqual(a.overall["breach_rate_pct"], 0.0)
        self.assertEqual(a.overall["max_breach_minutes"], 0.0)
        self.assertEqual(a.overall["avg_breach_minutes"], 0.0)


if __name__ == "__main__":
    unittest.main()