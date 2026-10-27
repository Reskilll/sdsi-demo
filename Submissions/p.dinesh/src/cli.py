#!/usr/bin/env python3
"""Job Scheduler CLI — process a job DAG and print the execution plan.

Usage:
    dag-scheduler <jobs.json> [--workers N] [--fail JOB] [--json]

Examples:
    dag-scheduler samples/basic.json
    dag-scheduler samples/complex.json --workers 3
    dag-scheduler samples/basic.json --fail B
    dag-scheduler samples/cycle.json            # prints validation errors
"""

import argparse
import sys
from pathlib import Path

# Allow running as a module or as a script from the repo root
try:
    from src.models import load_jobs
    from src.engine import build_plan, to_dot
except ModuleNotFoundError:
    # When installed via setup.py, everything is flat under src/
    from models import load_jobs   # type: ignore[no-redef]
    from engine import build_plan, to_dot  # type: ignore[no-redef]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dag-scheduler",
        description="Analyse a job DAG and produce an execution plan.",
    )
    parser.add_argument(
        "jobs_file",
        type=str,
        help="Path to a JSON file containing job definitions.",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        metavar="N",
        help="Maximum concurrent workers per stage (default: 4).",
    )
    parser.add_argument(
        "--fail",
        type=str,
        default=None,
        metavar="JOB",
        help="Simulate failure of a single job; report downstream jobs skipped.",
    )
    parser.add_argument(
        "--fails",
        type=str,
        default=None,
        metavar="JOB[,JOB...]",
        help="Simulate failure of multiple jobs (comma-separated).",
    )
    parser.add_argument(
        "--only",
        type=str,
        choices=["validate", "topo", "stages", "critical", "schedule", "slack", "fail"],
        default=None,
        metavar="MODE",
        help="Print a single section: validate, topo, stages, critical, "
             "schedule, slack, or fail.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output the full plan as JSON instead of a text report.",
    )
    parser.add_argument(
        "--dot",
        action="store_true",
        default=False,
        help="Output Graphviz DOT representation of the DAG (critical path highlighted).",
    )

    args = parser.parse_args(argv)

    # Validate the worker limit
    if args.workers < 1:
        print("Error: --workers must be >= 1", file=sys.stderr)
        return 2

    # Load jobs
    src = Path(args.jobs_file).resolve()
    if not src.exists():
        print(f"Error: file not found — {args.jobs_file}", file=sys.stderr)
        return 1

    jobs = load_jobs(src)

    plan = build_plan(
        jobs,
        worker_limit=args.workers,
        failed_job=args.fail,
        failed_jobs=[f for f in args.fails.split(",") if f.strip()] if args.fails else None,
    )

    # --only mode: print just one section
    if args.only:
        if args.only == "validate":
            if plan.valid:
                print("✅ Valid DAG")
            else:
                for e in plan.validation.errors:
                    print(e)
            return 1 if not plan.valid else 0

        # All other modes require a valid graph
        if not plan.valid:
            print(f"Error: --only {args.only} requires a valid DAG", file=sys.stderr)
            return 1

        if args.only == "topo":
            print(" → ".join(plan.topological_order or []))
            return 0
        if args.only == "stages":
            for i, s in enumerate(plan.stages or [], 1):
                print(f"Stage {i} t={s.start_time}→{s.end_time} ({s.duration}s): {', '.join(s.jobs)}")
            return 0
        if args.only == "critical":
            print(f"Path: {' → '.join(plan.critical_path or [])}")
            print(f"Time:  {plan.critical_path_time}s")
            return 0
        if args.only == "schedule":
            for s in plan.schedule.jobs if plan.schedule else []:
                print(f"t={s.start:3d}→{s.finish:3d} worker {s.worker}  {s.id}")
            if plan.schedule:
                print(f"Makespan: {plan.schedule.makespan}s")
            return 0
        if args.only == "slack":
            for s in plan.slack or []:
                print(f"{s.id:<16} ES {s.earliest_start:3d} LS {s.latest_start:3d} "
                      f"slack {s.total_slack}s" + ("  [CRITICAL]" if s.is_critical else ""))
            return 0
        if args.only == "fail":
            if not plan.failed_jobs:
                print("Error: --only fail requires --fail/--fails <JOB>", file=sys.stderr)
                return 1
            skipped = plan.skipped_jobs or []
            print(f"Failed: {', '.join(plan.failed_jobs)}")
            print(f"Skipped ({len(skipped)}): {', '.join(skipped)}")
            return 0

    if args.dot:
        if not plan.valid:
            print("Error: --dot requires a valid DAG", file=sys.stderr)
            return 1
        print(to_dot(
            jobs,
            critical_path_nodes=plan.critical_path,
            failed_node=plan.failed_job,
            skipped_nodes=plan.skipped_jobs,
        ))
        return 0

    if args.json:
        print(plan.to_json())
    else:
        plan.print()

    return 0 if plan.valid else 1


if __name__ == "__main__":
    sys.exit(main())