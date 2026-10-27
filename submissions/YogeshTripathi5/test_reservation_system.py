"""Automated tests for InventoryReservationSystem — includes edge cases,
TTL expiry, purchase limits, concurrency, and boundary conditions."""

import json
import os
import tempfile
import threading
import time
import unittest

from reservation_system import InventoryReservationSystem


# Helper: create a fresh system with known data for each test
BASE_DATA = {
    "PS4-CONSOLE": {"name": "PlayStation 4 Console", "total": 10, "reserved": 0, "sold": 0},
    "PS4-CONTROLLER": {"name": "DualShock 4 Controller", "total": 3, "reserved": 0, "sold": 0},
}


def fresh_system(**kw):
    """Create a system with baseline products, default TTL overridable."""
    kw.setdefault("default_ttl", 120)
    return InventoryReservationSystem(
        data=dict(BASE_DATA),
        **kw,
    )


class TestReservationSystem(unittest.TestCase):

    # --------------------------------------------------------------- load / init

    def test_load_from_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"sku": "TEST-1", "name": "Test Item", "stock": 5}], f)
            p = f.name
        try:
            s = InventoryReservationSystem(p)
            self.assertEqual(s.product("TEST-1")["available"], 5)
        finally:
            os.unlink(p)

    def test_invalid_inventory_malformed_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            p = f.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                InventoryReservationSystem(p)
        finally:
            os.unlink(p)

    def test_inventory_not_a_list_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"sku": "X", "stock": 1}, f)
            p = f.name
        try:
            with self.assertRaises(ValueError):
                InventoryReservationSystem(p)
        finally:
            os.unlink(p)

    def test_inventory_missing_sku_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"name": "no sku", "stock": 1}], f)
            p = f.name
        try:
            with self.assertRaises(ValueError):
                InventoryReservationSystem(p)
        finally:
            os.unlink(p)

    # ----------------------------------------------------------- products listing

    def test_products_returns_all(self):
        s = fresh_system()
        prods = s.products()
        self.assertIn("PS4-CONSOLE", prods)
        self.assertIn("PS4-CONTROLLER", prods)
        self.assertEqual(prods["PS4-CONSOLE"]["available"], 10)

    def test_product_returns_none_for_unknown(self):
        s = fresh_system()
        self.assertIsNone(s.product("NONEXISTENT"))

    # ------------------------------------------------------------- reserve basics

    def test_reserve_success(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", 2)
        self.assertTrue(r["success"])
        self.assertIn("reservation_id", r)
        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["reserved"], 2)
        self.assertEqual(p["available"], 8)

    def test_reserve_unknown_sku(self):
        s = fresh_system()
        r = s.reserve("FAKE", "alice", 1)
        self.assertFalse(r["success"])
        self.assertIn("unknown SKU", r["error"])

    def test_reserve_invalid_quantity_zero(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", 0)
        self.assertFalse(r["success"])

    def test_reserve_invalid_quantity_negative(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", -1)
        self.assertFalse(r["success"])

    def test_reserve_invalid_quantity_non_int(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", "five")  # type: ignore
        self.assertFalse(r["success"])

    def test_reserve_no_sku_or_user(self):
        s = fresh_system()
        r = s.reserve("", "alice", 1)
        self.assertFalse(r["success"])
        r2 = s.reserve("PS4-CONSOLE", "", 1)
        self.assertFalse(r2["success"])

    # ------------------------------------------------------------- overselling

    def test_reserve_insufficient_stock(self):
        s = fresh_system()
        r = s.reserve("PS4-CONTROLLER", "alice", 10)
        self.assertFalse(r["success"])
        self.assertIn("insufficient stock", r["error"])

    def test_reserve_exact_available_works(self):
        s = fresh_system()
        r = s.reserve("PS4-CONTROLLER", "alice", 3)
        self.assertTrue(r["success"])
        self.assertEqual(s.product("PS4-CONTROLLER")["available"], 0)

    # ------------------------------------------------------------ confirm / cancel

    def test_confirm_success(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", 2)
        rid = r["reservation_id"]
        res = s.confirm(rid)
        self.assertTrue(res["success"])
        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["sold"], 2)
        self.assertEqual(p["reserved"], 0)
        self.assertEqual(p["available"], 8)

    def test_confirm_idempotent(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        self.assertTrue(s.confirm(rid)["success"])
        r2 = s.confirm(rid)
        self.assertFalse(r2["success"])
        self.assertIn("already confirmed", r2["error"])

    def test_cancel_success(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 3)["reservation_id"]
        res = s.cancel(rid)
        self.assertTrue(res["success"])
        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["reserved"], 0)
        self.assertEqual(p["available"], 10)

    def test_cancel_idempotent(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        self.assertTrue(s.cancel(rid)["success"])
        r2 = s.cancel(rid)
        self.assertFalse(r2["success"])
        self.assertIn("already cancelled", r2["error"])

    def test_cancel_confirmed_fails(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        s.confirm(rid)
        r = s.cancel(rid)
        self.assertFalse(r["success"])

    def test_confirm_nonexistent(self):
        s = fresh_system()
        r = s.confirm("no-such-id")
        self.assertFalse(r["success"])
        self.assertIn("not found", r["error"])

    def test_cancel_nonexistent(self):
        s = fresh_system()
        r = s.cancel("no-such-id")
        self.assertFalse(r["success"])

    def test_duplicate_reservation_ids_are_unique(self):
        s = fresh_system()
        r1 = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        r2 = s.reserve("PS4-CONSOLE", "bob", 1)["reservation_id"]
        self.assertNotEqual(r1, r2)

    # --------------------------------------------------------------------- TTL

    def test_expired_reservation_releases_stock(self):
        s = fresh_system(default_ttl=0.01)
        rid = s.reserve("PS4-CONSOLE", "alice", 2)["reservation_id"]
        # initial state
        self.assertEqual(s.product("PS4-CONSOLE")["reserved"], 2)
        time.sleep(0.02)
        # trigger lazy expiry
        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["reserved"], 0)
        self.assertEqual(p["available"], 10)
        self.assertEqual(s.reservation(rid)["status"], "expired")

    def test_confirm_on_expired_reservation_fails(self):
        s = fresh_system(default_ttl=0.01)
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        time.sleep(0.02)
        r = s.confirm(rid)
        self.assertFalse(r["success"])
        self.assertIn("expired", r["error"])

    def test_cancel_on_expired_reservation_fails(self):
        s = fresh_system(default_ttl=0.01)
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        time.sleep(0.02)
        r = s.cancel(rid)
        self.assertFalse(r["success"])
        self.assertIn("expired", r["error"])

    def test_custom_ttl_per_reservation(self):
        s = fresh_system(default_ttl=120)
        rid = s.reserve("PS4-CONSOLE", "alice", 1, ttl=0.01)["reservation_id"]
        time.sleep(0.02)
        self.assertEqual(s.reservation(rid)["status"], "expired")

    # ------------------------------------------------------------- purchase limits

    def test_purchase_limit_enforced(self):
        s = fresh_system()
        # limit of 3 per user per SKU
        r1 = s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=3)
        self.assertTrue(r1["success"])
        r2 = s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=3)
        self.assertFalse(r2["success"])
        self.assertIn("purchase limit", r2["error"])

    def test_purchase_limit_per_user_separate(self):
        s = fresh_system()
        r1 = s.reserve("PS4-CONSOLE", "alice", 3, purchase_limit=3)
        self.assertTrue(r1["success"])
        r2 = s.reserve("PS4-CONSOLE", "bob", 3, purchase_limit=3)
        self.assertTrue(r2["success"])

    def test_purchase_limit_includes_confirmed(self):
        s = fresh_system()
        r1 = s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=3)
        rid = r1["reservation_id"]
        s.confirm(rid)
        # alice now has 2 confirmed, can only reserve 1 more
        r2 = s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=3)
        self.assertFalse(r2["success"])
        r3 = s.reserve("PS4-CONSOLE", "alice", 1, purchase_limit=3)
        self.assertTrue(r3["success"])

    def test_purchase_limit_respects_reserved_and_confirmed(self):
        s = fresh_system()
        s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=5)
        s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=5)
        r = s.reserve("PS4-CONSOLE", "alice", 2, purchase_limit=5)
        self.assertFalse(r["success"])

    # ---------------------------------------------------------------- accounting

    def test_accounting_consistency(self):
        s = fresh_system()
        s.reserve("PS4-CONSOLE", "alice", 3)
        s.reserve("PS4-CONSOLE", "bob", 2)
        s.reserve("PS4-CONTROLLER", "alice", 1)
        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["total"], p["available"] + p["reserved"] + p["sold"])
        # confirm one
        rid = list(s._reservations.keys())[0]
        s.confirm(rid)
        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["total"], p["available"] + p["reserved"] + p["sold"])

    # --------------------------------------------------------- reservation lookup

    def test_reservation_lookup_returns_none_for_missing(self):
        s = fresh_system()
        self.assertIsNone(s.reservation("missing"))

    def test_reservation_returns_state(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        r = s.reservation(rid)
        self.assertEqual(r["id"], rid)
        self.assertEqual(r["status"], "active")
        self.assertEqual(r["user_id"], "alice")
        self.assertEqual(r["sku"], "PS4-CONSOLE")

    # ------------------------------------------------------------- concurrency

    def test_concurrent_reserve_does_not_oversell(self):
        s = fresh_system()
        n_threads = 10
        results = []

        def worker():
            r = s.reserve("PS4-CONTROLLER", "racer", 1)
            results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for r in results if r.get("success")]
        self.assertEqual(len(successes), 3)  # only 3 stock
        self.assertEqual(s.product("PS4-CONTROLLER")["available"], 0)

    def test_concurrent_confirm_does_not_double_process(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 2)["reservation_id"]

        outcomes = []

        def worker():
            outcomes.append(s.confirm(rid))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        confirms = [o for o in outcomes if o["success"]]
        self.assertEqual(len(confirms), 1)  # only one should succeed
        self.assertEqual(s.product("PS4-CONSOLE")["sold"], 2)

    def test_concurrent_cancel_and_confirm_race(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]

        outcomes = []

        def do_cancel():
            outcomes.append(("cancel", s.cancel(rid)))

        def do_confirm():
            outcomes.append(("confirm", s.confirm(rid)))

        threads = [
            threading.Thread(target=do_cancel),
            threading.Thread(target=do_confirm),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [o for o in outcomes if o[1]["success"]]
        self.assertEqual(len(successes), 1)  # exactly one operation wins

    def test_concurrent_cleanup_does_not_corrupt(self):
        """Many reserve + cancel cycles with short TTL — stress expiry."""
        s = fresh_system(default_ttl=0.01, data={
            "PS4-CONSOLE": {"name": "Console", "total": 100, "reserved": 0, "sold": 0},
        })

        def cycle(n):
            for _ in range(n):
                r = s.reserve("PS4-CONSOLE", "stressor", 1)
                if r["success"]:
                    s.cancel(r["reservation_id"])
                time.sleep(0.005)

        threads = [threading.Thread(target=cycle, args=(10,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        p = s.product("PS4-CONSOLE")
        self.assertEqual(p["total"], p["available"] + p["reserved"] + p["sold"])
        self.assertEqual(p["reserved"], 0)

    # ------------------------------------------------------------ boundary / misc

    def test_large_reservation_block(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", 10)
        self.assertTrue(r["success"])
        self.assertEqual(s.product("PS4-CONSOLE")["available"], 0)

    def test_reserve_after_full_sell_works_if_released(self):
        s = fresh_system()
        rid = s.reserve("PS4-CONTROLLER", "alice", 2)["reservation_id"]
        s.cancel(rid)
        r2 = s.reserve("PS4-CONTROLLER", "alice", 2)
        self.assertTrue(r2["success"])

    def test_multiple_users_independent(self):
        s = fresh_system()
        r1 = s.reserve("PS4-CONSOLE", "alice", 5)
        r2 = s.reserve("PS4-CONSOLE", "bob", 5)
        self.assertTrue(r1["success"])
        self.assertTrue(r2["success"])
        self.assertEqual(s.product("PS4-CONSOLE")["available"], 0)

    def test_custom_ttl_still_expires(self):
        s = fresh_system(default_ttl=999)
        rid = s.reserve("PS4-CONSOLE", "alice", 1, ttl=0.01)["reservation_id"]
        time.sleep(0.02)
        self.assertEqual(s.reservation(rid)["status"], "expired")

    def test_purchase_limit_allows_exact_limit(self):
        s = fresh_system()
        r = s.reserve("PS4-CONSOLE", "alice", 3, purchase_limit=3)
        self.assertTrue(r["success"])

    def test_expired_reservation_still_in_lookup_with_status(self):
        s = fresh_system(default_ttl=0.01)
        rid = s.reserve("PS4-CONSOLE", "alice", 1)["reservation_id"]
        time.sleep(0.02)
        _ = s.product("PS4-CONSOLE")  # trigger cleanup
        r = s.reservation(rid)
        self.assertIsNotNone(r)
        self.assertEqual(r["status"], "expired")


if __name__ == "__main__":
    unittest.main(verbosity=2)