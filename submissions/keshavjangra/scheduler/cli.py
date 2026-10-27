"""Command-line interface for the job scheduler.

Usage examples::

    python -m scheduler.cli path/to/graph.json              # full analysis
    python -m scheduler.cli --topo path/to/graph.json       # topo order only
    python -m scheduler.cli --workers 3 path/to/graph.json  # schedule w/ limit
    python -m scheduler.cli --fail A path/to/graph.json     # simulate failure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .graph import DAG, Job
from .topo import topological_sort
from .parallel import parallel_schedule, parallel_stages, estimated_makespan
from .critical import critical_path, min_completion_time, job_schedule_times
from .failure import downstream_impact, failure_report


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Job Scheduler with Dependency Resolution (DAG)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m scheduler.cli samples/sample1.json
  python -m scheduler.cli --workers 4 samples/sample1.json
  python -m scheduler.cli --fail B samples/sample1.json
  echo '[{"id":"A","duration":5,"dependsOn":[]}]' | python -m scheduler.cli --stdin
""",
    )
    p.add_argument(
        "file",
        nargs="?",
        help="Path to a JSON file containing an array of job objects",
    )
    p.add_argument(
        "--stdin",
        action="store_true",
        help="Read JSON from stdin instead of a file",
    )
    p.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        help="Worker limit for parallel scheduling (default: unlimited)",
    )
    p.add_argument(
        "--topo",
        action="store_true",
        help="Print only the topological order",
    )
    p.add_argument(
        "--critical",
        action="store_true",
        dest="crit",
        help="Print only the critical path",
    )
    p.add_argument(
        "--fail",
        metavar="JOB_ID",
        default=None,
        help="Simulate a failure of the given job and list skipped downstream jobs",
    )
    p.add_argument(
        "--json-out",
        action="store_true",
        help="Output results as JSON (useful for piping)",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # ---- Load input ----------------------------------------------------
    try:
        if args.stdin:
            if args.file:
                print("Error: cannot specify both --stdin and a file path", file=sys.stderr)
                return 2
            raw = json.load(sys.stdin)
        elif args.file:
            raw = json.loads(Path(args.file).read_text(encoding="utf-8"))
        else:
            parser.print_help()
            return 0
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw, list):
        print("Error: input must be a JSON array of job objects", file=sys.stderr)
        return 1

    # ---- Build & validate DAG ------------------------------------------
    try:
        dag = DAG.from_dicts(raw)
    except ValueError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1

    # ---- Output as JSON ------------------------------------------------
    if args.json_out:
        result: Dict = {"job_count": len(dag)}
        result["topological_order"] = topological_sort(dag)
        result["parallel_stages"] = [sorted(s) for s in parallel_stages(dag)]
        cp_path, cp_duration = critical_path(dag)
        result["critical_path"] = {"path": cp_path, "duration": cp_duration}
        result["min_completion_time"] = cp_duration
        if args.workers:
            sched = parallel_schedule(dag, args.workers)
            result["schedule"] = {
                "worker_limit": args.workers,
                "slices": sched,
                "makespan": estimated_makespan(dag, args.workers),
            }
        if args.fail:
            skipped = sorted(downstream_impact(dag, args.fail))
            result["failure_simulation"] = {
                "failed_job": args.fail,
                "skipped_jobs": skipped,
                "skipped_count": len(skipped),
            }
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    # ---- Human-readable output -----------------------------------------
    print(f"Jobs: {len(dag)}")
    print(f"Roots: {dag.roots()}")
    print(f"Leaves: {dag.leaves()}")
    print()

    # Topological order
    order = topological_sort(dag)
    if args.topo:
        print(" -> ".join(order))
        return 0

    print("Topological order:")
    print("  " + " -> ".join(order))
    print()

    # Parallel stages (unlimited)
    stages = parallel_stages(dag)
    print("Parallel stages (unlimited workers):")
    for i, stage in enumerate(stages):
        print(f"  Stage {i + 1}: {sorted(stage)}")
    print()

    # Schedule with worker limit (if requested)
    if args.workers:
        print(f"Schedule with worker limit = {args.workers}:")
        sched = parallel_schedule(dag, args.workers)
        for i, slc in enumerate(sched):
            print(f"  Slice {i + 1}: {slc}")
        ms = estimated_makespan(dag, args.workers)
        print(f"  Estimated makespan: {ms}")
        print()

    # Critical path
    cp_path, cp_duration = critical_path(dag)
    if args.crit:
        print(f"Critical path: {' -> '.join(cp_path)}")
        print(f"Duration: {cp_duration}")
        return 0

    print(f"Critical path: {' -> '.join(cp_path)} (duration: {cp_duration})")
    print(f"Minimum completion time: {min_completion_time(dag)}")
    print()

    # Per-job schedule times
    times = job_schedule_times(dag)
    print("Earliest start / finish times:")
    for jid in order:
        s, f = times[jid]
        print(f"  {jid}: start={s}, finish={f}")
    print()

    # Failure simulation
    if args.fail:
        report = failure_report(dag, args.fail)
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())