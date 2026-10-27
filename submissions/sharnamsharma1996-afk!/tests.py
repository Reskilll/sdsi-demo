"""Tests for the flash-sale inventory reservation system.

Runs with pytest (``pytest``) or standalone (``python tests.py``).
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Make ``reservation`` importable when run directly (no package layout).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from reservation import (
    DataLoadError,
    InsufficientStock,
    InvalidQuantity,
    InventoryError,
    InventorySystem,
    ReservationExpired,
    ReservationNotActive,
    ReservationNotFound,
    SkuNotFound,
    Unauthorized,
    UserLimitExceeded,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE = {
    "config": {"reservation_ttl_seconds": 120},
    "products": [
        {"sku": "PS5", "name": "PlayStation 5", "total_stock": 10, "per_user_limit": 1},
        {"sku": "AIRPODS", "name": "AirPods Pro", "total_stock": 5, "per_user_limit": 2},
        {"sku": "NOLIMIT", "name": "No Limit Item", "total_stock": 3, "per_user_limit": 0},
    ],
}


def make_system(ttl: float = 120.0, products: dict | None = None) -> InventorySystem:
    inv = InventorySystem(ttl=ttl)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        import json
        json.dump(products if products is not None else SAMPLE, fh)
        path = fh.name
    inv.load_products(path)
    os.unlink(path)
    return inv


def _report(inv, sku):
    return next(r for r in inv.report() if r.sku == sku)


# ---------------------------------------------------------------------------
# M1: Load products
# ---------------------------------------------------------------------------

def test_load_products_basic():
    inv = make_system()
    assert len(inv.report()) == 3
    ps5 = _report(inv, "PS5")
    assert ps5.total_stock == 10
    assert ps5.available == 10
    assert ps5.reserved == 0
    assert ps5.sold == 0


def test_load_products_missing_file():
    inv = InventorySystem()
    try:
        inv.load_products("does_not_exist.json")
        assert False, "expected DataLoadError"
    except DataLoadError:
        pass


def test_load_products_invalid_json():
    inv = InventorySystem()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write("{ not valid json")
        path = fh.name
    try:
        inv.load_products(path)
        assert False, "expected DataLoadError"
    except DataLoadError:
        pass
    finally:
        os.unlink(path)


def test_load_products_negative_stock_rejected():
    bad = {"products": [{"sku": "X", "total_stock": -1}]}
    inv = InventorySystem()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        import json
        json.dump(bad, fh)
        path = fh.name
    try:
        inv.load_products(path)
        assert False, "expected DataLoadError"
    except DataLoadError:
        pass
    finally:
        os.unlink(path)


def test_load_products_duplicate_sku_rejected():
    bad = {"products": [
        {"sku": "X", "total_stock": 1},
        {"sku": "X", "total_stock": 2},
    ]}
    inv = InventorySystem()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        import json
        json.dump(bad, fh)
        path = fh.name
    try:
        inv.load_products(path)
        assert False, "expected DataLoadError"
    except DataLoadError:
        pass
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# M2: Reserve with TTL
# ---------------------------------------------------------------------------

def test_reserve_basic():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    assert r.sku == "PS5"
    assert r.quantity == 1
    assert r.status == "active"
    assert r.user_id == "alice"
    assert r.expires_at > time.time()

    ps5 = _report(inv, "PS5")
    assert ps5.available == 9
    assert ps5.reserved == 1
    assert ps5.sold == 0


def test_reserve_default_ttl_from_config():
    inv = make_system()  # config sets 120s
    r = inv.reserve("alice", "PS5")
    assert 110 < r.expires_at - time.time() <= 120


def test_reserve_custom_ttl_override():
    inv = make_system()
    r = inv.reserve("alice", "PS5", ttl=5)
    assert 0 < r.expires_at - time.time() <= 5


def test_reserve_invalid_quantity():
    inv = make_system()
    for bad in (0, -1, -100):
        try:
            inv.reserve("alice", "PS5", quantity=bad)
            assert False, f"expected InvalidQuantity for {bad}"
        except InvalidQuantity:
            pass


def test_reserve_unknown_sku():
    inv = make_system()
    try:
        inv.reserve("alice", "NOPE")
        assert False, "expected SkuNotFound"
    except SkuNotFound:
        pass


def test_reserve_exceeding_stock():
    inv = make_system()
    try:
        inv.reserve("alice", "PS5", quantity=11)
        assert False, "expected InsufficientStock"
    except InsufficientStock:
        pass


def test_reserve_empty_user_id():
    inv = make_system()
    try:
        inv.reserve("", "PS5")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# M3: Confirm / cancel / TTL expiry
# ---------------------------------------------------------------------------

def test_confirm_deducts_stock():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    inv.confirm(r.id)
    ps5 = _report(inv, "PS5")
    assert ps5.available == 9
    assert ps5.reserved == 0
    assert ps5.sold == 1


def test_cancel_releases_stock():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    inv.cancel(r.id)
    ps5 = _report(inv, "PS5")
    assert ps5.available == 10
    assert ps5.reserved == 0
    assert ps5.sold == 0


def test_ttl_expiry_releases_stock():
    inv = make_system(ttl=0.05)
    inv.reserve("alice", "PS5", ttl=0.05)
    time.sleep(0.15)
    ps5 = _report(inv, "PS5")
    assert ps5.available == 10
    assert ps5.reserved == 0
    assert ps5.sold == 0


def test_confirm_expired_reservation_fails():
    inv = make_system(ttl=0.05)
    r = inv.reserve("alice", "PS5", ttl=0.05)
    time.sleep(0.15)
    try:
        inv.confirm(r.id)
        assert False, "expected ReservationExpired"
    except ReservationExpired:
        pass


def test_double_confirm_fails():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    inv.confirm(r.id)
    try:
        inv.confirm(r.id)
        assert False, "expected ReservationNotActive"
    except ReservationNotActive:
        pass


def test_cancel_after_confirm_fails():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    inv.confirm(r.id)
    try:
        inv.cancel(r.id)
        assert False, "expected ReservationNotActive"
    except ReservationNotActive:
        pass


def test_confirm_unknown_reservation_fails():
    inv = make_system()
    try:
        inv.confirm("rsv_nonexistent")
        assert False, "expected ReservationNotFound"
    except ReservationNotFound:
        pass


# ---------------------------------------------------------------------------
# M4: Per-user purchase limit
# ---------------------------------------------------------------------------

def test_per_user_limit_enforced_on_reserve():
    inv = make_system()
    inv.reserve("alice", "AIRPODS")  # limit 2, take 1
    inv.reserve("alice", "AIRPODS")  # take 2nd
    try:
        inv.reserve("alice", "AIRPODS")  # 3rd -> rejected
        assert False, "expected UserLimitExceeded"
    except UserLimitExceeded:
        pass


def test_per_user_limit_aggregates_confirmed_and_reserved():
    inv = make_system()
    r1 = inv.reserve("alice", "AIRPODS")
    inv.confirm(r1.id)  # confirmed: 1
    inv.reserve("alice", "AIRPODS")  # reserved: 1 (total now 2)
    try:
        inv.reserve("alice", "AIRPODS")  # would make 3
        assert False, "expected UserLimitExceeded"
    except UserLimitExceeded:
        pass


def test_per_user_limit_zero_means_unlimited():
    inv = make_system()
    inv.reserve("alice", "NOLIMIT")  # stock 3, no limit
    inv.reserve("alice", "NOLIMIT")
    inv.reserve("alice", "NOLIMIT")  # exhausts stock but no limit error
    try:
        inv.reserve("alice", "NOLIMIT")  # out of stock now
        assert False, "expected InsufficientStock"
    except InsufficientStock:
        pass


def test_different_users_have_independent_limits():
    inv = make_system()
    inv.reserve("alice", "AIRPODS")
    inv.reserve("alice", "AIRPODS")
    # bob has his own limit
    inv.reserve("bob", "AIRPODS")
    inv.reserve("bob", "AIRPODS")
    try:
        inv.reserve("bob", "AIRPODS")
        assert False, "expected UserLimitExceeded"
    except UserLimitExceeded:
        pass


# ---------------------------------------------------------------------------
# M5: Reporting
# ---------------------------------------------------------------------------

def test_report_all_skus():
    inv = make_system()
    reports = inv.report()
    skus = {r.sku for r in reports}
    assert skus == {"PS5", "AIRPODS", "NOLIMIT"}


def test_report_single_sku():
    inv = make_system()
    reports = inv.report("PS5")
    assert len(reports) == 1
    assert reports[0].sku == "PS5"


def test_report_unknown_sku():
    inv = make_system()
    try:
        inv.report("NOPE")
        assert False, "expected SkuNotFound"
    except SkuNotFound:
        pass


# ---------------------------------------------------------------------------
# Edge cases & robustness
# ---------------------------------------------------------------------------

def test_reservation_id_uniqueness():
    inv = make_system()
    ids = {inv.reserve("u", "NOLIMIT").id for _ in range(100)}
    assert len(ids) == 100


def test_race_two_users_last_item():
    inv = make_system()  # PS5 stock 10
    # Simulate heavy contention: 20 threads each trying to reserve 1 PS5
    results = []
    lock = threading.Lock()

    def worker(i):
        try:
            r = inv.reserve(f"user{i}", "PS5")
            with lock:
                results.append(r)
        except InsufficientStock:
            with lock:
                results.append(None)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successful = [r for r in results if r is not None]
    assert len(successful) == 10, f"expected 10 successful, got {len(successful)}"
    ps5 = _report(inv, "PS5")
    assert ps5.reserved == 10
    assert ps5.available == 0
    assert ps5.sold == 0


def test_confirmation_after_other_user_cancels_frees_stock():
    inv = make_system()
    r1 = inv.reserve("alice", "PS5")
    inv.cancel(r1.id)
    # stock freed, bob can now reserve
    r2 = inv.reserve("bob", "PS5")
    inv.confirm(r2.id)
    ps5 = _report(inv, "PS5")
    assert ps5.sold == 1
    assert ps5.available == 9


def test_confirmation_with_wrong_user_rejected():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    try:
        inv.confirm(r.id, user_id="mallory")
        assert False, "expected Unauthorized"
    except Unauthorized:
        pass


def test_confirmation_with_correct_user_ok():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    inv.confirm(r.id, user_id="alice")  # should not raise
    assert _report(inv, "PS5").sold == 1


def test_cancel_with_wrong_user_rejected():
    inv = make_system()
    r = inv.reserve("alice", "PS5")
    try:
        inv.cancel(r.id, user_id="mallory")
        assert False, "expected Unauthorized"
    except Unauthorized:
        pass


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_state_persistence_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = str(Path(tmpdir) / "state.json")
        inv = InventorySystem(state_file=state_path, ttl=120)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            import json
            json.dump(SAMPLE, fh)
            inv_path = fh.name
        inv.load_products(inv_path)
        os.unlink(inv_path)

        r = inv.reserve("alice", "PS5")
        inv.confirm(r.id)
        inv.reserve("bob", "AIRPODS")

        # Re-open from disk — products + state are both persisted, no re-load
        inv2 = InventorySystem(state_file=state_path, ttl=120)

        ps5 = _report(inv2, "PS5")
        assert ps5.sold == 1
        assert ps5.available == 9  # 1 sold

        airpods = _report(inv2, "AIRPODS")
        assert airpods.reserved == 1


def test_expired_reservation_swept_after_reload():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = str(Path(tmpdir) / "state.json")
        inv = InventorySystem(state_file=state_path, ttl=0.05)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            import json
            json.dump(SAMPLE, fh)
            inv_path = fh.name
        inv.load_products(inv_path)
        os.unlink(inv_path)

        inv.reserve("alice", "PS5", ttl=0.05)
        time.sleep(0.15)

        # Re-open — the expired reservation should be swept on next access
        inv2 = InventorySystem(state_file=state_path, ttl=0.05)

        ps5 = _report(inv2, "PS5")
        assert ps5.available == 10
        assert ps5.reserved == 0


# ---------------------------------------------------------------------------
# Standalone runner (no pytest required)
# ---------------------------------------------------------------------------

def _run_all():
    tests = [
        (k, v) for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {name}: {exc!r}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
