"""Contract tests for the ``run()`` entry point (`agent.py`).

Run from the repo root::

    python -m unittest submissions/imakash93/test_agent.py -v
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from agent import reset_state, run


def _json_file(products) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"products": products}, handle)
    return path


SAMPLE = [
    {"sku": "A", "stock": 10, "limit_per_user": 2},
    {"sku": "B", "stock": 5,  "limit_per_user": 1},
]


class ContractTest(unittest.TestCase):

    def setUp(self) -> None:
        reset_state()
        self.inv_path = _json_file(SAMPLE)
        self.addCleanup(os.unlink, self.inv_path)

    def _r(self, obj) -> dict:
        """Shorthand: json-dump → run → return result dict."""
        return run(json.dumps(obj))

    # ── parse / validation ──────────────────────────────────────────

    def test_non_json_task_escalates(self):
        result = run("not json")
        self.assertTrue(result["escalated"])
        self.assertIsNone(result["result"])
        self.assertEqual("fail", result["plan"][0]["status"])

    def test_non_object_task_escalates(self):
        result = run(json.dumps([1, 2, 3]))
        self.assertTrue(result["escalated"])
        self.assertIsNone(result["result"])

    def test_unknown_action_rejected_no_escalation(self):
        result = self._r({"action": "dance"})
        self.assertFalse(result["escalated"])
        self.assertEqual("rejected", result["result"]["status"])
        self.assertEqual("UNKNOWN_ACTION", result["result"]["code"])

    # ── full lifecycle ──────────────────────────────────────────────

    def test_full_lifecycle(self):
        # load
        r = self._r({"action": "load", "file": self.inv_path})
        self.assertEqual("ok", r["result"]["status"])
        self.assertEqual(2, r["result"]["products_loaded"])

        # reserve
        r = self._r({"action": "reserve", "user": "alice", "sku": "A", "qty": 2})
        self.assertEqual("ok", r["result"]["status"])
        rid = r["result"]["reservation_id"]
        self.assertEqual(2, r["result"]["qty"])

        # confirm
        r = self._r({"action": "confirm", "reservation_id": rid})
        self.assertEqual("ok", r["result"]["status"])

        # report
        r = self._r({"action": "report", "sku": "A"})
        item = r["result"]["items"][0]
        self.assertEqual(8, item["available"])
        self.assertEqual(0, item["reserved"])
        self.assertEqual(2, item["sold"])

    def test_reserve_fails_insufficient_stock(self):
        self._r({"action": "load", "file": self.inv_path})
        r = self._r({"action": "reserve", "user": "bob", "sku": "B", "qty": 100})
        self.assertEqual("rejected", r["result"]["status"])
        self.assertEqual("INSUFFICIENT_STOCK", r["result"]["code"])
        self.assertFalse(r["escalated"])

    def test_reserve_missing_params(self):
        self._r({"action": "load", "file": self.inv_path})
        r = self._r({"action": "reserve"})
        self.assertEqual("rejected", r["result"]["status"])

    def test_ttl_zero_expiry_via_run(self):
        """ttl=0 causes immediate expiry — confirm should fail with EXPIRED."""
        self._r({"action": "load", "file": self.inv_path})
        res = self._r({"action": "reserve", "user": "carol", "sku": "A", "qty": 1, "ttl": 0})
        rid = res["result"]["reservation_id"]
        confirm = self._r({"action": "confirm", "reservation_id": rid})
        self.assertEqual("rejected", confirm["result"]["status"])
        self.assertEqual("EXPIRED", confirm["result"]["code"])

    def test_limit_exceeded_via_run(self):
        self._r({"action": "load", "file": self.inv_path})
        self._r({"action": "reserve", "user": "alice", "sku": "A", "qty": 2})
        res = self._r({"action": "confirm", "user": "alice", "sku": "A"})
        self.assertEqual("ok", res["result"]["status"])
        # alice now has 2 confirmed → at limit
        res = self._r({"action": "reserve", "user": "alice", "sku": "A", "qty": 1})
        self.assertEqual("LIMIT_EXCEEDED", res["result"]["code"])

    # ── sanitization ────────────────────────────────────────────────

    def test_control_chars_stripped_from_display(self):
        """User IDs with newlines are sanitized in results and plan."""
        self._r({"action": "load", "file": self.inv_path})
        r = self._r({"action": "reserve", "user": "bad\nuser\r", "sku": "A", "qty": 1})
        user_out = r["result"]["user"]
        self.assertNotIn("\n", user_out)
        self.assertNotIn("\r", user_out)
        # plan steps should also be clean
        for step in r["plan"]:
            if step.get("detail"):
                self.assertNotIn("\n", str(step["detail"]))

    # ── load edge cases via run ─────────────────────────────────────

    def test_load_file_not_found_escalates(self):
        r = self._r({"action": "load", "file": "no_such_file.json"})
        self.assertTrue(r["escalated"])
        self.assertEqual("error", r["result"]["status"])
        self.assertEqual("INVENTORY_NOT_FOUND", r["result"]["code"])

    def test_load_path_traversal_rejected(self):
        r = self._r({"action": "load", "file": "../../etc/passwd"})
        self.assertTrue(r["escalated"])
        self.assertEqual("INVENTORY_PATH_TRAVERSAL", r["result"]["code"])

    # ── confirm/cancel run-level fallbacks ──────────────────────────

    def test_cancel_by_user_sku_works(self):
        self._r({"action": "load", "file": self.inv_path})
        self._r({"action": "reserve", "user": "dave", "sku": "A", "qty": 1})
        r = self._r({"action": "cancel", "user": "dave", "sku": "A"})
        self.assertEqual("ok", r["result"]["status"])

    def test_report_all_action(self):
        self._r({"action": "load", "file": self.inv_path})
        r = self._r({"action": "report"})
        self.assertEqual("ok", r["result"]["status"])
        self.assertEqual(2, len(r["result"]["items"]))