#!/usr/bin/env python3
"""Flash-sale inventory reservation CLI.

Usage:
    python cli.py load <inventory.json>              # Load products
    python cli.py reserve <user> <sku> [<qty>] [--ttl <s>]   # Reserve stock
    python cli.py confirm <reservation-id> [--user <user>]   # Confirm
    python cli.py cancel <reservation-id> [--user <user>]    # Cancel
    python cli.py report [<sku>]                              # Stock report
    python cli.py list [--user <user>]                        # List reservations
    python cli.py summary                                     # Full summary

State is persisted in ``state.json`` next to the CLI file by default.
Override with ``--state <path>``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from reservation import (
    DataLoadError,
    InsufficientStock,
    InventoryError,
    InventorySystem,
    InvalidQuantity,
    ReservationExpired,
    ReservationNotActive,
    ReservationNotFound,
    SkuNotFound,
    Unauthorized,
    UserLimitExceeded,
)

# Default state file lives next to this script
_HERE = Path(__file__).resolve().parent
_DEFAULT_STATE = str(_HERE / "state.json")


def _system(args: argparse.Namespace) -> InventorySystem:
    state = args.state or _DEFAULT_STATE
    return InventorySystem(state_file=state)


def cmd_load(args: argparse.Namespace) -> None:
    inv = InventorySystem(state_file=args.state or _DEFAULT_STATE)
    path = args.path
    if not os.path.exists(path):
        path = str(_HERE / path)
    inv.load_products(path)
    print(f"✓ Loaded products from {path}")
    _print_report(inv)


def cmd_reserve(args: argparse.Namespace) -> None:
    inv = _system(args)
    try:
        ttl = float(args.ttl) if args.ttl is not None else None
        qty = int(args.quantity)
    except ValueError:
        print(f"✗ InvalidQuantity: quantity must be a positive integer, got {args.quantity!r}")
        sys.exit(1)
    try:
        resv = inv.reserve(args.user, args.sku, quantity=qty, ttl=ttl)
        actual_ttl = max(0, int(resv.expires_at - time.time()))
        print(f"✓ Reserved — ID: {resv.id}")
        print(f"  SKU: {resv.sku}  Qty: {resv.quantity}  User: {resv.user_id}")
        print(f"  Expires in {actual_ttl}s (at {time.strftime('%H:%M:%S', time.localtime(resv.expires_at))})")
    except InventoryError as exc:
        print(f"✗ {exc.__class__.__name__}: {exc}")
        sys.exit(1)


def cmd_confirm(args: argparse.Namespace) -> None:
    inv = _system(args)
    try:
        inv.confirm(args.reservation_id, user_id=args.user)
        print(f"✓ Confirmed reservation {args.reservation_id}")
    except InventoryError as exc:
        print(f"✗ {exc.__class__.__name__}: {exc}")
        sys.exit(1)


def cmd_cancel(args: argparse.Namespace) -> None:
    inv = _system(args)
    try:
        inv.cancel(args.reservation_id, user_id=args.user)
        print(f"✓ Cancelled reservation {args.reservation_id}")
    except InventoryError as exc:
        print(f"✗ {exc.__class__.__name__}: {exc}")
        sys.exit(1)


def cmd_report(args: argparse.Namespace) -> None:
    inv = _system(args)
    _print_report(inv, sku=args.sku)


def cmd_list(args: argparse.Namespace) -> None:
    inv = _system(args)
    reservations = inv.list_reservations(user_id=args.user)
    if not reservations:
        print("No reservations found.")
        return
    print(f"{'ID':<28} {'User':<14} {'SKU':<12} {'Qty':>4} {'Status':<12} {'Expires'}")
    print("-" * 90)
    for r in reservations:
        remains = max(0, int(r.expires_at - time.time()))
        exp = f"{remains}s left" if r.status == "active" else "—"
        print(f"{r.id:<28} {r.user_id:<14} {r.sku:<12} {r.quantity:>4} {r.status:<12} {exp}")


def cmd_summary(args: argparse.Namespace) -> None:
    inv = _system(args)
    _print_report(inv)
    print()
    cmd_list(args)


def _print_report(inv: InventorySystem, sku: str | None = None) -> None:
    try:
        reports = inv.report(sku=sku)
    except InventoryError as exc:
        print(f"✗ {exc}")
        sys.exit(1)

    if not reports:
        print("No products loaded.")
        return

    print(f"{'SKU':<16} {'Name':<20} {'Total':>6} {'Available':>10} {'Reserved':>9} {'Sold':>6}")
    print("-" * 70)
    for r in reports:
        print(f"{r.sku:<16} {r.name:<20} {r.total_stock:>6} {r.available:>10} {r.reserved:>9} {r.sold:>6}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Flash-sale inventory reservation CLI",
        prog="python cli.py",
    )
    parser.add_argument("--state", help="Path to state JSON file (default: state.json)")

    sub = parser.add_subparsers(dest="command", required=True)

    # load
    p = sub.add_parser("load", help="Load products from inventory JSON")
    p.add_argument("path", help="Path to inventory.json")
    p.set_defaults(func=cmd_load)

    # reserve
    p = sub.add_parser("reserve", help="Reserve stock")
    p.add_argument("user", help="User ID")
    p.add_argument("sku", help="Product SKU")
    p.add_argument("quantity", nargs="?", default="1", help="Quantity (default: 1)")
    p.add_argument("--ttl", help="Override TTL in seconds (default: from config or 120)")
    p.set_defaults(func=cmd_reserve)

    # confirm
    p = sub.add_parser("confirm", help="Confirm a reservation")
    p.add_argument("reservation_id", help="Reservation ID")
    p.add_argument("--user", help="User ID (verified for ownership)")
    p.set_defaults(func=cmd_confirm)

    # cancel
    p = sub.add_parser("cancel", help="Cancel a reservation")
    p.add_argument("reservation_id", help="Reservation ID")
    p.add_argument("--user", help="User ID (verified for ownership)")
    p.set_defaults(func=cmd_cancel)

    # report
    p = sub.add_parser("report", help="Show stock report")
    p.add_argument("sku", nargs="?", help="Filter to a specific SKU")
    p.set_defaults(func=cmd_report)

    # list
    p = sub.add_parser("list", help="List reservations")
    p.add_argument("--user", help="Filter by user ID")
    p.set_defaults(func=cmd_list)

    # summary
    sub.add_parser("summary", help="Full report + reservations list").set_defaults(func=cmd_summary)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()