"""Validator tests — corrupt inputs, missing fields, schema errors."""

import unittest

from sla_tracker.validator import validate_tickets, validate_policy, validate_holidays


class TestValidateTickets(unittest.TestCase):
    def test_valid_tickets(self):
        data = [
            {
                "ticket_id": "T-001",
                "priority": "P1",
                "assignee_group": "Network Ops",
                "transitions": [
                    {"timestamp": "2026-10-26T09:00:00", "status": "CREATED"},
                    {"timestamp": "2026-10-26T12:00:00", "status": "RESOLVED"},
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(tickets[0].ticket_id, "T-001")

    def test_missing_ticket_id(self):
        data = [{"priority": "P1", "transitions": []}]
        tickets, errors = validate_tickets(data)
        self.assertEqual(len(tickets), 0)
        self.assertGreater(len(errors), 0)

    def test_missing_transitions(self):
        data = [{"ticket_id": "T-001", "priority": "P1"}]
        tickets, errors = validate_tickets(data)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(len(tickets[0].transitions), 0)

    def test_invalid_transition_timestamp(self):
        data = [
            {
                "ticket_id": "T-002",
                "transitions": [
                    {"timestamp": "not-a-date", "status": "CREATED"}
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        # Ticket still accepted but with 0 valid transitions; errors logged
        self.assertEqual(len(tickets), 1)
        self.assertEqual(len(tickets[0].transitions), 0)
        self.assertGreater(len(errors), 0)

    def test_missing_status_in_transition(self):
        data = [
            {
                "ticket_id": "T-003",
                "transitions": [
                    {"timestamp": "2026-10-26T09:00:00"}
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(len(tickets[0].transitions), 0)

    def test_non_list_input(self):
        tickets, errors = validate_tickets({"not": "a list"})
        self.assertEqual(len(tickets), 0)
        self.assertGreater(len(errors), 0)

    def test_default_priority(self):
        data = [
            {
                "ticket_id": "T-004",
                "transitions": [
                    {"timestamp": "2026-10-26T09:00:00", "status": "CREATED"}
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        self.assertEqual(tickets[0].priority, "P4")

    def test_transitions_sorted_by_time(self):
        data = [
            {
                "ticket_id": "T-005",
                "transitions": [
                    {"timestamp": "2026-10-26T14:00:00", "status": "RESOLVED"},
                    {"timestamp": "2026-10-26T09:00:00", "status": "CREATED"},
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        self.assertEqual(tickets[0].transitions[0].status, "CREATED")
        self.assertEqual(tickets[0].transitions[1].status, "RESOLVED")

    def test_missing_assignee_becomes_unassigned(self):
        data = [
            {
                "ticket_id": "T-006",
                "transitions": [
                    {"timestamp": "2026-10-26T09:00:00", "status": "CREATED"}
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        self.assertEqual(tickets[0].assignee_group, "Unassigned")

    def test_null_assignee_becomes_unassigned(self):
        data = [
            {
                "ticket_id": "T-007",
                "assignee_group": None,
                "transitions": [
                    {"timestamp": "2026-10-26T09:00:00", "status": "CREATED"}
                ],
            }
        ]
        tickets, errors = validate_tickets(data)
        self.assertEqual(tickets[0].assignee_group, "Unassigned")


class TestValidatePolicy(unittest.TestCase):
    def test_valid_policy(self):
        policy, errors = validate_policy({
            "targets": {"P1": 240, "P2": 480, "P3": 1440, "P4": 4320}
        })
        self.assertIsNotNone(policy)
        self.assertEqual(len(errors), 0)

    def test_missing_targets(self):
        policy, errors = validate_policy({})
        self.assertIsNotNone(policy)
        self.assertEqual(policy.targets, {})

    def test_invalid_target_value(self):
        policy, errors = validate_policy({"targets": {"P1": "abc"}})
        self.assertTrue(policy is not None or len(errors) > 0)

    def test_non_dict_policy(self):
        policy, errors = validate_policy([])
        self.assertIsNone(policy)
        self.assertGreater(len(errors), 0)


class TestValidateHolidays(unittest.TestCase):
    def test_valid_holidays_list(self):
        dates, errors = validate_holidays(["2026-01-01", "2026-12-25"])
        self.assertEqual(len(dates), 2)
        self.assertEqual(len(errors), 0)

    def test_valid_holidays_dict(self):
        dates, errors = validate_holidays({"holidays": ["2026-01-01"]})
        self.assertEqual(len(dates), 1)

    def test_invalid_date_format(self):
        dates, errors = validate_holidays(["2026/01/01", "invalid"])
        self.assertEqual(len(dates), 0)
        self.assertEqual(len(errors), 2)

    def test_non_list_holidays(self):
        dates, errors = validate_holidays("not-a-list")
        self.assertEqual(len(dates), 0)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()