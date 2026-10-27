"""Command-line interface for the Expense Splitter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .processor import process


def main(argv: list[str] | None = None) -> int:
    """Entry-point; returns exit code."""
    parser = argparse.ArgumentParser(
        description="Split group expenses and settle debts optimally.",
    )
    parser.add_argument(
        "file",
        nargs="+",
        type=Path,
        help="One or more expenses JSON files to process.",
    )
    parser.add_argument(
        "--json-out",
        action="store_true",
        help="Output machine-readable JSON.",
    )

    args = parser.parse_args(argv)

    all_expenses = []

    for path in args.file:
        try:
            data = _load_json(path)
        except FileNotFoundError:
            print(f"Error: file not found — {path}", file=sys.stderr)
            return 1
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON in {path}: {exc}", file=sys.stderr)
            return 2
        except PermissionError:
            print(f"Error: cannot read {path} (permission denied)", file=sys.stderr)
            return 3

        if isinstance(data, dict):
            # Single expense object.
            all_expenses.append(data)
        elif isinstance(data, list):
            all_expenses.extend(data)
        else:
            print(
                f"Error: {path} must contain a JSON object or array of objects",
                file=sys.stderr,
            )
            return 4

    result = process(all_expenses)

    if args.json_out:
        print(json.dumps(_to_dict(result), indent=2, ensure_ascii=False))
    else:
        _pretty_print(result)

    if result.errors:
        return 5
    return 0


def _load_json(path: Path) -> object:
    """Read and parse a JSON file, stripping BOM if present."""
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text)


def _to_dict(result) -> dict:
    return {
        "balances": result.balances,
        "settlements": [
            {"from": s.from_member, "to": s.to_member, "amount": s.amount}
            for s in result.settlements
        ],
        "expenses_processed": result.expenses_processed,
        "errors": result.errors,
    }


def _pretty_print(result) -> None:
    print()
    print("═" * 50)
    print("  💰  EXPENSE SPLITTER  —  Settlement Report")
    print("═" * 50)
    print(f"  Expenses processed: {result.expenses_processed}")

    if result.errors:
        print(f"\n  ⚠  Warnings / skipped ({len(result.errors)}):")
        for e in result.errors:
            print(f"     • {e}")

    print(f"\n  ──  Net Balances  {'─' * 32}")
    print(f"  {'Member':<20} {'Balance (₹)':>12}")
    print(f"  {'─' * 20} {'─' * 12}")
    for member, bal in sorted(result.balances.items()):
        sign = "+" if bal > 0 else ""
        print(f"  {member:<20} {sign}{bal:>11,.2f}")
    print(f"  {'─' * 20} {'─' * 12}")

    # Sanity: total should be ~0
    total = sum(result.balances.values())
    print(f"  {'Sum (≈₹0)':<20} {total:>12.2f}")

    if not result.settlements:
        print("\n  ✅  All settled — no payments needed!")
    else:
        print(f"\n  ──  Simplified Settlements  {'─' * 25}")
        print(f"  {'#':<3} {'From':<14} {'→ To':<16} {'Amount (₹)':>10}")
        print(f"  {'─' * 3} {'─' * 14} {'─' * 16} {'─' * 10}")
        for i, s in enumerate(result.settlements, 1):
            print(
                f"  {i:<3}"
                f" {s.from_member:<14}"
                f" → {s.to_member:<15}"
                f" ₹{s.amount:>9,.2f}"
            )
        print(f"  {'─' * 3} {'─' * 14} {'─' * 16} {'─' * 10}")
        print(f"  Total transactions: {len(result.settlements)}")

    print()