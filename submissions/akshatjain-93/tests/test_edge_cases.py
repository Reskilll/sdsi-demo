"""Edge case validation, error handling, and robustness tests."""

from pathlib import Path
import sys
import time
import unittest

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


class TestEdgeCasesAndRobustness(unittest.TestCase):

    def setUp(self):
        self.engine = FlashSaleEngine(
            inventory_source=[
                {"sku": "ITEM-EDGE", "stock": 5, "per_user_limit": 2},
            ],
            default_ttl=10,
            auto_start_sweeper=False,
        )

    def tearDown(self):
        self.engine.shutdown()

    # -------------------------------------------------------------------------
    # Input Validation & Sanitization
    # -------------------------------------------------------------------------

    def test_invalid_quantities(self):
        """Quantities <= 0 or non-integers are rejected with ValidationError."""
        invalid_quantities = [0, -1, -99, 1.5, "1", None, []]
        for q in invalid_quantities:
            with self.subTest(quantity=q):
                with self.assertRaises(ValidationError):
                    self.engine.reserve(user_id="user_1", sku="ITEM-EDGE", quantity=q)

    def test_invalid_user_ids(self):
        """Empty, whitespace-only, or non-string user_ids are rejected."""
        invalid_users = ["", "   ", "\t\n", None, 123, {}]
        for u in invalid_users:
            with self.subTest(user_id=u):
                with self.assertRaises(ValidationError):
                    self.engine.reserve(user_id=u, sku="ITEM-EDGE", quantity=1)

    def test_invalid_skus(self):
        """Empty or whitespace-only SKUs are rejected."""
        invalid_skus = ["", "   ", None, 999]
        for s in invalid_skus:
            with self.subTest(sku=s):
                with self.assertRaises(ValidationError):
                    self.engine.reserve(user_id="user_1", sku=s, quantity=1)

    def test_invalid_ttl(self):
        """TTL <= 0 or non-integer is rejected."""
        for ttl in [0, -10, 1.5, "60"]:
            with self.subTest(ttl=ttl):
                with self.assertRaises(ValidationError):
                    self.engine.reserve(user_id="user_1", sku="ITEM-EDGE", quantity=1, ttl_seconds=ttl)

    # -------------------------------------------------------------------------
    # Security & Access Control: User Mismatch
    # -------------------------------------------------------------------------

    def test_confirm_wrong_user_rejected(self):
        """A user cannot confirm another user's reservation."""
        res = self.engine.reserve(user_id="victim_user", sku="ITEM-EDGE", quantity=1)
        with self.assertRaises(ReservationNotFoundError):
            self.engine.confirm(res.reservation_id, user_id="attacker_user")

    def test_cancel_wrong_user_rejected(self):
        """A user cannot cancel another user's reservation."""
        res = self.engine.reserve(user_id="victim_user", sku="ITEM-EDGE", quantity=1)
        with self.assertRaises(ReservationNotFoundError):
            self.engine.cancel(res.reservation_id, user_id="attacker_user")

    def test_nonexistent_reservation_operations(self):
        """Confirming or cancelling a bogus reservation ID fails."""
        with self.assertRaises(ReservationNotFoundError):
            self.engine.confirm("bogus-res-id")
        with self.assertRaises(ReservationNotFoundError):
            self.engine.cancel("bogus-res-id")

    # -------------------------------------------------------------------------
    # State Transition Integrity
    # -------------------------------------------------------------------------

    def test_double_cancel_rejected(self):
        """Cancelling a cancelled reservation raises InvalidStateError."""
        res = self.engine.reserve(user_id="user_1", sku="ITEM-EDGE", quantity=1)
        self.engine.cancel(res.reservation_id)
        with self.assertRaises(InvalidStateError):
            self.engine.cancel(res.reservation_id)

    def test_confirm_after_cancel_rejected(self):
        """Confirming a cancelled reservation raises InvalidStateError."""
        res = self.engine.reserve(user_id="user_1", sku="ITEM-EDGE", quantity=1)
        self.engine.cancel(res.reservation_id)
        with self.assertRaises(InvalidStateError):
            self.engine.confirm(res.reservation_id)

    def test_cancel_after_expiry_rejected(self):
        """Cancelling an expired reservation raises InvalidStateError."""
        sim_time = 500.0
        engine = FlashSaleEngine(
            inventory_source=[{"sku": "ITEM-EXP", "stock": 5, "per_user_limit": 2}],
            time_func=lambda: sim_time,
            auto_start_sweeper=False,
        )
        res = engine.reserve(user_id="user_1", sku="ITEM-EXP", quantity=1, ttl_seconds=5)
        sim_time += 10.0  # Expire
        engine.release_expired()

        with self.assertRaises(InvalidStateError):
            engine.cancel(res.reservation_id)

    # -------------------------------------------------------------------------
    # Exhaustion to Zero & Reclaim
    # -------------------------------------------------------------------------

    def test_full_depletion_and_reclaim(self):
        """Stock can be depleted down to 0, subsequent attempts fail, then succeeds upon release."""
        # 5 stock, limit 2
        r1 = self.engine.reserve("u1", "ITEM-EDGE", 2)
        r2 = self.engine.reserve("u2", "ITEM-EDGE", 2)
        r3 = self.engine.reserve("u3", "ITEM-EDGE", 1)  # Stock now 0

        self.assertEqual(self.engine.get_stock_report("ITEM-EDGE").available, 0)

        # u4 tries to reserve -> fails
        with self.assertRaises(InsufficientStockError):
            self.engine.reserve("u4", "ITEM-EDGE", 1)

        # Cancel r1 -> releases 2 units
        self.engine.cancel(r1.reservation_id)
        self.assertEqual(self.engine.get_stock_report("ITEM-EDGE").available, 2)

        # u4 can now reserve
        r4 = self.engine.reserve("u4", "ITEM-EDGE", 2)
        self.assertIsNotNone(r4)

    # -------------------------------------------------------------------------
    # Sweeper & Audit Robustness
    # -------------------------------------------------------------------------

    def test_sweeper_start_stop_idempotent(self):
        """Starting or stopping the sweeper multiple times causes no issues."""
        sweeper_engine = FlashSaleEngine(
            inventory_source=[{"sku": "ITEM-SWEEP", "stock": 5, "per_user_limit": 2}],
            auto_start_sweeper=True,
        )
        self.assertTrue(sweeper_engine.sweeper.is_running())
        sweeper_engine.sweeper.start()  # Idempotent start
        sweeper_engine.shutdown()
        self.assertFalse(sweeper_engine.sweeper.is_running())
        sweeper_engine.shutdown()  # Idempotent stop

    def test_audit_ledger_tracking(self):
        """Audit ledger records every action accurately."""
        res = self.engine.reserve("u_audit", "ITEM-EDGE", 1)
        self.engine.confirm(res.reservation_id)

        events = self.engine.audit.get_events(sku="ITEM-EDGE")
        event_types = [e.event_type for e in events]
        self.assertIn("INVENTORY_LOADED", event_types)
        self.assertIn("RESERVATION_CREATED", event_types)
        self.assertIn("RESERVATION_CONFIRMED", event_types)


if __name__ == "__main__":
    unittest.main()

