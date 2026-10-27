"""High-concurrency stress tests verifying zero overselling and thread-safety."""

import concurrent.futures
from pathlib import Path
import random
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flash_sale import (
    FlashSaleEngine,
    InsufficientStockError,
    PurchaseLimitExceededError,
    ReservationExpiredError,
    InvalidStateError,
)


class TestConcurrency(unittest.TestCase):

    def test_prevent_overselling_under_extreme_race(self):
        """
        100 concurrent threads compete for 10 units of high-demand stock.
        Guarantees EXACTLY 10 reservations succeed, 90 fail, and ZERO overselling.
        """
        stock_units = 10
        thread_count = 100

        engine = FlashSaleEngine(
            inventory_source=[{"sku": "LIMITED-PHONE", "stock": stock_units, "per_user_limit": 1}],
            default_ttl=60,
            auto_start_sweeper=False,
        )

        successful_reservations = []
        out_of_stock_errors = []
        other_errors = []

        def buyer_attempt(user_id: str):
            try:
                res = engine.reserve(user_id=user_id, sku="LIMITED-PHONE", quantity=1)
                return ("SUCCESS", res)
            except InsufficientStockError as e:
                return ("OUT_OF_STOCK", e)
            except Exception as e:
                return ("OTHER_ERROR", e)

        # Launch all 100 threads simultaneously using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            user_ids = [f"buyer_{i:03d}" for i in range(thread_count)]
            futures = [executor.submit(buyer_attempt, uid) for uid in user_ids]
            for f in concurrent.futures.as_completed(futures):
                outcome, payload = f.result()
                if outcome == "SUCCESS":
                    successful_reservations.append(payload)
                elif outcome == "OUT_OF_STOCK":
                    out_of_stock_errors.append(payload)
                else:
                    other_errors.append(payload)

        # Assertions
        self.assertEqual(len(other_errors), 0, f"Unexpected errors: {other_errors}")
        self.assertEqual(len(successful_reservations), stock_units, "Should allocate exactly stock count")
        self.assertEqual(len(out_of_stock_errors), thread_count - stock_units)

        # Invariant check
        report = engine.get_stock_report("LIMITED-PHONE")
        self.assertEqual(report.available, 0)
        self.assertEqual(report.reserved, stock_units)
        self.assertEqual(report.sold, 0)
        self.assertEqual(report.initial_stock, report.available + report.reserved + report.sold)

        engine.shutdown()

    def test_concurrent_mixed_operations_and_invariant_preservation(self):
        """
        Tests simultaneous reserve, confirm, and cancel operations across 50 threads.
        Asserts that the invariant (initial == available + reserved + sold) is never violated.
        """
        stock_units = 25
        engine = FlashSaleEngine(
            inventory_source=[{"sku": "GADGET-X", "stock": stock_units, "per_user_limit": 5}],
            default_ttl=60,
            auto_start_sweeper=False,
        )

        def worker_lifecycle(user_id: str):
            # Attempt to reserve 1-2 items
            qty = random.randint(1, 2)
            try:
                res = engine.reserve(user_id=user_id, sku="GADGET-X", quantity=qty)
            except (InsufficientStockError, PurchaseLimitExceededError):
                return

            # Randomly decide to confirm or cancel
            time.sleep(random.uniform(0.001, 0.01))
            try:
                if random.choice([True, False]):
                    engine.confirm(res.reservation_id, user_id=user_id)
                else:
                    engine.cancel(res.reservation_id, user_id=user_id)
            except (InvalidStateError, ReservationExpiredError):
                pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(worker_lifecycle, f"user_{i}") for i in range(60)]
            concurrent.futures.wait(futures)

        report = engine.get_stock_report("GADGET-X")
        self.assertEqual(report.initial_stock, report.available + report.reserved + report.sold)
        self.assertGreaterEqual(report.available, 0)
        self.assertGreaterEqual(report.reserved, 0)
        self.assertGreaterEqual(report.sold, 0)

        engine.shutdown()

    def test_multi_sku_concurrency_isolation(self):
        """
        Confirms that high concurrency on SKU-A does not block or bottleneck SKU-B.
        """
        engine = FlashSaleEngine(
            inventory_source=[
                {"sku": "SKU-A", "stock": 10, "per_user_limit": 1},
                {"sku": "SKU-B", "stock": 10, "per_user_limit": 1},
            ],
            auto_start_sweeper=False,
        )

        def work(sku: str, idx: int):
            try:
                return engine.reserve(f"user_{sku}_{idx}", sku, 1)
            except InsufficientStockError:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures_a = [executor.submit(work, "SKU-A", i) for i in range(20)]
            futures_b = [executor.submit(work, "SKU-B", i) for i in range(20)]
            res_a = [f.result() for f in futures_a if f.result() is not None]
            res_b = [f.result() for f in futures_b if f.result() is not None]

        self.assertEqual(len(res_a), 10)
        self.assertEqual(len(res_b), 10)
        self.assertEqual(engine.get_stock_report("SKU-A").available, 0)
        self.assertEqual(engine.get_stock_report("SKU-B").available, 0)

        engine.shutdown()


if __name__ == "__main__":
    unittest.main()

