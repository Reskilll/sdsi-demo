"""
Command-line interface for the Splitwise-Lite expense settler.

Usage:
    python run.py input.json
    python run.py input.json --output result.json
    python run.py input.json --balances-only
    python run.py batch/input_directory/
    python run.py --stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.errors import SplitwiseError
from src.services.json_processor import JSONProcessor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="splitwise-lite",
        description="Team-outing expense settler — compute balances and minimize settlements.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a .json file or a directory of .json files",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read JSON from standard input",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write output to this file instead of stdout",
    )
    parser.add_argument(
        "--balances-only",
        action="store_true",
        help="Only display net balances, not settlements",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact JSON output (no indentation)",
    )

    args = parser.parse_args(argv)

    indent = None if args.compact else 2

    try:
        if args.stdin:
            result = JSONProcessor.process_stdin()
            _emit(result, args, indent)
            return 0

        if args.input is None:
            parser.print_help()
            return 1

        input_path = Path(args.input)

        if input_path.is_dir():
            # Batch mode.
            batch_results = JSONProcessor.process_batch(str(input_path))
            _emit({"batch": batch_results}, args, indent)

            # Exit non-zero if any file had errors.
            errors = [r for r in batch_results if "error" in r]
            return 1 if errors else 0

        elif input_path.suffix == ".json":
            result = JSONProcessor.process_one(str(input_path))
            _emit(result, args, indent)
            return 0

        else:
            print(f"Error: '{args.input}' is not a .json file or directory", file=sys.stderr)
            return 1

    except SplitwiseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _emit(result: dict, args: argparse.Namespace, indent: int | None) -> None:
    """Apply output filters and write the result."""
    if args.balances_only:
        if "net_balances" in result:
            output = json.dumps(result["net_balances"], indent=indent, ensure_ascii=False)
        else:
            output = json.dumps(result, indent=indent, ensure_ascii=False)
    else:
        output = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
            fh.write("\n")
        print(f"Output written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    raise SystemExit(main())