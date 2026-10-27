"""Command-line interface for the expense splitter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

# Ensure Unicode box-drawing & ₹ render on all platforms (especially Windows cp1252).
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from .engine import compute_balances, simplify_debts
from .models import Expense, SplitResult, SplitType
from .validator import ValidationError, validate_expense, validate_group_input


def load_expenses(file_path: str) -> dict:
    """Load a JSON expenses file. Supports single group object or list of groups (batch)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def parse_expense(raw: dict) -> Expense:
    """Parse one expense dict into an Expense model."""
    return Expense(
        description=raw["description"],
        total=float(raw["total"]),
        paid_by=raw["paid_by"],
        split_type=SplitType(raw["split_type"].lower()),
        members=list(raw["members"]),
        amounts=[float(a) for a in raw.get("amounts", [])],
    )


def process_group(group_name: str, group_data: dict) -> SplitResult:
    """Process one group from raw JSON data → full SplitResult."""

    members: List[str] = list(group_data["members"])
    raw_expenses: List[dict] = group_data.get("expenses", [])

    # Stage-1 structural validation
    validate_group_input(group_name, members, raw_expenses)

    result = SplitResult(group_name=group_name, members=members, expenses=[], balances={}, settlements=[])

    # Parse and validate each expense
    for i, raw in enumerate(raw_expenses):
        try:
            exp = parse_expense(raw)
        except (KeyError, ValueError) as e:
            result.errors.append(f"Expense #{i + 1}: parse error — {e}")
            continue

        try:
            validate_expense(exp, set(members))
        except ValidationError as e:
            result.errors.append(f"Expense #{i + 1} ('{exp.description}'): {e}")
            continue

        result.expenses.append(exp)

    if result.errors:
        return result  # don't compute balances on partial data

    # Compute
    result.balances = compute_balances(result.expenses, members)
    result.settlements = simplify_debts(result.balances)

    return result


def format_result(result: SplitResult) -> str:
    """Pretty-print a SplitResult for terminal display."""

    lines: List[str] = []
    width = 60
    double = "═" * width
    single = "─" * width

    lines.append(f"\n{double}")
    lines.append(f"  Group: {result.group_name}")
    lines.append(f"  Members: {', '.join(result.members)}")
    lines.append(f"  Expenses processed: {len(result.expenses)}")
    lines.append(double)

    if result.errors:
        lines.append("\n  ❌ VALIDATION ERRORS:")
        for err in result.errors:
            lines.append(f"    • {err}")
        lines.append("")
        return "\n".join(lines)

    # ── Balances ───────────────────────────────────────────────────────
    lines.append(f"\n  📊 NET BALANCES")
    lines.append(f"  {single}")
    lines.append(f"  {'Member':<20} {'Paid':>10} {'Owed':>10} {'Net':>10}")
    lines.append(f"  {single}")
    for member in result.members:
        bal = result.balances[member]
        net = bal.net
        sign = "+" if net >= 0 else ""
        lines.append(
            f"  {member:<20} {bal.paid:>10.2f} {bal.owed:>10.2f} {sign}{net:>9.2f}"
        )
    lines.append(f"  {single}")
    lines.append(f"  {'TOTAL':<20} "
                 f"{sum(b.paid for b in result.balances.values()):>10.2f} "
                 f"{sum(b.owed for b in result.balances.values()):>10.2f}")

    # ── Settlements ────────────────────────────────────────────────────
    if result.settlements:
        lines.append(f"\n  💸 SIMPLIFIED SETTLEMENTS")
        lines.append(f"  {single}")
        for s in result.settlements:
            lines.append(f"  {s.from_member}  ──₹{s.amount:,.2f}──▶  {s.to_member}")
    else:
        lines.append(f"\n  ✅ All settled — no payments needed.")

    lines.append(f"\n{double}\n")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="expense-splitter",
        description="Split group expenses and simplify debts — Splitwise-lite.",
    )
    parser.add_argument(
        "file",
        help="Path to a JSON expenses file (single group or batch of groups).",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of pretty-printed text.",
    )
    args = parser.parse_args(argv)

    try:
        data = load_expenses(args.file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Support both single-object and list-of-groups (batch) input
    if isinstance(data, list):
        groups: Dict[str, dict] = {}
        for entry in data:
            name = entry.get("group", f"Group-{len(groups) + 1}")
            groups[name] = entry
    elif isinstance(data, dict):
        groups = {data.get("group", "default"): data}
    else:
        print("Error: JSON root must be an object or array of objects.", file=sys.stderr)
        sys.exit(1)

    results: List[SplitResult] = []
    for name, gdata in groups.items():
        result = process_group(name, gdata)
        results.append(result)

    if args.json:
        output = []
        for r in results:
            entry = {
                "group": r.group_name,
                "members": r.members,
                "expenses_processed": len(r.expenses),
                "errors": r.errors,
                "balances": {
                    m: {"paid": b.paid, "owed": b.owed, "net": round(b.net, 2)}
                    for m, b in r.balances.items()
                } if r.balances else None,
                "settlements": [
                    {"from": s.from_member, "to": s.to_member, "amount": s.amount}
                    for s in r.settlements
                ],
            }
            output.append(entry)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(format_result(r))

    # Non-zero exit if any group had errors
    if any(r.errors for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()