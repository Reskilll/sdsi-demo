"""Engine-level tests — every must-have (M1–M5) and the 23 inferred edge cases.

Run from the repo root::

    python -m unittest submissions/imakash93/test_engine.py -v
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from engine import BusinessError, ReservationSystem, SystemError

# ------------------------------------------------------------------ helpers


class FakeClock:
    """Controllable clock so TTL expiry is testable without sleeping."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _json_file(products) -> str:
    """Write a temporary inventory JSON file, returning its path."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"products": products}, handle)
    return path


def _sample_products():
    return [
        {"sku": "A", "name": "Item A", "stock": 10, "limit_per_user": 3},
        {"sku": "B", "name": "Item B", "stock": 5,  "limit_per_user": 2},
        {"sku": "C", "name": "Item C", "stock": 1,  "limit_per_user": None},
    ]


class EngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.sys = ReservationSystem(clock=self.clock)

    def _load(self, products=None) -> dict:
        products = _sample_products() if products is None else products
        path = _json_file(products)
        self.addCleanup(os.unlink, path)
        return self.sys.load(path)


# -------------------------------------------------------------- must-haves


class MustHaveTests(EngineTestCase):
    """M1–M5 from the problem statement."""

    def test_m1_load_products_from_file(self):
        """M1: load reads stock counts correctly."""
        result = self._load()
        self.assertEqual("ok", result["status"])
        self.assertEqual(3, result["products_loaded"])
        report = self.sys.report()
        items = {i["sku"]: i for i in report["items"]}
        self.assertEqual(10, items["A"]["stock"])
        self.assertEqual(5, items["B"]["stock"])
        self.assertEqual(1, items["C"]["stock"])

    def test_m2_reserve_holds_stock_with_ttl(self):
        """M2: reserve moves stock to reserved and sets TTL."""
        self._load()
        result = self.sys.reserve("alice", "A", 2)
        self.assertEqual("ok", result["status"])
        self.assertIn("reservation_id", result)
        self.assertEqual(2, result["qty"])
        # TTL default 120 s
        self.assertAlmostEqual(
            self.clock.now + 120, result["expires_at"], delta=0.01,
        )
        report = self.sys.report("A")["items"][0]
        self.assertEqual(8, report["available"])
        self.assertEqual(2, report["reserved"])
        self.assertEqual(0, report["sold"])

    def test_m3a_confirm_permanently_deducts(self):
        """M3: confirm transfers reserved → sold (available unchanged)."""
        self._load()
        rid = self.sys.reserve("alice", "A", 2)["reservation_id"]
        self.sys.confirm(rid)
        report = self.sys.report("A")["items"][0]
        self.assertEqual(8, report["available"])
        self.assertEqual(0, report["reserved"])
        self.assertEqual(2, report["sold"])

    def test_m3b_cancel_releases_stock(self):
        """M3: cancel returns reserved stock to available."""
        self._load()
        rid = self.sys.reserve("alice", "A", 2)["reservation_id"]
        self.sys.cancel(rid)
        report = self.sys.report("A")["items"][0]
        self.assertEqual(10, report["available"])
        self.assertEqual(0, report["reserved"])
        self.assertEqual(0, report["sold"])

    def test_m3c_ttl_expiry_releases_stock(self):
        """M3: a reservation that times out releases automatically."""
        self._load()
        self.sys.reserve("alice", "A", 2, ttl=60)
        # before expiry — stock still reserved
        self.clock.advance(30)
        report = self.sys.report("A")["items"][0]
        self.assertEqual(8, report["available"])
        self.assertEqual(2, report["reserved"])
        # after expiry
        self.clock.advance(31)
        report = self.sys.report("A")["items"][0]
        self.assertEqual(10, report["available"])
        self.assertEqual(0, report["reserved"])

    def test_m4_per_user_purchase_limit(self):
        """M4: reserve refuses when user would exceed their per-SKU cap."""
        self._load()
        # alice has limit 3 for SKU A
        self.sys.reserve("alice", "A", 1)
        rid = self.sys.reserve("alice", "A", 2)["reservation_id"]
        self.sys.confirm(rid)  # confirmed total = 3 (reserve #1 still active)
        # alice now has 1 reserved + 2 confirmed = 3 committed → at limit
        with self.assertRaises(BusinessError) as ctx:
            self.sys.reserve("alice", "A", 1)
        self.assertEqual("LIMIT_EXCEEDED", ctx.exception.code)

    def test_m4_limit_released_after_cancel(self):
        """M4: cancelling a reservation frees limit capacity."""
        self._load()
        rid = self.sys.reserve("alice", "A", 3)["reservation_id"]
        self.sys.cancel(rid)
        # now 0 committed → can reserve again
        self.sys.reserve("alice", "A", 3)

    def test_m5_report_counts(self):
        """M5: report returns available, reserved, sold per SKU."""
        self._load()
        self.sys.reserve("alice", "A", 2)
        rid = self.sys.reserve("alice", "B", 1)["reservation_id"]
        self.sys.confirm(rid)

        items = {i["sku"]: i for i in self.sys.report()["items"]}
        self.assertEqual(3, len(items))
        self.assertEqual({"available": 8,  "reserved": 2, "sold": 0},
                         {k: items["A"][k] for k in ("available", "reserved", "sold")})
        self.assertEqual({"available": 4,  "reserved": 0, "sold": 1},
                         {k: items["B"][k] for k in ("available", "reserved", "sold")})
        self.assertEqual({"available": 1,  "reserved": 0, "sold": 0},
                         {k: items["C"][k] for k in ("available", "reserved", "sold")})


# -------------------------------------------------------------- edge cases


class EdgeCaseTests(EngineTestCase):

    # ── inventory loading ───────────────────────────────────────────

    def test_e1_empty_inventory(self):
        """E1: loading an empty list returns zero products, no crash."""
        result = self._load([])
        self.assertEqual("ok", result["status"])
        self.assertEqual(0, result["products_loaded"])
        self.assertEqual([], self.sys.report()["items"])

    def test_e2_file_not_found(self):
        """E2: a missing file raises SystemError."""
        with self.assertRaises(SystemError) as ctx:
            self.sys.load("non_existent_file.json")
        self.assertEqual("INVENTORY_NOT_FOUND", ctx.exception.code)

    def test_e3_invalid_json(self):
        """E3: a file that is not valid JSON raises SystemError."""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("{{{ bad json")
        self.addCleanup(os.unlink, path)
        with self.assertRaises(SystemError) as ctx:
            self.sys.load(path)
        self.assertEqual("INVENTORY_INVALID_JSON", ctx.exception.code)

    def test_e4_missing_fields_skipped(self):
        """E4: malformed entries are skipped with a warning."""
        result = self._load([
            {"sku": "A", "stock": 1},
            {"sku": "B"},                 # missing stock
            "not_an_object",              # wrong type
            {"sku": "C", "stock": 2, "name": "Thing C"},
        ])
        self.assertEqual("ok", result["status"])
        self.assertEqual(2, result["products_loaded"])
        self.assertGreater(len(result["warnings"]), 0)
        skus = {i["sku"] for i in self.sys.report()["items"]}
        self.assertSetEqual({"A", "C"}, skus)

    # ── reserve rejections ──────────────────────────────────────────

    def test_e5_reserve_more_than_available(self):
        """E5: reserve fails when qty > available."""
        self._load()
        with self.assertRaises(BusinessError) as ctx:
            self.sys.reserve("alice", "A", 11)
        self.assertEqual("INSUFFICIENT_STOCK", ctx.exception.code)

    def test_e6_reserve_zero_or_negative(self):
        """E6: reserve rejects qty <= 0."""
        self._load()
        for bad in (0, -1):
            with self.assertRaises(BusinessError) as ctx:
                self.sys.reserve("alice", "A", bad)
            self.assertEqual("INVALID_INPUT", ctx.exception.code)

    # ── confirm/cancel rejections ───────────────────────────────────

    def test_e7_confirm_without_reservation(self):
        """E7: confirm without a prior reserve rejects."""
        self._load()
        with self.assertRaises(BusinessError) as ctx:
            self.sys.confirm("nonexistent")
        self.assertEqual("RESERVATION_NOT_FOUND", ctx.exception.code)

    def test_e8_cancel_without_reservation(self):
        """E8: cancel without a prior reserve rejects."""
        self._load()
        with self.assertRaises(BusinessError) as ctx:
            self.sys.cancel("nonexistent")
        self.assertEqual("RESERVATION_NOT_FOUND", ctx.exception.code)

    def test_e9a_double_confirm(self):
        """E9: confirming twice rejects the second attempt."""
        self._load()
        rid = self.sys.reserve("alice", "A", 1)["reservation_id"]
        self.sys.confirm(rid)
        with self.assertRaises(BusinessError) as ctx:
            self.sys.confirm(rid)
        self.assertEqual("ALREADY_FINALIZED", ctx.exception.code)

    def test_e9b_double_cancel(self):
        """E9: cancelling twice rejects the second attempt."""
        self._load()
        rid = self.sys.reserve("alice", "A", 1)["reservation_id"]
        self.sys.cancel(rid)
        with self.assertRaises(BusinessError) as ctx:
            self.sys.cancel(rid)
        self.assertEqual("ALREADY_FINALIZED", ctx.exception.code)

    def test_e10_ttl_expire_before_confirm(self):
        """E10: confirming after TTL expiry rejects with EXPIRED."""
        self._load()
        rid = self.sys.reserve("alice", "A", 1, ttl=10)["reservation_id"]
        self.clock.advance(11)
        with self.assertRaises(BusinessError) as ctx:
            self.sys.confirm(rid)
        self.assertEqual("EXPIRED", ctx.exception.code)
        # stock should be back
        report = self.sys.report("A")["items"][0]
        self.assertEqual(10, report["available"])

    def test_e11_per_user_limit_exceeded(self):
        """E11: reserve rejects when user would pass limit."""
        self._load()
        self.sys.reserve("alice", "A", 3)  # at limit
        with self.assertRaises(BusinessError) as ctx:
            self.sys.reserve("alice", "A", 1)
        self.assertEqual("LIMIT_EXCEEDED", ctx.exception.code)

    def test_e12_concurrent_reservations_same_sku(self):
        """E12: multiple users reserving same SKU tracks available correctly."""
        self._load()
        self.sys.reserve("alice", "A", 3)
        self.sys.reserve("bob", "A", 4)
        report = self.sys.report("A")["items"][0]
        # stock=10, 7 reserved → 3 available
        self.assertEqual(3, report["available"])
        self.assertEqual(7, report["reserved"])

    def test_e13_all_or_nothing_confirm(self):
        """E13: confirm deducts the entire reservation quantity at once."""
        self._load()
        rid = self.sys.reserve("alice", "A", 3)["reservation_id"]
        result = self.sys.confirm(rid)
        self.assertEqual(3, result["qty"])  # full amount

    def test_e14_report_nonexistent_sku(self):
        """E14: report on a SKU not in inventory rejects."""
        self._load()
        with self.assertRaises(BusinessError) as ctx:
            self.sys.report("ZZZ")
        self.assertEqual("SKU_NOT_FOUND", ctx.exception.code)

    def test_e15_report_before_load(self):
        """E15: report before any load returns empty list, no crash."""
        self.assertEqual([], self.sys.report()["items"])

    def test_e18_ttl_zero_immediate_expiry(self):
        """E18: ttl=0 creates a reservation that expires immediately."""
        self._load()
        self.sys.reserve("alice", "A", 1, ttl=0)
        report = self.sys.report("A")["items"][0]
        self.assertEqual(10, report["available"])
        self.assertEqual(0, report["reserved"])

    def test_e21_negative_stock_rejected(self):
        """E21: negative stock in inventory is rejected at parse time."""
        result = self._load([{"sku": "A", "stock": -5}])
        self.assertEqual(0, result["products_loaded"])
        self.assertGreater(len(result["warnings"]), 0)

    def test_e22_duplicate_sku_rejected(self):
        """E22: duplicate SKU aborts the entire load."""
        with self.assertRaises(SystemError) as ctx:
            self._load([
                {"sku": "A", "stock": 1},
                {"sku": "A", "stock": 2},
            ])
        self.assertEqual("INVENTORY_DUPLICATE_SKU", ctx.exception.code)

    def test_e23_reserve_unknown_sku(self):
        """E23: reserving a SKU not in inventory rejects."""
        self._load()
        with self.assertRaises(BusinessError) as ctx:
            self.sys.reserve("alice", "ZZZ", 1)
        self.assertEqual("SKU_NOT_FOUND", ctx.exception.code)

    # ── input validation ────────────────────────────────────────────

    def test_e17_missing_reserve_params(self):
        """E17: reserve with missing params fails at validation."""
        self._load()
        for bad_qty in (None, "many", 3.14, True):
            with self.assertRaises(BusinessError):
                self.sys.reserve("u", "A", bad_qty)

    def test_non_string_user_rejected(self):
        self._load()
        with self.assertRaises(BusinessError):
            self.sys.reserve(123, "A", 1)

    def test_non_string_sku_rejected(self):
        self._load()
        with self.assertRaises(BusinessError):
            self.sys.reserve("u", 456, 1)

    # ── user+sku fallback ───────────────────────────────────────────

    def test_confirm_by_user_sku_works(self):
        """Confirm with user+sku targets the single active reservation."""
        self._load()
        self.sys.reserve("alice", "A", 1)
        result = self.sys.confirm(user="alice", sku="A")
        self.assertEqual("ok", result["status"])

    def test_cancel_by_user_sku_ambiguous(self):
        """Cancel with user+sku fails when there are multiple matches."""
        self._load()
        self.sys.reserve("alice", "A", 1)
        self.sys.reserve("alice", "A", 1)
        with self.assertRaises(BusinessError) as ctx:
            self.sys.cancel(user="alice", sku="A")
        self.assertEqual("AMBIGUOUS_RESERVATION", ctx.exception.code)

    # ── sanitization ────────────────────────────────────────────────

    def test_e19_user_with_control_chars(self):
        """E19: user ID with control characters is sanitized."""
        self._load()
        result = self.sys.reserve("ali\nce\r", "A", 1)
        self.assertNotIn("\n", result["user"])
        self.assertNotIn("\r", result["user"])

    # ── performance smoke ───────────────────────────────────────────

    def test_e20_large_inventory_works(self):
        """E20: many SKUs load and operate without O(n) degradation."""
        products = []
        for i in range(2000):
            products.append({
                "sku": f"SKU-{i:06d}",
                "stock": 100,
                "limit_per_user": 5,
            })
        self._load(products)
        # report all
        report = self.sys.report()
        self.assertEqual(2000, len(report["items"]))
        # reserve on one SKU — O(1) at dict level
        self.sys.reserve("u", "SKU-001000", 1)
        single = self.sys.report("SKU-001000")["items"][0]
        self.assertEqual(99, single["available"])
        self.assertEqual(1, single["reserved"])