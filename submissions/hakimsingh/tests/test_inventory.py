"""Tests for the inventory reservation system (PS4)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

# Ensure the package is importable (add submissions/ps4/ to path)
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from errors import (
    InsufficientStockError,
    InvalidDataError,
    InvalidTransitionError,
    PerUserLimitError,
    ReservationExpiredError,
    ReservationNotFoundError,
)
from loader import load_inventory
from models import Product, ReservationState
from service import InventoryReservationEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_products():
    return {
        "TSHIRT-BLK": Product("TSHIRT-BLK", "Black T-Shirt", 100, 3, 120),
        "TSHIRT-WHT": Product("TSHIRT-WHT", "White T-Shirt", 50, 2, 60),
        "MUG-CRM": Product("MUG-CRM", "Ceramic Mug", 25, 5, 120),
        "STKR-SET": Product("STKR-SET", "Sticker Set", 200, 10, 300),
    }


@pytest.fixture
def engine(sample_products):
    return InventoryReservationEngine(sample_products)


def make_inventory_file(products: list[dict]) -> str:
    """Write a temporary inventory.json and return its path."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="inventory_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f)
    return path


# ---------------------------------------------------------------------------
# M1 — Load and validate inventory.json
# ---------------------------------------------------------------------------

class TestM1Loading:
    def test_load_valid(self):
        """Happy path: well-formed inventory loads correctly."""
        path = make_inventory_file([
            {"sku": "A", "name": "A", "total": 10, "per_user_limit": 2},
            {"sku": "B", "name": "B", "total": 5, "per_user_limit": 1, "ttl_seconds": 30},
        ])
        products = load_inventory(path)
        assert len(products) == 2
        assert products["A"].sku == "A"
        assert products["A"].ttl_seconds == 120  # default
        assert products["B"].ttl_seconds == 30
        os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(InvalidDataError, match="not found"):
            load_inventory("/nonexistent/path.json")

    def test_malformed_json(self):
        path = make_inventory_file([])
        with open(path, "w") as f:
            f.write("not json")
        with pytest.raises(InvalidDataError, match="parse"):
            load_inventory(path)
        os.unlink(path)

    def test_empty_array(self):
        path = make_inventory_file([])
        with pytest.raises(InvalidDataError, match="no valid products"):
            load_inventory(path)
        os.unlink(path)

    def test_not_a_list(self):
        path = make_inventory_file([])
        with open(path, "w") as f:
            f.write('"string"')
        with pytest.raises(InvalidDataError, match="JSON array"):
            load_inventory(path)
        os.unlink(path)

    def test_duplicate_sku(self):
        path = make_inventory_file([
            {"sku": "A", "name": "A", "total": 10, "per_user_limit": 2},
            {"sku": "A", "name": "A dup", "total": 5, "per_user_limit": 1},
        ])
        with pytest.raises(InvalidDataError, match="Duplicate"):
            load_inventory(path)
        os.unlink(path)

    def test_missing_fields(self):
        path = make_inventory_file([
            {"sku": "A", "name": "A"},  # missing total, per_user_limit
        ])
        with pytest.raises(InvalidDataError, match="missing"):
            load_inventory(path)
        os.unlink(path)

    def test_bad_total_non_int(self):
        path = make_inventory_file([
            {"sku": "A", "name": "A", "total": 10.5, "per_user_limit": 2},
        ])
        with pytest.raises(InvalidDataError, match="positive integer"):
            load_inventory(path)
        os.unlink(path)

    def test_bad_total_zero(self):
        path = make_inventory_file([
            {"sku": "A", "name": "A", "total": 0, "per_user_limit": 2},
        ])
        with pytest.raises(InvalidDataError, match="positive integer"):
            load_inventory(path)
        os.unlink(path)

    def test_per_user_limit_exceeds_total(self):
        path = make_inventory_file([
            {"sku": "A", "name": "A", "total": 5, "per_user_limit": 10},
        ])
        with pytest.raises(InvalidDataError, match="not exceed"):
            load_inventory(path)
        os.unlink(path)

    def test_bad_sku_empty_string(self):
        path = make_inventory_file([
            {"sku": "", "name": "A", "total": 10, "per_user_limit": 2},
        ])
        with pytest.raises(InvalidDataError, match="non-empty"):
            load_inventory(path)
        os.unlink(path)

    def test_bad_sku_not_string(self):
        path = make_inventory_file([
            {"sku": 123, "name": "A", "total": 10, "per_user_limit": 2},
        ])
        with pytest.raises(InvalidDataError, match="non-empty"):
            load_inventory(path)
        os.unlink(path)

    def test_dict_wrapper_products_key(self):
        """Support {"products": [...]} wrapping."""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"products": [{"sku": "A", "name": "A", "total": 10, "per_user_limit": 2}]}, f)
        products = load_inventory(path)
        assert "A" in products
        os.unlink(path)


# ---------------------------------------------------------------------------
# M2 — Reserve stock
# ---------------------------------------------------------------------------

class TestM2Reserve:
    def test_basic_reserve(self, engine):
        rid, expires = engine.reserve("TSHIRT-BLK", "alice", 2)
        assert rid is not None
        assert isinstance(rid, str) and len(rid) > 0
        assert expires > datetime.now(timezone.utc)

    def test_reserve_reduces_available(self, engine):
        before = engine.report("TSHIRT-BLK")
        engine.reserve("TSHIRT-BLK", "alice", 3)
        after = engine.report("TSHIRT-BLK")
        assert after["available"] == before["available"] - 3
        assert after["reserved"] == before["reserved"] + 3

    def test_reserve_zero_qty(self, engine):
        with pytest.raises(InvalidDataError, match="positive integer"):
            engine.reserve("TSHIRT-BLK", "alice", 0)

    def test_reserve_negative_qty(self, engine):
        with pytest.raises(InvalidDataError, match="positive integer"):
            engine.reserve("TSHIRT-BLK", "alice", -1)

    def test_reserve_non_int_qty(self, engine):
        with pytest.raises(InvalidDataError, match="positive integer"):
            engine.reserve("TSHIRT-BLK", "alice", "two")

    def test_reserve_unknown_sku(self, engine):
        with pytest.raises(InvalidDataError, match="Unknown SKU"):
            engine.reserve("NONEXIST", "alice", 1)

    def test_reserve_empty_user(self, engine):
        with pytest.raises(InvalidDataError, match="non-empty"):
            engine.reserve("TSHIRT-BLK", "", 1)

    def test_reserve_exceeds_stock(self, engine):
        with pytest.raises(InsufficientStockError, match="only 25 available"):
            engine.reserve("MUG-CRM", "alice", 26)


# ---------------------------------------------------------------------------
# M3 — Confirm / Cancel / Expiry
# ---------------------------------------------------------------------------

class TestM3ConfirmCancelExpiry:
    def test_confirm_reduces_reserved_increases_sold(self, engine):
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 2)
        before = engine.report("TSHIRT-BLK")
        engine.confirm(rid)
        after = engine.report("TSHIRT-BLK")
        assert after["reserved"] == before["reserved"] - 2
        assert after["sold"] == before["sold"] + 2
        assert after["available"] == before["available"]

    def test_cancel_releases_stock(self, engine):
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 2)
        before = engine.report("TSHIRT-BLK")
        engine.cancel(rid)
        after = engine.report("TSHIRT-BLK")
        assert after["reserved"] == before["reserved"] - 2
        assert after["available"] == before["available"] + 2

    def test_double_confirm_fails(self, engine):
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 1)
        engine.confirm(rid)
        with pytest.raises(InvalidTransitionError, match="already confirmed"):
            engine.confirm(rid)

    def test_confirm_after_cancel_fails(self, engine):
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 1)
        engine.cancel(rid)
        with pytest.raises(InvalidTransitionError, match="cancelled"):
            engine.confirm(rid)

    def test_cancel_unknown_id(self, engine):
        with pytest.raises(ReservationNotFoundError, match="not found"):
            engine.cancel("bogus-id")

    def test_confirm_unknown_id(self, engine):
        with pytest.raises(ReservationNotFoundError, match="not found"):
            engine.confirm("bogus-id")

    def test_cancel_after_confirm_fails(self, engine):
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 1)
        engine.confirm(rid)
        with pytest.raises(InvalidTransitionError, match="confirmed"):
            engine.cancel(rid)

    def test_lazy_expiry_on_confirm(self, engine):
        """Expired reservation raises on confirm (lazy check)."""
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 1)
        # Force expiry
        with engine._lock:
            rec = engine._reservations[rid]
            rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)  # 100ms in the past
        with pytest.raises(ReservationExpiredError, match="expired"):
            engine.confirm(rid)

    def test_lazy_expiry_returns_stock(self, engine):
        """After expiry, stock is released."""
        rid, _ = engine.reserve("MUG-CRM", "alice", 5)
        with engine._lock:
            rec = engine._reservations[rid]
            rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)
        # Trigger lazy expiry via confirm fail
        try:
            engine.confirm(rid)
        except ReservationExpiredError:
            pass
        report = engine.report("MUG-CRM")
        assert report["available"] == 25  # back to full

    def test_sweeper_releases_expired(self, engine):
        """Background sweeper releases expired stock."""
        rid, _ = engine.reserve("MUG-CRM", "alice", 5)
        with engine._lock:
            rec = engine._reservations[rid]
            rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)

        engine.start_sweeper(interval=0.5)
        time.sleep(1)
        engine.stop_sweeper()

        report = engine.report("MUG-CRM")
        assert report["available"] == 25

    def test_cancel_of_expired_reservation(self, engine):
        """Cancelling an already-expired reservation is allowed."""
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 1)
        with engine._lock:
            rec = engine._reservations[rid]
            rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)
        # Trigger lazy expiry
        try:
            engine.confirm(rid)
        except ReservationExpiredError:
            pass
        # Now cancel the expired marker
        engine.cancel(rid)
        report = engine.report("TSHIRT-BLK")
        assert report["available"] == 100


# ---------------------------------------------------------------------------
# M4 — Per-user purchase limit
# ---------------------------------------------------------------------------

class TestM4PerUserLimit:
    def test_enforce_limit(self, engine):
        """User cannot reserve beyond per_user_limit."""
        engine.reserve("TSHIRT-BLK", "alice", 3)
        with pytest.raises(PerUserLimitError, match="may hold at most 3"):
            engine.reserve("TSHIRT-BLK", "alice", 1)

    def test_limit_counts_reserved_and_sold(self, engine):
        """Both reserved and confirmed count toward the limit."""
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 2)
        engine.confirm(rid)
        # alice now has sold=2, can only reserve 1 more
        engine.reserve("TSHIRT-BLK", "alice", 1)
        with pytest.raises(PerUserLimitError):
            engine.reserve("TSHIRT-BLK", "alice", 1)

    def test_different_users_independent_limits(self, engine):
        """Two users each get their own limit."""
        engine.reserve("TSHIRT-BLK", "alice", 3)
        engine.reserve("TSHIRT-BLK", "bob", 3)  # bob has his own limit

    def test_limit_after_cancel(self, engine):
        """Cancelling frees up the user's quota."""
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 3)
        engine.cancel(rid)
        engine.reserve("TSHIRT-BLK", "alice", 2)  # now allowed

    def test_limit_after_expiry(self, engine):
        """Expiry frees up the user's quota."""
        rid, _ = engine.reserve("MUG-CRM", "alice", 3)
        with engine._lock:
            rec = engine._reservations[rid]
            rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)
        # Trigger lazy expiry
        try:
            engine.confirm(rid)
        except ReservationExpiredError:
            pass
        engine.reserve("MUG-CRM", "alice", 2)  # now allowed


# ---------------------------------------------------------------------------
# M5 — Reporting
# ---------------------------------------------------------------------------

class TestM5Reporting:
    def test_report_single_sku(self, engine):
        report = engine.report("TSHIRT-BLK")
        assert report["sku"] == "TSHIRT-BLK"
        assert report["total"] == 100
        assert report["available"] == 100
        assert report["reserved"] == 0
        assert report["sold"] == 0

    def test_report_all(self, engine):
        report = engine.report()
        assert isinstance(report, dict)
        assert "TSHIRT-BLK" in report
        assert len(report) == 4

    def test_report_reflects_reservations(self, engine):
        engine.reserve("MUG-CRM", "alice", 5)
        engine.reserve("MUG-CRM", "bob", 3)
        engine.reserve("STKR-SET", "alice", 5)
        report = engine.report()
        assert report["MUG-CRM"]["reserved"] == 8
        assert report["MUG-CRM"]["available"] == 17
        assert report["STKR-SET"]["reserved"] == 5
        assert report["STKR-SET"]["available"] == 195

    def test_report_unknown_sku(self, engine):
        with pytest.raises(InvalidDataError, match="Unknown SKU"):
            engine.report("BOGUS")


# ---------------------------------------------------------------------------
# Concurrency: the core invariant
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_reserve_no_oversell(self, engine):
        """Two threads racing for the last unit — only one wins."""
        mug = Product("MUG-CRM", "Ceramic Mug", 2, 2, 120)
        eng = InventoryReservationEngine({"MUG-CRM": mug})

        results: list[str | None] = [None, None]

        def reserve_for(user: str, idx: int):
            try:
                rid, _ = eng.reserve("MUG-CRM", user, 2)
                results[idx] = rid
            except InsufficientStockError:
                results[idx] = None

        t1 = threading.Thread(target=reserve_for, args=("alice", 0))
        t2 = threading.Thread(target=reserve_for, args=("bob", 1))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        winners = sum(1 for r in results if r is not None)
        assert winners == 1, f"Expected exactly one winner, got {winners}"

    def test_many_concurrent_reserves_honour_invariant(self, engine):
        """Many concurrent reservations must never violate reserved+sold <= total."""
        sku = "TSHIRT-BLK"
        eng = InventoryReservationEngine({
            sku: Product(sku, "Test", 10, 3, 300),
        })

        n_users = 20
        threads = []
        successes = []

        def reserve_and_record(user: str):
            try:
                rid, _ = eng.reserve(sku, user, 1)
                successes.append(rid)
            except (InsufficientStockError, PerUserLimitError, InvalidDataError):
                pass

        for i in range(n_users):
            t = threading.Thread(target=reserve_and_record, args=(f"user{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        report = eng.report(sku)
        assert report["reserved"] + report["sold"] + report["available"] == 10
        assert report["reserved"] + report["sold"] <= 10
        assert len(successes) <= 10

    def test_confirm_concurrent_with_report(self, engine):
        """Confirm and report can run concurrently without corrupting state."""
        rid, _ = engine.reserve("MUG-CRM", "alice", 3)
        errors: list[str] = []

        def confirm_thread():
            try:
                engine.confirm(rid)
            except Exception as e:
                errors.append(str(e))

        def report_thread():
            for _ in range(100):
                try:
                    r = engine.report("MUG-CRM")
                    assert r["reserved"] + r["sold"] + r["available"] == 25
                except Exception as e:
                    errors.append(str(e))

        t1 = threading.Thread(target=confirm_thread)
        t2 = threading.Thread(target=report_thread)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors, f"Errors: {errors}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_exact_stock_reserve(self, engine):
        """Reserving exactly all remaining stock succeeds (using multiple users)."""
        engine.reserve("MUG-CRM", "alice", 5)
        engine.reserve("MUG-CRM", "bob", 5)
        engine.reserve("MUG-CRM", "charlie", 5)
        engine.reserve("MUG-CRM", "diana", 5)
        engine.reserve("MUG-CRM", "eve", 5)
        report = engine.report("MUG-CRM")
        assert report["available"] == 0

    def test_two_users_last_unit(self, engine):
        """Two users fighting for the last unit — exactly one wins."""
        eng = InventoryReservationEngine({
            "A": Product("A", "A", 1, 1, 300),
        })
        results = []
        lock = threading.Lock()

        def try_reserve(user: str):
            try:
                rid, _ = eng.reserve("A", user, 1)
                with lock:
                    results.append((user, rid))
            except InsufficientStockError:
                pass

        t1 = threading.Thread(target=try_reserve, args=("alice",))
        t2 = threading.Thread(target=try_reserve, args=("bob",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(results) == 1

    def test_report_consistency_mid_mutation(self, engine):
        """Report runs under lock so it never sees half-updated state."""
        engine.reserve("STKR-SET", "alice", 10)
        report = engine.report()
        assert report["STKR-SET"]["available"] == 190

    def test_cancel_then_reserve_same_user(self, engine):
        """User who cancels can re-reserve within their limit."""
        rid, _ = engine.reserve("TSHIRT-BLK", "alice", 2)
        engine.cancel(rid)
        engine.reserve("TSHIRT-BLK", "alice", 2)  # should work

    def test_unknown_sku_on_report(self, engine):
        with pytest.raises(InvalidDataError, match="Unknown SKU"):
            engine.report("NOPE")

    def test_negative_total_not_allowed(self):
        """Loader rejects negative total."""
        path = make_inventory_file([
            {"sku": "A", "name": "A", "total": -5, "per_user_limit": 2},
        ])
        with pytest.raises(InvalidDataError, match="positive integer"):
            load_inventory(path)
        os.unlink(path)

    def test_sweeper_multiple_expired(self, engine):
        """Sweeper handles many expired reservations at once."""
        for i in range(10):
            engine.reserve("TSHIRT-BLK", f"user{i}", 1)
        # Force all to expire
        with engine._lock:
            for rec in engine._reservations.values():
                rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)
        released = engine._release_expired()
        assert released == 10
        report = engine.report("TSHIRT-BLK")
        assert report["available"] == 100


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

class TestInvariant:
    """After every operation, reserved + sold <= total must hold."""

    def _check_all(self, engine):
        for sku in engine._product_states:
            st = engine._product_states[sku]
            assert st.invariant_holds, (
                f"Invariant violated for {sku}: reserved({st.reserved}) + "
                f"sold({st.sold}) > total({st.total})"
            )

    def test_invariant_after_reserve(self, engine):
        for i in range(5):
            engine.reserve("TSHIRT-BLK", f"user{i}", 3)
            self._check_all(engine)

    def test_invariant_after_confirm(self, engine):
        rids = []
        for i in range(3):
            rid, _ = engine.reserve("TSHIRT-BLK", f"user{i}", 3)
            rids.append(rid)
        for rid in rids:
            engine.confirm(rid)
            self._check_all(engine)

    def test_invariant_after_cancel(self, engine):
        rid, _ = engine.reserve("STKR-SET", "alice", 5)
        self._check_all(engine)
        engine.cancel(rid)
        self._check_all(engine)

    def test_invariant_after_expiry(self, engine):
        rid, _ = engine.reserve("STKR-SET", "alice", 5)
        with engine._lock:
            rec = engine._reservations[rid]
            rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=0.1)
        engine._release_expired()
        self._check_all(engine)