#!/usr/bin/env python3
"""CLI entry point for the DAG Job Scheduler.

Usage:
    python main.py samples/example.json                  # basic run
    python main.py samples/example.json --workers 4      # with worker cap
    python main.py samples/example.json --fail job_x      # failure sim
    python main.py samples/example.json -w 3 -f init_job  # combined

Run `python main.py --help` for all options.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.orchestrator import PipelineResult, format_pipeline_result, run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="job-scheduler",
        description="DAG-based job scheduler with dependency resolution.",
    )
    p.add_argument(
        "input",
        help="Path to a JSON file containing a list of job objects.",
    )
    p.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        metavar="N",
        help="Maximum concurrent workers for parallel scheduling (default: 1).",
    )
    p.add_argument(
        "-f", "--fail",
        type=str,
        default=None,
        metavar="JOB_ID",
        help="Simulate failure of the named job (M5).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output the full result as JSON instead of human-readable text.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate worker count early.
    if args.workers < 1:
        print(f"Error: --workers must be >= 1, got {args.workers}.", file=sys.stderr)
        return 2

    try:
        pipeline: PipelineResult = run(
            input_source=args.input,
            worker_limit=args.workers,
            fail_job=args.fail,
        )
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json_output:
        _print_json(pipeline)
    else:
        print(format_pipeline_result(pipeline))

    return 0 if pipeline.is_valid else 3


def _print_json(result: PipelineResult) -> None:
    """Serialize the pipeline result as JSON."""
    import json

    def _serialize(obj):
        """Handle dataclass and custom types for JSON serialization."""
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _serialize(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialize(v) for v in obj]
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        return obj

    output = {
        "is_valid": result.is_valid,
        "validation_issues": [
            {"kind": i.kind, "message": i.message}
            for i in result.validation_issues
        ],
        "topological_order": result.topological_order,
        "schedule": _serialize(result.schedule_result),
        "critical_path": _serialize(result.critical_path_result),
        "failure": _serialize(result.failure_result),
        "input_summary": result.input_summary,
    }
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())