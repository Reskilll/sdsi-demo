#!/usr/bin/env python3
"""
CLI Entry Point — Expense Splitter
===================================
Usage:
    python run.py <input.json>              # Single group file
    python run.py --batch <batch.json>       # Batch groups file
    python run.py --sample                   # Use built-in sample data

Output is printed to stdout as pretty-printed JSON.
"""

import json
import sys
import os

from expense_splitter import process_group, process_batch, ValidationError


def load_json(path: str) -> dict:
    """Load a JSON file, returning its contents."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found — {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path} — {e}", file=sys.stderr)
        sys.exit(1)


def print_result(result: dict) -> None:
    """Pretty-print the result dictionary."""
    print(json.dumps(result, indent=2))


def sample_data() -> dict:
    """Return a built-in sample for quick demo."""
    return {
        "name": "Team Outing",
        "members": ["Alice", "Bob", "Charlie", "Diana"],
        "expenses": [
            {
                "title": "Dinner",
                "total_amount": 6000,
                "paid_by": "Alice",
                "split_type": "equal",
                "members": ["Alice", "Bob", "Charlie", "Diana"],
            },
            {
                "title": "Movie Tickets",
                "total_amount": 1500,
                "paid_by": "Bob",
                "split_type": "exact",
                "shares": {"Alice": 500, "Bob": 500, "Charlie": 500},
                "members": ["Alice", "Bob", "Charlie"],
            },
            {
                "title": "Cab Fare",
                "total_amount": 1200,
                "paid_by": "Charlie",
                "split_type": "percentage",
                "shares": {"Alice": 50, "Charlie": 50},
                "members": ["Alice", "Charlie"],
            },
        ],
    }


def main() -> None:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__.strip())
        return

    if "--sample" in args:
        data = sample_data()
        try:
            result = process_group(
                group_name=data["name"],
                members=data["members"],
                expenses_data=data["expenses"],
            )
            print_result(result)
        except ValidationError as e:
            print(f"Validation error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if "--batch" in args:
        idx = args.index("--batch") + 1
        if idx >= len(args):
            print("Error: --batch requires a file path", file=sys.stderr)
            sys.exit(1)
        batch_data = load_json(args[idx])
        try:
            result = process_batch(batch_data)
            print_result(result)
        except ValidationError as e:
            print(f"Validation error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Default: single file
    data = load_json(args[0])
    try:
        # Detect batch format: has "groups" key
        if "groups" in data:
            result = process_batch(data)
        else:
            result = process_group(
                group_name=data.get("name", data.get("group", "Group")),
                members=data["members"],
                expenses_data=data["expenses"],
            )
        print_result(result)
    except ValidationError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()