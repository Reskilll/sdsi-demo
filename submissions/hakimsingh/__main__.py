"""Demo CLI for the inventory reservation system.

Run:  python -m submissions.ps4
"""

from __future__ import annotations

import sys
import time
import os
import traceback

# Allow running as `python -m submissions.ps4`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from errors import InventoryError
from loader import load_inventory
from reporting import format_report, heading
from service import InventoryReservationEngine


def main() -> None:
    inventory_path = os.path.join(os.path.dirname(__file__), "inventory.json")

    try:
        products = load_inventory(inventory_path)
    except InventoryError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    engine = InventoryReservationEngine(products)

    print(heading("INVENTORY RESERVATION SYSTEM - Flash Sale Demo"))
    print("Products loaded:")
    print(format_report(engine.report()))

    # ------------------------------------------------------------------
    # 1. Reserve units for user alice
    # ------------------------------------------------------------------
    print(heading("Reserve"))
    try:
        rid1, expires = engine.reserve("TSHIRT-BLK", "alice", 2)
        print(f"Reservation {rid1} created for alice (qty=2), expires at {expires}")
    except InventoryError as exc:
        print(f"ERROR: {exc}")

    # Try to exceed per-user limit
    print("\n--- Alice tries to reserve beyond her per_user_limit of 3 ---")
    try:
        engine.reserve("TSHIRT-BLK", "alice", 2)
    except InventoryError as exc:
        print(f"  -> Correctly refused: {exc}")

    # ------------------------------------------------------------------
    # 2. Report mid-state
    # ------------------------------------------------------------------
    print(heading("Report after reservation"))
    print(format_report(engine.report("TSHIRT-BLK")))

    # ------------------------------------------------------------------
    # 3. Confirm
    # ------------------------------------------------------------------
    print(heading("Confirm"))
    try:
        engine.confirm(rid1)
        print(f"Reservation {rid1} confirmed")
    except InventoryError as exc:
        print(f"ERROR: {exc}")

    print(heading("Report after confirm"))
    print(format_report(engine.report("TSHIRT-BLK")))

    # ------------------------------------------------------------------
    # 4. Cancel a reservation
    # ------------------------------------------------------------------
    try:
        rid2, _ = engine.reserve("TSHIRT-WHT", "bob", 1)
        print(f"\nReservation {rid2} created for bob (qty=1)")
        engine.cancel(rid2)
        print(f"Reservation {rid2} cancelled - stock released")
    except InventoryError as exc:
        print(f"ERROR: {exc}")

    print(heading("Report after cancel"))
    print(format_report(engine.report("TSHIRT-WHT")))

    # ------------------------------------------------------------------
    # 5. Reservation expiry (demonstrate lazy + eager)
    # ------------------------------------------------------------------
    print(heading("Expiry Demo"))
    # Create a reservation on a short-TTL product
    rid3, _ = engine.reserve("TSHIRT-WHT", "charlie", 1)
    print(f"Reservation {rid3} created for charlie (TSHIRT-WHT, TTL=60s)")
    # Force expiry by advancing time (we cannot freeze time in a demo, so lazy check)
    # Override expires_at to force immediate expiry for demo
    from datetime import datetime, timedelta, timezone
    from models import ReservationState

    with engine._lock:
        rec = engine._reservations[rid3]
        rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)  # expire 1s ago

    # Lazy expiry — confirm should now raise
    try:
        engine.confirm(rid3)
    except InventoryError as exc:
        print(f"  -> Lazy-expiry caught it: {exc}")

    # Report shows stock released
    print("\nReport after lazy expiry:")
    print(format_report(engine.report("TSHIRT-WHT")))

    # ------------------------------------------------------------------
    # 6. All-SKU final report
    # ------------------------------------------------------------------
    print(heading("Final All-SKU Report"))
    print(format_report(engine.report()))

    # ------------------------------------------------------------------
    # 7. Edge case: Not enough stock
    # ------------------------------------------------------------------
    print(heading("Edge: Insufficient Stock"))
    try:
        engine.reserve("MUG-CRM", "mallory", 999)
    except InventoryError as exc:
        print(f"  -> Correctly refused: {exc}")

    print("\n[v] Demo complete. Check tests/ for exhaustive edge-case coverage.")


if __name__ == "__main__":
    main()