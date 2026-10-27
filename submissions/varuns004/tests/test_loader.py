import json
import tempfile
import unittest
from datetime import date, timedelta, timezone
from pathlib import Path

from sla_tracker.loader import parse_holidays, parse_policy, parse_tickets, read_json
from sla_tracker.models import ConfigError
from sla_tracker.timeutil import parse_timestamp, parse_timezone

from .helpers import POLICY, dt

AS_OF = dt(30, 18)


def one(raw, as_of=AS_OF):
    return parse_tickets([raw], POLICY, as_of)


def base(**overrides):
    raw = {"id": "T-1", "priority": "P1", "assignee_group": "Net",
           "created_at": "2026-10-05T10:00:00+05:30"}
    raw.update(overrides)
    return raw


class TicketValidationTest(unittest.TestCase):
    def assertRejected(self, raw, fragment):
        tickets, errors = one(raw)
        self.assertEqual(tickets, [])
        self.assertEqual(len(errors), 1)
        self.assertIn(fragment, errors[0].message)

    def test_valid_ticket(self):
        tickets, errors = one(base())
        self.assertEqual(errors, [])
        self.assertEqual(tickets[0].created_at, dt(5, 10))

    def test_unknown_priority(self):
        self.assertRejected(base(priority="P9"), "priority")

    def test_priority_case_insensitive(self):
        self.assertEqual(one(base(priority=" p2 "))[0][0].priority, "P2")

    def test_missing_id(self):
        raw = base()
        del raw["id"]
        self.assertRejected(raw, "id is required")

    def test_unsafe_id(self):
        self.assertRejected(base(id="../../etc/passwd"), "id is required")

    def test_numeric_id_accepted(self):
        self.assertEqual(one(base(id=42))[0][0].ticket_id, "42")

    def test_bad_timestamp(self):
        self.assertRejected(base(created_at="yesterday"), "created_at")

    def test_overlong_timestamp(self):
        self.assertRejected(base(created_at="2" * 500), "created_at")

    def test_created_after_as_of(self):
        self.assertRejected(base(created_at="2099-01-01T00:00:00Z"), "after the evaluation time")

    def test_event_before_creation(self):
        self.assertRejected(base(status_history=[{"status": "RESOLVED", "at": "2026-10-04T10:00:00+05:30"}]),
                            "before created_at")

    def test_unknown_status(self):
        self.assertRejected(base(status_history=[{"status": "PARTY", "at": "2026-10-05T11:00:00+05:30"}]),
                            "not a known status")

    def test_history_not_list(self):
        self.assertRejected(base(status_history="ON_HOLD"), "must be a list")

    def test_non_object_ticket(self):
        self.assertRejected("hello", "JSON object")

    def test_control_chars_in_group(self):
        self.assertRejected(base(assignee_group="Net\x1b[31m"), "assignee_group")

    def test_missing_group_defaults(self):
        self.assertEqual(one(base(assignee_group=None))[0][0].assignee_group, "UNASSIGNED")

    def test_history_sorted(self):
        raw = base(status_history=[{"status": "RESOLVED", "at": "2026-10-05T13:00:00+05:30"},
                                   {"status": "ON_HOLD", "at": "2026-10-05T11:00:00+05:30"}])
        statuses = [e.status for e in one(raw)[0][0].history]
        self.assertEqual(statuses, ["ON_HOLD", "RESOLVED"])

    def test_duplicate_ids_rejected_but_first_kept(self):
        tickets, errors = parse_tickets([base(), base()], POLICY, AS_OF)
        self.assertEqual(len(tickets), 1)
        self.assertIn("duplicate", errors[0].message)

    def test_bad_ticket_does_not_block_others(self):
        tickets, errors = parse_tickets([base(priority="X"), base(id="T-2")], POLICY, AS_OF)
        self.assertEqual([t.ticket_id for t in tickets], ["T-2"])
        self.assertEqual(len(errors), 1)

    def test_wrapper_object_or_bare_list(self):
        self.assertEqual(len(parse_tickets({"tickets": [base()]}, POLICY, AS_OF)[0]), 1)
        with self.assertRaises(ConfigError):
            parse_tickets({"items": []}, POLICY, AS_OF)


class TimestampTest(unittest.TestCase):
    def test_utc_z_converted_to_policy_zone(self):
        self.assertEqual(parse_timestamp("2026-10-05T04:30:00Z", POLICY.timezone, "x"), dt(5, 10))

    def test_naive_treated_as_policy_zone(self):
        self.assertEqual(parse_timestamp("2026-10-05T10:00:00", POLICY.timezone, "x"), dt(5, 10))

    def test_microseconds_dropped(self):
        self.assertEqual(parse_timestamp("2026-10-05T10:00:00.999+05:30", POLICY.timezone, "x"), dt(5, 10))

    def test_offsets(self):
        self.assertEqual(parse_timezone("UTC"), timezone.utc)
        self.assertEqual(parse_timezone("-0400").utcoffset(None), timedelta(hours=-4))
        for bad in ("", "+25:00", "Mars/Olympus", "../../etc/passwd", 5):
            with self.assertRaises(ConfigError):
                parse_timezone(bad)


class PolicyTest(unittest.TestCase):
    def test_defaults_match_spec(self):
        p = parse_policy({})
        self.assertEqual(dict(p.targets_minutes), {"P1": 240, "P2": 480, "P3": 1440, "P4": 4320})
        self.assertEqual(p.working_days, frozenset(range(5)))
        self.assertIn("ON_HOLD", p.paused_statuses)

    def test_invalid_policies(self):
        cases = [
            [],
            {"business_hours": {"start": "18:00", "end": "09:00"}},
            {"business_hours": {"start": "9am", "end": "18:00"}},
            {"working_days": []},
            {"working_days": ["FUNDAY"]},
            {"targets_hours": {"P1": 0}},
            {"targets_hours": {"P1": -4}},
            {"targets_hours": {"P1": True}},
            {"targets_hours": {"P1": "4"}},
            {"paused_statuses": ["OPEN"]},
            {"at_risk_ratio": 1.5},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ConfigError):
                parse_policy(case)


class HolidayTest(unittest.TestCase):
    def test_formats(self):
        expected = frozenset({date(2026, 10, 2), date(2026, 12, 25)})
        self.assertEqual(parse_holidays(["2026-10-02", "2026-12-25"]), expected)
        self.assertEqual(parse_holidays({"holidays": [{"date": "2026-10-02"}, "2026-12-25", "2026-12-25"]}), expected)

    def test_invalid(self):
        for bad in ({"days": []}, ["2026-02-30"], ["02/10/2026"], [None]):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                parse_holidays(bad)


class ReadJsonTest(unittest.TestCase):
    def write(self, text: str) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / "f.json"
        p.write_text(text, encoding="utf-8")
        return p

    def test_reads_valid(self):
        self.assertEqual(read_json(self.write('{"a": 1}')), {"a": 1})

    def test_missing_file(self):
        with self.assertRaises(ConfigError):
            read_json("does/not/exist.json")

    def test_directory_rejected(self):
        with self.assertRaises(ConfigError):
            read_json(tempfile.mkdtemp())

    def test_invalid_json_message_has_location_only(self):
        with self.assertRaises(ConfigError) as ctx:
            read_json(self.write('{"a": '))
        self.assertIn("line 1", str(ctx.exception))
        self.assertNotIn("Traceback", str(ctx.exception))

    def test_nan_rejected(self):
        with self.assertRaises(ConfigError):
            read_json(self.write('{"a": NaN}'))

    def test_deep_nesting_rejected(self):
        with self.assertRaises(ConfigError):
            read_json(self.write("[" * 100_000 + "]" * 100_000))

    def test_bom_tolerated(self):
        p = self.write("")
        p.write_bytes(b"\xef\xbb\xbf" + json.dumps([1]).encode())
        self.assertEqual(read_json(p), [1])


if __name__ == "__main__":
    unittest.main()

