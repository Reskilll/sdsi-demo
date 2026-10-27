"""DAG Job Scheduler — CLI entry point.

Usage:
  python -m dag_scheduler.main <path-to-spec.json> [--workers N] [--fail JOB]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .graph import (
    critical_path,
    detect_cycle,
    JobNode,
    simulate_failure,
    topological_sort,
)
from .scheduler import group_stages, schedule_parallel
from .validator import load_json_safe, spec_to_jobnodes, validate_and_parse


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level, format="%(levelname)s: %(message)s", stream=sys.stderr
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DAG Job Scheduler — dependency resolution, "
        "parallel scheduling, critical-path analysis, and failure simulation."
    )
    parser.add_argument(
        "spec", type=str, help="Path to JSON job-specification file"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=4,
        help="Maximum parallel workers (default: 4, min: 1)"
    )
    parser.add_argument(
        "--fail", "-f", type=str, default=None,
        help="Simulate failure of the named job and report skipped downstream jobs"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug-level logging"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Write full report to a JSON file"
    )
    return parser.parse_args(argv)


def _jobs_to_spec(jobs: dict[str, JobNode]) -> list[dict]:
    """Convert graph nodes back to a portable dict for JSON export."""
    return [
        {"name": n.name, "duration": n.duration, "dependsOn": n.depends_on}
        for n in jobs.values()
    ]


def main(argv: list[str] | None = None) -> dict:
    """Run the full pipeline and return a result dict (also prints to stdout)."""
    args = parse_args(argv)
    setup_logging(args.verbose)

    spec_path = Path(args.spec)
    raw = load_json_safe(spec_path)
    validated = validate_and_parse(raw, source_path=str(spec_path))

    # Apply CLI worker override if present
    if args.workers < 1:
        print("Error: --workers must be >= 1", file=sys.stderr)
        sys.exit(1)
    validated.worker_limit = args.workers

    jobs = spec_to_jobnodes(validated)

    report: dict = {
        "source": str(spec_path),
        "job_count": len(jobs),
        "worker_limit": validated.worker_limit,
    }

    # ---------- M1: Cycle detection ----------
    cycle = detect_cycle(jobs)
    report["cycle"] = {
        "has_cycle": cycle.has_cycle,
        "cycle_path": cycle.cycle_path,
    }

    if cycle.has_cycle:
        print("\n⚠  CYCLE DETECTED!")
        print(f"   Path: {' → '.join(cycle.cycle_path)}")
        print("   Cannot proceed with scheduling until the cycle is resolved.\n")
        if args.output:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    # ---------- M2: Topological sort ----------
    topo = topological_sort(jobs)
    report["topological_order"] = topo.order
    report["levels"] = topo.levels

    print(f"\n📋 Topological order: {' → '.join(topo.order)}")

    # ---------- M4: Critical path ----------
    cp = critical_path(jobs)
    report["critical_path"] = {
        "path": cp.path,
        "total_time": cp.total_time,
    }
    print(f"🕐 Critical path: {' → '.join(cp.path)} (total: {cp.total_time:.1f})")

    # ---------- M3: Parallel scheduling ----------
    stages_parallel = schedule_parallel(jobs, validated.worker_limit)
    report["schedule"] = {
        "stages": stages_parallel.stages,
        "makespan": stages_parallel.makespan,
        "timeline": [
            {"job": se.job, "start": se.start, "end": se.end, "worker": se.worker}
            for se in stages_parallel.schedule
        ],
    }

    print(f"\n⚙️  Parallel schedule ({validated.worker_limit} workers, "
          f"makespan {stages_parallel.makespan:.1f}):")
    for i, stage in enumerate(stages_parallel.stages):
        print(f"   Stage {i}: {stage}")

    # ---------- M5: Failure simulation ----------
    if args.fail:
        if args.fail not in jobs:
            print(f"\n❌ Error: cannot fail unknown job '{args.fail}'", file=sys.stderr)
            sys.exit(1)
        failure = simulate_failure(jobs, args.fail)
        report["failure_simulation"] = {
            "failed_job": failure.failed_job,
            "directly_skipped": failure.directly_skipped,
            "all_skipped": failure.all_skipped,
            "still_runnable": failure.still_runnable,
        }
        print(f"\n💥 Failure simulation (job '{args.fail}' failed):")
        print(f"   Directly skipped: {failure.directly_skipped or '(none)'}")
        print(f"   All skipped:      {failure.all_skipped or '(none)'}")
        print(f"   Still runnable:   {failure.still_runnable or '(none)'}")

    # ---------- Structured output ----------
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n📄 Full report written to {out_path}")

    print()  # trailing blank line
    return report


if __name__ == "__main__":
    main()