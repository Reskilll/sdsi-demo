"""
Unit & concurrency tests for the Inventory Reservation System.

Run:
    cd submissions/dinesh-pal
    python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import tempfile
import threading
import time

import pytest

from src import engine as engine_mod
from src.models import ErrorCode, ReservationState, SystemConfig


# ── Helpers ────────────────────────────────────────────────────────


def _make_inventory(
    skus: list[dict] | None = None,
    ttl: float = 120.0,
) -> str:
    """Write a temporary inventory.json and return its path."""
    if skus is None:
        skus = [
            {"sku": "SKU-A", "name": "Product A", "total_stock": 100, "per_user_limit": 5}
        ]
    data = {
        "products": skus,
        "config": {"reservation_ttl_seconds": ttl, "sweeper_interval_seconds": 0.1},
    }
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, f)
    f.close()
    return f.name


def _new_engine(inventory_skus=None, ttl=120.0) -> engine_mod.ReservationEngine:
    """Create a fully initialised engine with temp inventory and running sweeper."""
    path = _make_inventory(inventory_skus, ttl)
    eng = engine_mod.ReservationEngine()
    eng.load_inventory(path)
    eng.start_sweeper()
    return eng


# ═══════════════════════════════════════════════════════════════════
# M1: Product loading
# ═══════════════════════════════════════════════════════════════════


class TestProductLoading:
    """M1: Load products from inventory.json."""

    def test_loads_all_products(self):
        skus = [
            {"sku": "A", "name": "Alpha", "total_stock": 10, "per_user_limit": 2},
            {"sku": "B", "name": "Beta", "total_stock": 20, "per_user_limit": 3},
        ]
        eng = _new_engine(skus)
        report = eng.report_all()
        assert len(report) == 2
        assert report[0].sku == "A"
        assert report[0].total_stock == 10
        assert report[1].sku == "B"
        assert report[1].total_stock == 20

    def test_empty_inventory(self):
        eng = _new_engine([])
        assert eng.report_all() == []

    def test_file_not_found_raises(self):
        eng = engine_mod.ReservationEngine()
        with pytest.raises(FileNotFoundError):
            eng.load_inventory("/nonexistent/path.json")


# ═══════════════════════════════════════════════════════════════════
# M2: Reserve
# ═══════════════════════════════════════════════════════════════════


class TestReserve:
    """M2: Reserve stock with TTL."""

    def test_reserve_happy_path(self):
        eng = _new_engine()
        ok, rec = eng.reserve("SKU-A", "user-1", 3)
        assert ok
        assert rec.reservation_id
        assert rec.sku == "SKU-A"
        assert rec.quantity == 3
        assert rec.state == ReservationState.RESERVED
        r = eng.report_sku("SKU-A")
        assert r.reserved == 3
        assert r.available == 97

    def test_reserve_insufficient_stock(self):
        eng = _new_engine(
            [{"sku": "X", "name": "X", "total_stock": 2, "per_user_limit": 10}]
        )
        ok, err = eng.reserve("X", "u1", 3)
        assert not ok
        assert err["error"] == ErrorCode.INSUFFICIENT_STOCK.value

    def test_reserve_sku_not_found(self):
        eng = _new_engine()
        ok, err = eng.reserve("NONEXISTENT", "u1", 1)
        assert not ok
        assert err["error"] == ErrorCode.SKU_NOT_FOUND.value

    def test_reserve_zero_quantity_rejected(self):
        eng = _new_engine()
        ok, err = eng.reserve("SKU-A", "u1", 0)
        assert not ok
        assert err["error"] == ErrorCode.INVALID_REQUEST.value


# ═══════════════════════════════════════════════════════════════════
# M3: Confirm / Cancel
# ═══════════════════════════════════════════════════════════════════


class TestConfirm:
    """M3: Confirm permanently deducts stock."""

    def test_confirm_transitions_to_sold(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 5)
        ok, confirmed = eng.confirm(rec.reservation_id)
        assert ok
        assert confirmed.state == ReservationState.SOLD
        r = eng.report_sku("SKU-A")
        assert r.sold == 5
        assert r.reserved == 0

    def test_double_confirm_is_idempotent(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 2)
        eng.confirm(rec.reservation_id)
        ok, confirmed = eng.confirm(rec.reservation_id)
        assert ok
        assert confirmed.state == ReservationState.SOLD
        r = eng.report_sku("SKU-A")
        assert r.sold == 2  # not 4!

    def test_confirm_nonexistent_returns_error(self):
        eng = _new_engine()
        ok, err = eng.confirm("nonexistent-id")
        assert not ok
        assert err["error"] == ErrorCode.RESERVATION_NOT_FOUND.value

    def test_confirm_after_cancel_fails(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 1)
        eng.cancel(rec.reservation_id)
        ok, err = eng.confirm(rec.reservation_id)
        assert not ok
        assert err["error"] == ErrorCode.RESERVATION_ALREADY_TERMINAL.value


class TestCancel:
    """M3: Cancel releases stock back."""

    def test_cancel_releases_stock(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 3)
        ok, cancelled = eng.cancel(rec.reservation_id)
        assert ok
        assert cancelled.state == ReservationState.RELEASED
        r = eng.report_sku("SKU-A")
        assert r.reserved == 0
        assert r.available == 100

    def test_double_cancel_is_idempotent(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 2)
        eng.cancel(rec.reservation_id)
        ok, cancelled = eng.cancel(rec.reservation_id)
        assert ok
        assert cancelled.state == ReservationState.RELEASED

    def test_cancel_after_confirm_fails(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 1)
        eng.confirm(rec.reservation_id)
        ok, err = eng.cancel(rec.reservation_id)
        assert not ok
        assert err["error"] == ErrorCode.RESERVATION_ALREADY_TERMINAL.value


# ═══════════════════════════════════════════════════════════════════
# M4: Per-user purchase limit
# ═══════════════════════════════════════════════════════════════════


class TestUserLimits:
    """M4: Per-user purchase limit enforcement."""

    def test_limit_enforced_at_reserve(self):
        eng = _new_engine(
            [{"sku": "SKU-A", "name": "A", "total_stock": 100, "per_user_limit": 2}]
        )
        ok1, _ = eng.reserve("SKU-A", "u1", 1)
        assert ok1
        ok2, _ = eng.reserve("SKU-A", "u1", 1)
        assert ok2
        ok3, err = eng.reserve("SKU-A", "u1", 1)
        assert not ok3
        assert err["error"] == ErrorCode.USER_LIMIT_EXCEEDED.value

    def test_held_reservations_count_toward_limit(self):
        """Active (unconfirmed) reservations count toward the limit."""
        eng = _new_engine(
            [{"sku": "SKU-A", "name": "A", "total_stock": 100, "per_user_limit": 2}]
        )
        eng.reserve("SKU-A", "u1", 2)
        ok, err = eng.reserve("SKU-A", "u1", 1)
        assert not ok
        assert err["error"] == ErrorCode.USER_LIMIT_EXCEEDED.value

    def test_cancel_frees_limit_slot(self):
        eng = _new_engine(
            [{"sku": "SKU-A", "name": "A", "total_stock": 100, "per_user_limit": 2}]
        )
        _, r1 = eng.reserve("SKU-A", "u1", 1)
        _, r2 = eng.reserve("SKU-A", "u1", 1)
        eng.cancel(r1.reservation_id)
        ok, _ = eng.reserve("SKU-A", "u1", 1)
        assert ok

    def test_confirm_frees_limit_slot(self):
        """Confirmed (sold) reservations no longer count toward held limit."""
        eng = _new_engine(
            [{"sku": "SKU-A", "name": "A", "total_stock": 100, "per_user_limit": 2}]
        )
        _, r1 = eng.reserve("SKU-A", "u1", 1)
        eng.confirm(r1.reservation_id)
        ok, _ = eng.reserve("SKU-A", "u1", 2)
        assert ok


# ═══════════════════════════════════════════════════════════════════
# M5: Reports
# ═══════════════════════════════════════════════════════════════════


class TestReports:
    """M5: Real-time stock reports."""

    def test_initial_report_all_zero(self):
        eng = _new_engine(
            [{"sku": "SKU-A", "name": "A", "total_stock": 50, "per_user_limit": 5}]
        )
        r = eng.report_sku("SKU-A")
        assert r.sold == 0
        assert r.reserved == 0
        assert r.available == 50
        assert not r.is_sold_out

    def test_report_reflects_reservation(self):
        eng = _new_engine(
            [{"sku": "SKU-A", "name": "A", "total_stock": 100, "per_user_limit": 10}]
        )
        eng.reserve("SKU-A", "u1", 10)
        r = eng.report_sku("SKU-A")
        assert r.reserved == 10
        assert r.available == 90

    def test_report_after_sold_out(self):
        eng = _new_engine(
            [{"sku": "X", "name": "X", "total_stock": 1, "per_user_limit": 10}]
        )
        _, rec = eng.reserve("X", "u1", 1)
        eng.confirm(rec.reservation_id)
        r = eng.report_sku("X")
        assert r.sold == 1
        assert r.available == 0
        assert r.is_sold_out

    def test_report_all_includes_all_skus(self):
        skus = [
            {"sku": "A", "name": "A", "total_stock": 10, "per_user_limit": 1},
            {"sku": "B", "name": "B", "total_stock": 20, "per_user_limit": 2},
        ]
        eng = _new_engine(skus)
        reports = eng.report_all()
        assert len(reports) == 2
        assert {r.sku for r in reports} == {"A", "B"}


# ═══════════════════════════════════════════════════════════════════
# TTL Expiry
# ═══════════════════════════════════════════════════════════════════


class TestTTLExpiry:
    """TTL expiration — sweeper releases stale reservations."""

    def test_sweeper_releases_expired(self):
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": 10, "per_user_limit": 5}], ttl=0.05
        )
        _, rec = eng.reserve("A", "u1", 2)
        assert rec.state == ReservationState.RESERVED

        time.sleep(0.3)

        record = eng.get_reservation(rec.reservation_id)
        assert record is not None
        assert record.state == ReservationState.RELEASED

        r = eng.report_sku("A")
        assert r.reserved == 0
        assert r.available == 10

    def test_expired_reservation_cannot_be_confirmed(self):
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": 10, "per_user_limit": 5}], ttl=0.05
        )
        _, rec = eng.reserve("A", "u1", 1)
        time.sleep(0.3)
        ok, err = eng.confirm(rec.reservation_id)
        assert not ok
        record = eng.get_reservation(rec.reservation_id)
        assert record.state == ReservationState.RELEASED

    def test_expired_holds_free_user_limit(self):
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": 10, "per_user_limit": 2}], ttl=0.05
        )
        eng.reserve("A", "u1", 2)  # hit limit
        time.sleep(0.3)  # both expire
        ok, _ = eng.reserve("A", "u1", 2)
        assert ok


# ═══════════════════════════════════════════════════════════════════
# Idempotency
# ═══════════════════════════════════════════════════════════════════


class TestIdempotency:
    """Idempotency-key based deduplication."""

    def test_same_key_returns_same_success(self):
        eng = _new_engine()
        ok1, r1 = eng.reserve("SKU-A", "u1", 3, idempotency_key="ikey-1")
        assert ok1
        ok2, r2 = eng.reserve("SKU-A", "u2", 1, idempotency_key="ikey-1")
        assert ok2
        assert r2.reservation_id == r1.reservation_id
        assert r2.user_id == "u1"  # original user
        assert r2.quantity == 3  # original quantity

    def test_same_key_returns_same_error(self):
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": 1, "per_user_limit": 5}]
        )
        ok1, err1 = eng.reserve("A", "u1", 5, idempotency_key="ikey-err")
        assert not ok1
        ok2, err2 = eng.reserve("A", "u2", 1, idempotency_key="ikey-err")
        assert not ok2
        assert err2["error"] == err1["error"]

    def test_different_keys_are_independent(self):
        eng = _new_engine()
        ok1, r1 = eng.reserve("SKU-A", "u1", 1, idempotency_key="k1")
        ok2, r2 = eng.reserve("SKU-A", "u1", 1, idempotency_key="k2")
        assert ok1 and ok2
        assert r1.reservation_id != r2.reservation_id

    def test_idempotency_on_confirm(self):
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 2)
        ok1, _ = eng.confirm(rec.reservation_id, idempotency_key="conf-1")
        assert ok1
        ok2, _ = eng.confirm(rec.reservation_id, idempotency_key="conf-1")
        assert ok2


# ═══════════════════════════════════════════════════════════════════
# Concurrency: Zero Oversell
# ═══════════════════════════════════════════════════════════════════


class TestConcurrency:
    """Concurrency & race-condition safety."""

    def test_zero_oversell_under_parallel_reserve(self):
        """50 threads × 1 unit when only 30 available → exactly 30 succeed."""
        total_stock = 30
        workers = 50
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": total_stock, "per_user_limit": 10}]
        )

        results: list[tuple[bool, object]] = []
        lock = threading.Lock()

        def worker(i: int):
            ok, result = eng.reserve("A", f"user-{i}", 1)
            with lock:
                results.append((ok, result))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for ok, r in results if ok]
        failures = [r for ok, r in results if not ok]

        assert len(successes) == total_stock, (
            f"Expected exactly {total_stock} successful reservations, got {len(successes)}"
        )
        assert len(failures) == workers - total_stock

        r = eng.report_sku("A")
        assert r.reserved == total_stock
        assert r.available == 0

    def test_parallel_confirm_no_double_deduct(self):
        """50 threads confirming same reservation → sold count = qty, not 50*qty."""
        eng = _new_engine()
        qty = 5
        _, rec = eng.reserve("SKU-A", "u1", qty)

        results: list[bool] = []

        def worker():
            ok, _ = eng.confirm(rec.reservation_id)
            results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)
        r = eng.report_sku("SKU-A")
        assert r.sold == qty

    def test_parallel_cancel_no_double_release(self):
        """Many threads cancelling → stock only released once."""
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 3)

        def worker():
            eng.cancel(rec.reservation_id)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        r = eng.report_sku("SKU-A")
        assert r.reserved == 0
        assert r.available == 100

    def test_user_limit_race(self):
        """Two threads reserving the per-user limit → only one wins."""
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": 100, "per_user_limit": 3}]
        )
        winner_ids: list[str] = []

        def worker(qty: int):
            ok, result = eng.reserve("A", "same-user", qty)
            if ok:
                winner_ids.append(f"qty-{qty}")

        t1 = threading.Thread(target=worker, args=(3,))
        t2 = threading.Thread(target=worker, args=(3,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(winner_ids) == 1, (
            f"Expected 1 success, got {len(winner_ids)}: {winner_ids}"
        )

    def test_reserve_and_expire_race(self):
        """Expired stock becomes available for new reservations."""
        eng = _new_engine(
            [{"sku": "A", "name": "A", "total_stock": 2, "per_user_limit": 5}],
            ttl=0.05,
        )
        _, r1 = eng.reserve("A", "u1", 1)
        _, r2 = eng.reserve("A", "u1", 1)

        time.sleep(0.3)

        ok3, _ = eng.reserve("A", "u2", 1)
        ok4, _ = eng.reserve("A", "u3", 1)
        assert ok3 and ok4

        r = eng.report_sku("A")
        assert r.reserved == 2
        assert r.available == 0


# ═══════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Additional edge cases."""

    def test_sweeper_starts_and_stops(self):
        eng = _new_engine()
        assert eng.sweeper.is_running
        eng.stop()
        assert not eng.sweeper.is_running

    def test_get_reservation_returns_none_for_unknown(self):
        eng = _new_engine()
        assert eng.get_reservation("nope") is None

    def test_report_unknown_sku_returns_none(self):
        eng = _new_engine()
        assert eng.report_sku("nope") is None

    def test_ttl_uses_monotonic_no_clock_drift_bug(self):
        """time.monotonic() used everywhere — never goes backward."""
        eng = _new_engine()
        _, rec = eng.reserve("SKU-A", "u1", 1)
        assert rec.expires_at > rec.created_at
        assert rec.created_at > 0

    def test_total_stock_zero(self):
        eng = _new_engine(
            [{"sku": "ZERO", "name": "None", "total_stock": 0, "per_user_limit": 1}]
        )
        ok, err = eng.reserve("ZERO", "u1", 1)
        assert not ok
        assert err["error"] == ErrorCode.INSUFFICIENT_STOCK.value