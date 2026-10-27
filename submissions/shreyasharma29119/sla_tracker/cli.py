"""CLI entry-point — loads data files, runs the SLA computation, prints results."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .reporter import format_summary, format_ticket_report
from .sla_calculator import compute_all_tickets
from .validation import load_holidays, load_policy, load_tickets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="IT Service-Desk SLA Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python run.py
  python run.py --tickets data/tickets.json --policy data/sla_policy.json --holidays data/holidays.json
  python run.py --reference-time "2026-10-22T18:00:00"
        """.strip(),
    )
    default_data = Path(__file__).resolve().parent.parent / "data"

    parser.add_argument(
        "--tickets",
        default=str(default_data / "tickets.json"),
        help="Path to tickets JSON (default: data/tickets.json)",
    )
    parser.add_argument(
        "--policy",
        default=str(default_data / "sla_policy.json"),
        help="Path to SLA policy JSON (default: data/sla_policy.json)",
    )
    parser.add_argument(
        "--holidays",
        default=str(default_data / "holidays.json"),
        help="Path to holidays JSON (default: data/holidays.json)",
    )
    parser.add_argument(
        "--reference-time",
        default=None,
        help="Reference time (ISO format) for unresolved tickets (default: now)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (for programmatic consumption)",
    )

    args = parser.parse_args(argv)

    try:
        tickets = load_tickets(Path(args.tickets))
        policy = load_policy(Path(args.policy))
        holidays = load_holidays(Path(args.holidays))
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    reference_time = None
    if args.reference_time:
        try:
            reference_time = datetime.fromisoformat(args.reference_time)
        except ValueError as exc:
            print(f"ERROR: invalid --reference-time: {exc}", file=sys.stderr)
            return 1

    results = compute_all_tickets(tickets, policy, holidays, reference_time)

    if args.json:
        import json

        output = {
            "tickets": [
                {
                    "ticket_id": r.ticket_id,
                    "priority": r.priority,
                    "assignee_group": r.assignee_group,
                    "elapsed_business_minutes": r.elapsed_business_minutes,
                    "target_minutes": r.target_minutes,
                    "due_by": r.due_by.isoformat(),
                    "breached": r.breached,
                    "breach_minutes": r.breach_minutes,
                }
                for r in results
            ],
        }
        print(json.dumps(output, indent=2))
        return 0

    print(format_ticket_report(results))
    print()
    print(format_summary(results))
    return 0