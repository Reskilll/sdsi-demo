"""Tests for the FIFO Waitlist and auto-promotion mechanism (Stretch Feature)."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flash_sale import FlashSaleEngine, InsufficientStockError


class TestWaitlist(unittest.TestCase):

    def setUp(self):
        self.engine = FlashSaleEngine(
            inventory_source=[{"sku": "LIMITED-WATCH", "stock": 2, "per_user_limit": 2}],
            default_ttl=10,
            auto_promote_waitlist=True,
            auto_start_sweeper=False,
        )

    def tearDown(self):
        self.engine.shutdown()

    def test_waitlist_queue_ordering(self):
        """Users joining the waitlist receive correct 1-based queue positions."""
        # Exhaust stock of 2
        self.engine.reserve("user_buyer1", "LIMITED-WATCH", 2)

        # Users join waitlist
        pos1 = self.engine.join_waitlist("waiter_1", "LIMITED-WATCH", 1)
        pos2 = self.engine.join_waitlist("waiter_2", "LIMITED-WATCH", 1)
        pos3 = self.engine.join_waitlist("waiter_3", "LIMITED-WATCH", 2)

        self.assertEqual(pos1, 1)
        self.assertEqual(pos2, 2)
        self.assertEqual(pos3, 3)

        # Joining again returns existing position
        pos1_again = self.engine.join_waitlist("waiter_1", "LIMITED-WATCH", 1)
        self.assertEqual(pos1_again, 1)

    def test_waitlist_auto_promotion_on_cancellation(self):
        """When an active reservation is cancelled, waitlisted user is automatically promoted."""
        # Reserve stock
        res = self.engine.reserve("user_buyer1", "LIMITED-WATCH", 2)
        self.assertEqual(self.engine.get_stock_report("LIMITED-WATCH").available, 0)

        # Waitlist user
        self.engine.join_waitlist("waiter_alice", "LIMITED-WATCH", 1)

        # Cancel reservation -> 2 stock released -> 1 auto-reserved for waiter_alice
        self.engine.cancel(res.reservation_id)

        report = self.engine.get_stock_report("LIMITED-WATCH")
        self.assertEqual(report.available, 1)  # 2 - 1 = 1 left
        self.assertEqual(report.reserved, 1)   # 1 auto-reserved for waiter_alice

        events = self.engine.audit.get_events(event_type="WAITLIST_PROMOTED", sku="LIMITED-WATCH")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].user_id, "waiter_alice")


if __name__ == "__main__":
    unittest.main()

