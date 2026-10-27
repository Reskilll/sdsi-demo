"""Comprehensive unit tests covering requirements M1 through M5."""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Ensure package root is in path regardless of current working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flash_sale import (
    FlashSaleEngine,
    ProductNotFoundError,
    InsufficientStockError,
    PurchaseLimitExceededError,
    ReservationNotFoundError,
    ReservationExpiredError,
    InvalidStateError,
    ValidationError,
    ReservationStatus,
)


class TestFlashSaleEngine(unittest.TestCase):

    def setUp(self):
        self.sample_data = [
            {"sku": "SKU-IPHONE", "name": "iPhone 15", "stock": 10, "price": 999.0, "per_user_limit": 2},
            {"sku": "SKU-PS5", "name": "PS5 Console", "stock": 5, "price": 499.0, "per_user_limit": 1},
            {"sku": "SKU-HEADPHONES", "name": "Wireless Headphones", "stock": 20, "price": 150.0, "per_user_limit": 3},
        ]
        self.engine = FlashSaleEngine(
            inventory_source=self.sample_data,
            default_ttl=120,
            auto_start_sweeper=False,
        )

    def tearDown(self):
        self.engine.shutdown()

    # -------------------------------------------------------------------------
    # M1: Inventory Loading
    # -------------------------------------------------------------------------

    def test_m1_load_inventory_from_data(self):
        """M1: Products and stock load properly from list of dictionaries."""
        reports = self.engine.get_all_reports()
        self.assertEqual(len(reports), 3)
        self.assertIn("SKU-IPHONE", reports)
        self.assertEqual(reports["SKU-IPHONE"].available, 10)
        self.assertEqual(reports["SKU-IPHONE"].reserved, 0)
        self.assertEqual(reports["SKU-IPHONE"].sold, 0)

    def test_m1_load_inventory_from_file(self):
        """M1: Products and stock load from a valid JSON file."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            json.dump([{"sku": "SKU-TEST", "name": "Test Item", "stock": 50, "per_user_limit": 5}], tmp)
            tmp_path = tmp.name

        try:
            file_engine = FlashSaleEngine(inventory_source=tmp_path, auto_start_sweeper=False)
            report = file_engine.get_stock_report("SKU-TEST")
            self.assertEqual(report.available, 50)
            self.assertEqual(report.initial_stock, 50)
            file_engine.shutdown()
        finally:
            os.remove(tmp_path)

    def test_m1_load_file_not_found(self):
        """M1: Loading a non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            FlashSaleEngine(inventory_source="non_existent_file_12345.json", auto_start_sweeper=False)

    def test_m1_load_invalid_json(self):
        """M1: Loading malformed JSON raises ValidationError."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            tmp.write("{malformed json [")
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValidationError):
                FlashSaleEngine(inventory_source=tmp_path, auto_start_sweeper=False)
        finally:
            os.remove(tmp_path)

    def test_m1_load_invalid_stock(self):
        """M1: Negative stock in inventory raises ValidationError."""
        invalid_items = [{"sku": "BAD-STOCK", "stock": -5, "per_user_limit": 2}]
        with self.assertRaises(ValidationError):
            FlashSaleEngine(inventory_source=invalid_items, auto_start_sweeper=False)

    # -------------------------------------------------------------------------
    # M2: Stock Reservation & TTL
    # -------------------------------------------------------------------------

    def test_m2_reserve_stock_success(self):
        """M2: Reserving stock holds it for default TTL (120s) and decrements available."""
        res = self.engine.reserve(user_id="user_alice", sku="SKU-IPHONE", quantity=2)
        self.assertIsNotNone(res.reservation_id)
        self.assertEqual(res.user_id, "user_alice")
        self.assertEqual(res.sku, "SKU-IPHONE")
        self.assertEqual(res.quantity, 2)
        self.assertEqual(res.status, ReservationStatus.PENDING)
        self.assertAlmostEqual(res.expires_at - res.created_at, 120.0, delta=1.0)

        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual(report.available, 8)
        self.assertEqual(report.reserved, 2)
        self.assertEqual(report.sold, 0)

    def test_m2_reserve_custom_ttl(self):
        """M2: Custom TTL is respected."""
        res = self.engine.reserve(user_id="user_bob", sku="SKU-PS5", quantity=1, ttl_seconds=60)
        self.assertAlmostEqual(res.expires_at - res.created_at, 60.0, delta=1.0)

    def test_m2_reserve_insufficient_stock(self):
        """M2: Reserving more than available stock raises InsufficientStockError."""
        # Cleanly reserve 19 units using distinct users within their limit (3)
        self.engine.reserve(user_id="u_a", sku="SKU-HEADPHONES", quantity=3)
        self.engine.reserve(user_id="u_b", sku="SKU-HEADPHONES", quantity=3)
        self.engine.reserve(user_id="u_c", sku="SKU-HEADPHONES", quantity=3)
        self.engine.reserve(user_id="u_d", sku="SKU-HEADPHONES", quantity=3)
        self.engine.reserve(user_id="u_e", sku="SKU-HEADPHONES", quantity=3)
        self.engine.reserve(user_id="u_f", sku="SKU-HEADPHONES", quantity=3)
        self.engine.reserve(user_id="u_g", sku="SKU-HEADPHONES", quantity=1)  # 19 reserved, 1 left

        # user_charlie has limit 3, requests 2, but only 1 available!
        with self.assertRaises(InsufficientStockError) as ctx:
            self.engine.reserve(user_id="user_charlie", sku="SKU-HEADPHONES", quantity=2)
        self.assertEqual(ctx.exception.sku, "SKU-HEADPHONES")
        self.assertEqual(ctx.exception.requested, 2)
        self.assertEqual(ctx.exception.available, 1)

    def test_m2_reserve_unknown_sku(self):
        """M2: Reserving non-existent SKU raises ProductNotFoundError."""
        with self.assertRaises(ProductNotFoundError):
            self.engine.reserve(user_id="user_charlie", sku="NON-EXISTENT", quantity=1)

    # -------------------------------------------------------------------------
    # M3: Confirm, Cancel, and TTL Expiry
    # -------------------------------------------------------------------------

    def test_m3_confirm_permanently_deducts_stock(self):
        """M3: Confirm moves stock from reserved to sold."""
        res = self.engine.reserve(user_id="user_dave", sku="SKU-IPHONE", quantity=1)
        confirmed = self.engine.confirm(res.reservation_id, user_id="user_dave")
        self.assertEqual(confirmed.status, ReservationStatus.CONFIRMED)
        self.assertIsNotNone(confirmed.confirmed_at)

        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual(report.available, 9)
        self.assertEqual(report.reserved, 0)
        self.assertEqual(report.sold, 1)

    def test_m3_cancel_releases_stock(self):
        """M3: Cancel releases reserved stock back to available."""
        res = self.engine.reserve(user_id="user_eve", sku="SKU-IPHONE", quantity=2)
        report_before = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual(report_before.available, 8)
        self.assertEqual(report_before.reserved, 2)

        cancelled = self.engine.cancel(res.reservation_id, user_id="user_eve")
        self.assertEqual(cancelled.status, ReservationStatus.CANCELLED)

        report_after = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual(report_after.available, 10)
        self.assertEqual(report_after.reserved, 0)
        self.assertEqual(report_after.sold, 0)

    def test_m3_ttl_expiry_releases_stock(self):
        """M3: TTL expiration releases stock back to available pool."""
        simulated_time = 1000.0

        def mock_time():
            return simulated_time

        timed_engine = FlashSaleEngine(
            inventory_source=[{"sku": "SKU-CLOCK", "stock": 5, "per_user_limit": 2}],
            time_func=mock_time,
            auto_start_sweeper=False,
        )

        res = timed_engine.reserve(user_id="user_frank", sku="SKU-CLOCK", quantity=2, ttl_seconds=10)
        self.assertEqual(timed_engine.get_stock_report("SKU-CLOCK").available, 3)
        self.assertEqual(timed_engine.get_stock_report("SKU-CLOCK").reserved, 2)

        # Advance time past TTL
        simulated_time += 15.0

        # Trigger sweeper sweep or passive report check
        timed_engine.release_expired()
        report = timed_engine.get_stock_report("SKU-CLOCK")
        self.assertEqual(report.available, 5)
        self.assertEqual(report.reserved, 0)
        self.assertEqual(report.sold, 0)

        # Confirming expired reservation must fail
        with self.assertRaises(ReservationExpiredError):
            timed_engine.confirm(res.reservation_id)

    def test_m3_double_confirm_prevented(self):
        """M3: Confirming an already confirmed reservation raises InvalidStateError."""
        res = self.engine.reserve(user_id="user_grace", sku="SKU-PS5", quantity=1)
        self.engine.confirm(res.reservation_id)
        with self.assertRaises(InvalidStateError):
            self.engine.confirm(res.reservation_id)

    def test_m3_cancel_after_confirm_prevented(self):
        """M3: Cancelling an already confirmed reservation raises InvalidStateError."""
        res = self.engine.reserve(user_id="user_heidi", sku="SKU-PS5", quantity=1)
        self.engine.confirm(res.reservation_id)
        with self.assertRaises(InvalidStateError):
            self.engine.cancel(res.reservation_id)

    # -------------------------------------------------------------------------
    # M4: Per-User Purchase Limit per SKU
    # -------------------------------------------------------------------------

    def test_m4_enforce_limit_single_reservation(self):
        """M4: User cannot reserve more than per_user_limit in one request."""
        # SKU-IPHONE has per_user_limit: 2
        with self.assertRaises(PurchaseLimitExceededError) as ctx:
            self.engine.reserve(user_id="user_ivan", sku="SKU-IPHONE", quantity=3)
        self.assertEqual(ctx.exception.limit, 2)
        self.assertEqual(ctx.exception.requested, 3)

    def test_m4_enforce_limit_accumulated_reservations(self):
        """M4: User cannot exceed quota across multiple reservations."""
        self.engine.reserve(user_id="user_judy", sku="SKU-IPHONE", quantity=1)
        self.engine.reserve(user_id="user_judy", sku="SKU-IPHONE", quantity=1)  # Total 2 (limit reached)
        
        with self.assertRaises(PurchaseLimitExceededError):
            self.engine.reserve(user_id="user_judy", sku="SKU-IPHONE", quantity=1)

    def test_m4_enforce_limit_across_purchased_and_reserved(self):
        """M4: Confirmed purchases also count toward the user's limit."""
        res = self.engine.reserve(user_id="user_mallory", sku="SKU-IPHONE", quantity=1)
        self.engine.confirm(res.reservation_id)

        # User has 1 confirmed purchase, limit is 2. Can reserve 1 more.
        res2 = self.engine.reserve(user_id="user_mallory", sku="SKU-IPHONE", quantity=1)
        self.assertIsNotNone(res2)

        # Attempting to reserve another exceeds quota
        with self.assertRaises(PurchaseLimitExceededError):
            self.engine.reserve(user_id="user_mallory", sku="SKU-IPHONE", quantity=1)

    def test_m4_quota_restored_on_cancel_or_expiry(self):
        """M4: Cancelling or expiring a reservation restores available user quota."""
        res = self.engine.reserve(user_id="user_oscar", sku="SKU-PS5", quantity=1)  # Limit is 1
        with self.assertRaises(PurchaseLimitExceededError):
            self.engine.reserve(user_id="user_oscar", sku="SKU-PS5", quantity=1)

        # Cancel reservation
        self.engine.cancel(res.reservation_id)

        # User can now reserve again
        res_new = self.engine.reserve(user_id="user_oscar", sku="SKU-PS5", quantity=1)
        self.assertIsNotNone(res_new)

    # -------------------------------------------------------------------------
    # M5: Reporting & Invariants
    # -------------------------------------------------------------------------

    def test_m5_report_counts_and_invariant(self):
        """M5: Accurately reports available, reserved, and sold counts, satisfying invariant."""
        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual((report.available, report.reserved, report.sold), (10, 0, 0))

        # Reserve 2
        res1 = self.engine.reserve("u1", "SKU-IPHONE", 2)
        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual((report.available, report.reserved, report.sold), (8, 2, 0))

        # Reserve 1
        res2 = self.engine.reserve("u2", "SKU-IPHONE", 1)
        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual((report.available, report.reserved, report.sold), (7, 3, 0))

        # Confirm res1 (2 sold)
        self.engine.confirm(res1.reservation_id)
        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual((report.available, report.reserved, report.sold), (7, 1, 2))

        # Cancel res2 (1 back to available)
        self.engine.cancel(res2.reservation_id)
        report = self.engine.get_stock_report("SKU-IPHONE")
        self.assertEqual((report.available, report.reserved, report.sold), (8, 0, 2))

        # Strict mathematical invariant check
        self.assertEqual(report.initial_stock, report.available + report.reserved + report.sold)

    def test_m5_system_summary(self):
        """M5: System summary provides correct global aggregates."""
        summary = self.engine.get_system_summary()
        self.assertEqual(summary["total_products"], 3)
        self.assertEqual(summary["total_initial_stock"], 35)
        self.assertTrue(summary["inventory_invariant_satisfied"])


if __name__ == "__main__":
    unittest.main()
