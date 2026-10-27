#!/usr/bin/env python3
"""CLI for the PS4 Inventory Reservation System.

Usage:
    python app.py <command> [args]

Commands:
    products                          List all products
    product <sku>                     Show one product
    reserve <sku> <user_id> [qty]     Reserve stock
    confirm <reservation_id>          Confirm (purchase) a reservation
    cancel <reservation_id>           Cancel a reservation
    reservation <reservation_id>      Show a reservation
"""

import sys
import os

# Allow running from the submission directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reservation_system import InventoryReservationSystem


def main():
    inventory_path = os.path.join(os.path.dirname(__file__), "inventory.json")
    system = InventoryReservationSystem(inventory_path)

    if len(sys.argv) < 2:
        _usage("command required")

    cmd = sys.argv[1]

    if cmd == "products":
        for sku, p in system.products().items():
            print(f"{p['sku']:20s} {p['available']:3d} available / {p['total']:3d} total  ({p['name']})")

    elif cmd == "product":
        if len(sys.argv) < 3:
            return _usage("product <sku>")
        p = system.product(sys.argv[2])
        if p is None:
            print(f"SKU not found: {sys.argv[2]}")
            sys.exit(1)
        print(f"SKU:        {p['sku']}")
        print(f"Name:       {p['name']}")
        print(f"Total:      {p['total']}")
        print(f"Reserved:   {p['reserved']}")
        print(f"Sold:       {p['sold']}")
        print(f"Available:  {p['available']}")

    elif cmd == "reserve":
        if len(sys.argv) < 4:
            return _usage("reserve <sku> <user_id> [quantity]")
        sku = sys.argv[2]
        user_id = sys.argv[3]
        qty = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        result = system.reserve(sku, user_id, qty)
        print(json.dumps(result, indent=2))

    elif cmd == "confirm":
        if len(sys.argv) < 3:
            return _usage("confirm <reservation_id>")
        result = system.confirm(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif cmd == "cancel":
        if len(sys.argv) < 3:
            return _usage("cancel <reservation_id>")
        result = system.cancel(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif cmd == "reservation":
        if len(sys.argv) < 3:
            return _usage("reservation <reservation_id>")
        r = system.reservation(sys.argv[2])
        if r is None:
            print("Reservation not found")
            sys.exit(1)
        print(json.dumps(r, indent=2, default=str))

    else:
        _usage(f"unknown command: {cmd}")


def _usage(msg=None):
    if msg:
        print(f"Error: {msg}", file=sys.stderr)
    print(
        __doc__,
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    import json
    main()