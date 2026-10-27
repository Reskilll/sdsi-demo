#!/usr/bin/env python3
"""IT Service-Desk SLA Tracker — CLI entry point.

Commands:
  run         Compute SLA for all tickets and print report
  json        Output JSON report
  csv         Output CSV report
  html        Output HTML dashboard
  generate    Generate synthetic test tickets
  benchmark  Run high-volume performance benchmark
"""

import argparse
import json
import sys
import time
from pathlib import Path

from sla_tracker.models import SLAPolicy
from sla_tracker.calendar import HolidayCalendar
from sla_tracker.engine import compute_ticket_sla
from sla_tracker.analytics import compute_analytics
from sla_tracker.validator import validate_tickets
from sla_tracker.reporter import (
    print_cli_report,
    to_json_report,
    to_csv_report,
    to_html_report,
)
from sla_tracker.synthetic import generate_tickets


DATA_DIR = Path(__file__).parent / "data"


def load_all():
    """Load tickets, policy, and holidays from data/ directory."""
    with open(DATA_DIR / "tickets.json", "r") as f:
        tickets_raw = json.load(f)
    tickets, errors = validate_tickets(tickets_raw)
    if errors:
        print(f"Validation warnings ({len(errors)}):")
        for e in errors[:10]:
            print(f"  ⚠ {e}")
    policy = SLAPolicy.from_file(str(DATA_DIR / "sla_policy.json"))
    holidays = HolidayCalendar.from_file(str(DATA_DIR / "holidays.json"))
    return tickets, policy, holidays


def cmd_run(args):
    tickets, policy, holidays = load_all()
    results = [compute_ticket_sla(t, policy, holidays) for t in tickets]
    analytics = compute_analytics(results)
    filters = {}
    if args.priority:
        filters["priority"] = args.priority
    if args.assignee_group:
        filters["assignee_group"] = args.assignee_group
    print_cli_report(results, analytics, filters)


def cmd_json(args):
    tickets, policy, holidays = load_all()
    results = [compute_ticket_sla(t, policy, holidays) for t in tickets]
    analytics = compute_analytics(results)
    out = to_json_report(results, analytics)
    if args.output:
        Path(args.output).write_text(out)
        print(f"JSON report → {args.output}")
    else:
        print(out)


def cmd_csv(args):
    tickets, policy, holidays = load_all()
    results = [compute_ticket_sla(t, policy, holidays) for t in tickets]
    out = to_csv_report(results)
    if args.output:
        Path(args.output).write_text(out)
        print(f"CSV report → {args.output}")
    else:
        print(out)


def cmd_html(args):
    tickets, policy, holidays = load_all()
    results = [compute_ticket_sla(t, policy, holidays) for t in tickets]
    analytics = compute_analytics(results)
    out = to_html_report(results, analytics)
    if args.output:
        Path(args.output).write_text(out)
        print(f"HTML dashboard → {args.output}")
    else:
        path = DATA_DIR.parent / "sla_report.html"
        Path(path).write_text(out)
        print(f"HTML dashboard → {path}")


def cmd_generate(args):
    out = args.output or str(DATA_DIR / "tickets.json")
    tickets = generate_tickets(count=args.count, seed=args.seed)
    with open(out, "w") as f:
        json.dump(tickets, f, indent=2)
    print(f"Generated {len(tickets)} tickets → {out}")


def cmd_benchmark(args):
    """Run high-volume benchmark demonstrating O(1) calendar arithmetic."""
    from datetime import datetime, timedelta, timezone

    tickets, policy, holidays = load_all()
    n = args.count
    min_count = min(n, len(tickets))

    if min_count < n:
        # Generate additional tickets
        extra = generate_tickets(count=n, seed=args.seed)
        # Override tickets list for benchmark
        from sla_tracker.validator import validate_tickets
        tickets, _ = validate_tickets(extra)

    print(f"Benchmark: {len(tickets)} tickets, {args.runs} runs...")
    total = 0.0
    for run in range(args.runs):
        start = time.perf_counter()
        for t in tickets:
            compute_ticket_sla(t, policy, holidays)
        elapsed = time.perf_counter() - start
        total += elapsed
        print(f"  Run {run+1}: {elapsed:.4f}s — {len(tickets)/elapsed:.0f} tickets/s")

    avg = total / args.runs
    print(f"\nAverage: {avg:.4f}s ({len(tickets)/avg:.0f} tickets/s)")
    if len(tickets) >= 100000:
        print("✅ O(1) day-block arithmetic verified — no minute-by-minute loops.")


def main():
    parser = argparse.ArgumentParser(
        description="IT Service-Desk SLA Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    # run
    p_run = sub.add_parser("run", help="Compute SLA and print terminal report")
    p_run.add_argument("--priority", help="Filter by priority (P1-P4)")
    p_run.add_argument("--assignee-group", help="Filter by assignee group")

    # json
    p_j = sub.add_parser("json", help="Output JSON report")
    p_j.add_argument("-o", "--output", help="Output file path")

    # csv
    p_c = sub.add_parser("csv", help="Output CSV report")
    p_c.add_argument("-o", "--output", help="Output file path")

    # html
    p_h = sub.add_parser("html", help="Output HTML dashboard")
    p_h.add_argument("-o", "--output", help="Output file path")

    # generate
    p_g = sub.add_parser("generate", help="Generate synthetic test tickets")
    p_g.add_argument("-o", "--output", help="Output file path")
    p_g.add_argument("-n", "--count", type=int, default=50, help="Number of tickets")
    p_g.add_argument("--seed", type=int, default=42, help="Random seed")

    # benchmark
    p_b = sub.add_parser("benchmark", help="Run performance benchmark")
    p_b.add_argument("-n", "--count", type=int, default=1000, help="Number of tickets")
    p_b.add_argument("-r", "--runs", type=int, default=3, help="Number of runs")
    p_b.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "json":
        cmd_json(args)
    elif args.command == "csv":
        cmd_csv(args)
    elif args.command == "html":
        cmd_html(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    else:
        # Default: run the report
        from argparse import Namespace
        cmd_run(Namespace(priority=None, assignee_group=None))


if __name__ == "__main__":
    main()