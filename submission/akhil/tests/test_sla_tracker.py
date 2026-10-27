import unittest
from datetime import date, datetime

from sla_tracker import SLAInputError, evaluate, parse_holidays, parse_policy


POLICY = parse_policy(
    {
        "timezone": "UTC",
        "business_days": [0, 1, 2, 3, 4],
        "business_hours": {"start": "09:00", "end": "18:00"},
        "priority_hours": {"P1": 4, "P2": 8, "P3": 24, "P4": 72},
    }
)


class BusinessTimeTests(unittest.TestCase):
    def evaluate_one(self, ticket, holidays=(), as_of="2026-01-08T12:00:00Z"):
        return evaluate(
            [ticket],
            POLICY,
            frozenset(date.fromisoformat(day) for day in holidays),
            datetime.fromisoformat(as_of.replace("Z", "+00:00")),
        )["tickets"][0]

    def test_weekend_is_excluded_and_due_time_crosses_to_monday(self):
        result = self.evaluate_one(
            {
                "ticket_id": "WEEKEND",
                "priority": "P2",
                "created_at": "2026-01-02T17:00:00Z",
                "resolved_at": "2026-01-05T10:00:00Z",
            }
        )
        self.assertEqual(result["elapsed_business_minutes"], 120)
        self.assertEqual(result["due_by"], "2026-01-05T16:00:00+00:00")
        self.assertFalse(result["breached"])

    def test_holiday_is_excluded_from_elapsed_time_and_due_time(self):
        result = self.evaluate_one(
            {
                "ticket_id": "HOLIDAY",
                "priority": "P3",
                "created_at": "2026-01-05T09:00:00Z",
                "resolved_at": "2026-01-07T10:00:00Z",
            },
            holidays=["2026-01-06"],
        )
        self.assertEqual(result["elapsed_business_minutes"], 600)
        self.assertEqual(result["due_by"], "2026-01-08T15:00:00+00:00")

    def test_on_hold_pauses_clock_and_moves_due_time(self):
        result = self.evaluate_one(
            {
                "ticket_id": "PAUSED",
                "priority": "P1",
                "created_at": "2026-01-05T09:00:00Z",
                "resolved_at": "2026-01-06T11:00:00Z",
                "status_history": [
                    {"timestamp": "2026-01-05T11:00:00Z", "status": "ON_HOLD"},
                    {"timestamp": "2026-01-06T10:00:00Z", "status": "IN_PROGRESS"},
                    {"timestamp": "2026-01-06T11:00:00Z", "status": "RESOLVED"},
                ],
            }
        )
        self.assertEqual(result["elapsed_business_minutes"], 180)
        self.assertEqual(result["due_by"], "2026-01-06T12:00:00+00:00")
        self.assertFalse(result["breached"])

    def test_active_on_hold_projects_due_time_from_as_of(self):
        result = self.evaluate_one(
            {
                "ticket_id": "ACTIVE-HOLD",
                "priority": "P1",
                "created_at": "2026-01-05T09:00:00Z",
                "status_history": [
                    {"timestamp": "2026-01-05T11:00:00Z", "status": "ON_HOLD"}
                ],
            },
            as_of="2026-01-06T10:00:00Z",
        )
        self.assertEqual(result["elapsed_business_minutes"], 120)
        self.assertEqual(result["due_by"], "2026-01-06T12:00:00+00:00")
        self.assertFalse(result["breached"])

    def test_breach_metrics_are_grouped_by_priority_and_assignee(self):
        report = evaluate(
            [
                {
                    "ticket_id": "BREACH",
                    "priority": "P1",
                    "assignee_group": "Network",
                    "created_at": "2026-01-05T09:00:00Z",
                    "resolved_at": "2026-01-05T15:00:00Z",
                },
                {
                    "ticket_id": "OK",
                    "priority": "P1",
                    "assignee_group": "Network",
                    "created_at": "2026-01-05T09:00:00Z",
                    "resolved_at": "2026-01-05T10:00:00Z",
                },
            ],
            POLICY,
            frozenset(),
            datetime.fromisoformat("2026-01-08T12:00:00+00:00"),
        )
        self.assertEqual(report["summary"]["by_priority"]["P1"]["breach_percent"], 50.0)
        self.assertEqual(report["summary"]["by_assignee_group"]["Network"]["breach_count"], 1)
        self.assertEqual(report["tickets"][0]["breach_minutes"], 120)

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(SLAInputError, "timezone"):
            self.evaluate_one(
                {
                    "ticket_id": "BAD-TIME",
                    "priority": "P1",
                    "created_at": "2026-01-05T09:00:00",
                }
            )

    def test_holiday_file_accepts_wrapped_array(self):
        self.assertEqual(parse_holidays({"holidays": ["2026-01-06"]}), frozenset({date(2026, 1, 6)}))


if __name__ == "__main__":
    unittest.main()