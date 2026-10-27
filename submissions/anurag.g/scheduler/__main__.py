"""CLI entrypoint for the job scheduler.

Usage:
  python -m scheduler validate  examples/sample.json
  python -m scheduler schedule  examples/sample.json --workers 3
  python -m scheduler fail      examples/sample.json --failed B
  python -m scheduler schedule  examples/sample.json --workers 2 --failed C
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scheduler.scheduler import run
from scheduler.models import GraphLoadError
from scheduler.stages import WorkerLimitError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scheduler",
        description="PS5 Job Scheduler — DAG-based build/ETL orchestrator",
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    # validate
    p_val = sub.add_parser("validate", help="Validate the job graph (M1)")
    p_val.add_argument("input", help="JSON file path or inline JSON string")

    # schedule (default)
    p_sched = sub.add_parser("schedule", help="Run full schedule pipeline (M1-M4) [default]")
    p_sched.add_argument("input", help="JSON file path or inline JSON string")
    p_sched.add_argument("--workers", "-w", type=int, default=1, help="Worker limit N (default: 1)")
    p_sched.add_argument("--failed", "-f", type=str, default=None, help="Job id to simulate failure for (M5)")

    # fail
    p_fail = sub.add_parser("fail", help="Simulate failure of a job (M1+M5)")
    p_fail.add_argument("input", help="JSON file path or inline JSON string")
    p_fail.add_argument("--failed", "-f", type=str, required=True, help="Job id to fail")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        if args.command == "validate":
            report = run(args.input)
            print(report.pretty())
            return 0 if report.validation.is_valid else 1

        elif args.command == "schedule":
            report = run(args.input, workers=args.workers, fail=args.failed)
            print(report.pretty())
            return 0 if report.validation.is_valid else 1

        elif args.command == "fail":
            report = run(args.input, fail=args.failed)
            print(report.pretty())
            return 0 if report.validation.is_valid else 1

    except (GraphLoadError, WorkerLimitError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())