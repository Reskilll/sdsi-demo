"""CLI entry point for Expense Splitter."""
import argparse
import json
import sys
from pathlib import Path

from expense_splitter import ExpenseSplitter, ExpenseError
from expense_splitter.core import Expense, SplitType, _to_decimal


def _parse_member(s: str) -> str:
    return s.strip()


def cmd_add(args):
    """Interactively add a single expense (for quick testing)."""
    print("Add Expense (Ctrl+C to finish)")
    title = input("  Title: ").strip()
    total = _to_decimal(input("  Total (₹): "))
    paid_by = input("  Paid by: ").strip()
    print("  Split type: equal / exact / percentage")
    st = input("  Type: ").strip().lower()
    members = input("  Members (comma-sep): ").strip().split(",")
    members = [m.strip() for m in members if m.strip()]

    if st == "equal":
        shares = [{"member": m} for m in members]
    elif st == "exact":
        shares = []
        for m in members:
            amt = input(f"    Amount for {m}: ")
            shares.append({"member": m, "amount": _to_decimal(amt)})
    elif st == "percentage":
        shares = []
        for m in members:
            pct = input(f"    Percentage for {m}: ")
            shares.append({"member": m, "percentage": _to_decimal(pct)})
    else:
        print("Unknown split type")
        sys.exit(1)

    expense = Expense(
        title=title, total=total, paid_by=paid_by,
        split_type=SplitType(st), shares=shares,
    )
    data = {"members": [], "expenses": []}
    if args.input:
        with open(args.input, "r") as f:
            data = json.load(f)
    data["expenses"].append(expense_to_dict(expense))
    # Collect all member names
    all_members = set()
    for m in data.get("members", []):
        all_members.add(m)
    for s in shares:
        all_members.add(s["member"])
    all_members.add(paid_by)
    data["members"] = sorted(all_members)
    data.setdefault("expenses", [])

    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Appended to {args.output}")
    else:
        print(json.dumps(data, indent=2, default=str))


def expense_to_dict(e: Expense) -> dict:
    """Convert an Expense to a JSON-serializable dict."""
    d = {
        "title": e.title,
        "total": float(e.total),
        "paid_by": e.paid_by,
        "split": {"type": e.split_type.value},
    }
    if e.split_type == SplitType.EQUAL:
        d["split"]["members"] = [s["member"] for s in e.shares]
    elif e.split_type == SplitType.EXACT:
        d["split"]["shares"] = [
            {"member": s["member"], "amount": float(s["amount"])}
            for s in e.shares
        ]
    elif e.split_type == SplitType.PERCENTAGE:
        d["split"]["shares"] = [
            {"member": s["member"], "percentage": float(s["percentage"])}
            for s in e.shares
        ]
    return d


def cmd_process(args):
    """Process a JSON file and print report."""
    try:
        splitter = ExpenseSplitter.from_json(args.input)
    except ExpenseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    print(splitter.report())


def main():
    parser = argparse.ArgumentParser(description="Expense Splitter")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Interactively add an expense to a JSON file")
    p_add.add_argument("-i", "--input", default="expenses.json", help="Input JSON file")
    p_add.add_argument("-o", "--output", default="expenses.json", help="Output JSON file")
    p_add.set_defaults(func=cmd_add)

    p_run = sub.add_parser("process", help="Process a JSON expense file and print report")
    p_run.add_argument("input", nargs="?", default="expenses.json", help="JSON file to process")
    p_run.set_defaults(func=cmd_process)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()