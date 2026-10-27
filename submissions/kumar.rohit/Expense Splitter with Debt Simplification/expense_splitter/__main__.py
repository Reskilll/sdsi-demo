"""
CLI entry point for the expense splitter.

Usage:
    python -m expense_splitter --input expenses.json
    python -m expense_splitter --input expenses.json --json
    python -m expense_splitter --input expenses.json --output result.json
    python -m expense_splitter --input expenses.json --balances-only
    python -m expense_splitter --input expenses.json --settlements-only
    python -m expense_splitter --input expenses.json --exact
    python -m expense_splitter --serve        # Start web UI server
    python -m expense_splitter --serve --port 9000
"""

from __future__ import annotations

import argparse
import sys

from .engine import process_group
from .exceptions import ExpenseSplitterError, ValidationError
from .io import format_human_readable, format_json_output, read_expenses, write_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expense-splitter",
        description="Split shared expenses and simplify debts among a group.",
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Path to JSON input file with group members and expenses.",
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to write output (JSON or text). If omitted, output goes to stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of human-readable text.",
    )
    parser.add_argument(
        "--balances-only",
        action="store_true",
        help="Output only balances (no settlements).",
    )
    parser.add_argument(
        "--settlements-only",
        action="store_true",
        help="Output only settlements (no balances).",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Use exact minimum-transaction solver for small groups (n ≤ 12).",
    )
    parser.add_argument(
        "--serve", "-s",
        action="store_true",
        help="Start the web UI server instead of processing a file.",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Port for the web server (default: 8080).",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for the web server (default: 0.0.0.0).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # Ensure stdout supports the ₹ symbol on Windows.
    import io as _io
    for _stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(_stream, "reconfigure"):
                _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.serve:
        from .server import run_server
        run_server(host=args.host, port=args.port)
        return 0

    if not args.input:
        print("Error: --input is required (or use --serve for web UI)", file=sys.stderr)
        return 1

    try:
        group = read_expenses(args.input)
    except (ValidationError, OSError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 1

    try:
        result = process_group(group, use_exact=args.exact)
    except ExpenseSplitterError as e:
        print(f"Error processing expenses: {e}", file=sys.stderr)
        return 2

    if args.balances_only and args.settlements_only:
        print("Error: --balances-only and --settlements-only are mutually exclusive", file=sys.stderr)
        return 3

    try:
        if args.balances_only:
            if args.json:
                import json
                output = json.dumps(
                    [
                        {
                            "member_id": b.member_id,
                            "total_paid": str(b.total_paid),
                            "total_share": str(b.total_share),
                            "net_balance": str(b.net_balance),
                        }
                        for b in result.balances
                    ],
                    indent=2,
                    ensure_ascii=False,
                )
            else:
                lines = []
                for b in result.balances:
                    net_str = f"{b.net_balance:+.2f}"
                    lines.append(f"{b.member_id}: paid ₹{b.total_paid:.2f}, share ₹{b.total_share:.2f}, net {net_str}")
                output = "\n".join(lines)
        elif args.settlements_only:
            if args.json:
                import json
                output = json.dumps(
                    [
                        {"from": s.from_member_id, "to": s.to_member_id, "amount": str(s.amount)}
                        for s in result.settlements
                    ],
                    indent=2,
                    ensure_ascii=False,
                )
            else:
                if not result.settlements:
                    output = "All settled!"
                else:
                    output = "\n".join(
                        f"{s.from_member_id} pays {s.to_member_id} ₹{s.amount:.2f}"
                        for s in result.settlements
                    )
        else:
            output = write_output(result, None, json_mode=args.json)

        # Write to file or stdout
        if args.output:
            from pathlib import Path
            out_path = Path(args.output)
            if out_path.exists():
                print(f"Error: output file already exists: {args.output}", file=sys.stderr)
                return 4
            out_path.write_text(output, encoding="utf-8")
        else:
            print(output)

    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())