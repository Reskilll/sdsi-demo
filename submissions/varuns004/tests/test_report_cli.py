import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from sla_tracker.cli import main
from sla_tracker.engine import evaluate_ticket
from sla_tracker.report import build_report, render_csv, render_table, summarize

from .helpers import POLICY, calendar, dt, ticket

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "sample_data"
AS_OF = "2026-10-16T18:00:00+05:30"


def result(prio, group, resolved_hour, tid):
    t = ticket(prio, dt(5, 9), ("RESOLVED", dt(5, resolved_hour)), group=group, tid=tid)
    return evaluate_ticket(t, POLICY, calendar(), dt(30, 18))


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.results = [
            result("P1", "Net", 12, "A"),   # 180 min, ok
            result("P1", "Net", 15, "B"),   # 360 min, breach
            result("P1", "Db", 16, "C"),    # breach
            result("P2", "Db", 12, "D"),    # ok
        ]

    def test_breach_pct_per_priority_and_group(self):
        s = summarize(self.results, ["P1", "P2", "P3"])
        self.assertEqual(s["by_priority"]["P1"]["breach_pct"], 66.67)
        self.assertEqual(s["by_priority"]["P2"]["breach_pct"], 0.0)
        self.assertEqual(s["by_assignee_group"]["Net"]["breach_pct"], 50.0)
        self.assertEqual(s["by_assignee_group"]["Db"]["breach_pct"], 50.0)
        self.assertEqual(s["overall"]["breach_pct"], 50.0)

    def test_empty_priority_has_null_pct(self):
        s = summarize(self.results, ["P1", "P2", "P3"])
        self.assertEqual(s["by_priority"]["P3"]["total"], 0)
        self.assertIsNone(s["by_priority"]["P3"]["breach_pct"])

    def test_no_tickets(self):
        s = summarize([], ["P1"])
        self.assertEqual(s["overall"]["total"], 0)
        self.assertIsNone(s["overall"]["breach_pct"])
        self.assertIn("Overall: 0/0", render_table(build_report([], [], POLICY, dt(5, 9))))

    def test_csv_formula_injection_neutralised(self):
        r = result("P1", "=cmd|' /C calc'!A0", 12, "X")
        rows = list(csv.reader(io.StringIO(render_csv(build_report([r], [], POLICY, dt(30, 18))))))
        self.assertTrue(rows[1][2].startswith("'="))


class CliTest(unittest.TestCase):
    def cli(self, *extra, tickets="tickets.json"):
        out, err = io.StringIO(), io.StringIO()
        args = ["--tickets", str(DATA / tickets), "--policy", str(DATA / "sla_policy.json"),
                "--holidays", str(DATA / "holidays.json"), "--as-of", AS_OF, *extra]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_sample_json_end_to_end(self):
        code, out, _ = self.cli("--format", "json")
        self.assertEqual(code, 0)
        report = json.loads(out)
        by_id = {t["ticket_id"]: t for t in report["tickets"]}
        self.assertEqual(len(by_id), 12)
        self.assertEqual(by_id["INC-1003"]["breach_minutes"], 240)
        self.assertEqual(by_id["INC-1004"]["elapsed_business_minutes"], 720)  # holiday skipped
        self.assertEqual(by_id["INC-1006"]["clock_state"], "PAUSED")
        self.assertEqual(by_id["INC-1008"]["breached"], False)  # exactly at target
        self.assertEqual(by_id["INC-1012"]["elapsed_business_minutes"], 120)  # unsorted history
        self.assertEqual(report["summary"]["by_priority"]["P1"]["breach_pct"], 25.0)

    def test_table_and_csv(self):
        self.assertIn("Summary by assignee group", self.cli()[1])
        self.assertTrue(self.cli("--format", "csv")[1].startswith("ticket_id,"))

    def test_output_file(self):
        target = Path(tempfile.mkdtemp()) / "report.json"
        code, out, _ = self.cli("--format", "json", "--output", str(target))
        self.assertEqual((code, out), (0, ""))
        self.assertIn("summary", json.loads(target.read_text(encoding="utf-8")))

    def test_fail_on_breach(self):
        self.assertEqual(self.cli("--fail-on-breach")[0], 1)

    def test_invalid_tickets_reported_not_fatal(self):
        code, _, err = self.cli(tickets="invalid_tickets.json")
        self.assertEqual(code, 0)
        self.assertIn("duplicate ticket id", err)
        self.assertEqual(self.cli("--strict", tickets="invalid_tickets.json")[0], 2)

    def test_missing_file_is_clean_error(self):
        code, _, err = self.cli(tickets="nope.json")
        self.assertEqual(code, 2)
        self.assertIn("error: input file not found", err)
        self.assertNotIn("Traceback", err)

    def test_bad_as_of(self):
        code, _, err = self.cli("--as-of", "soon")
        self.assertEqual(code, 2)
        self.assertIn("--as-of", err)


if __name__ == "__main__":
    unittest.main()

