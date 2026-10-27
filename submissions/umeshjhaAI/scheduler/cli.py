"""Command-line interface and output formatting for the scheduler."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional, Sequence

from .errors import ValidationError
from .engine import build_schedule, propagate_failure
from .model import Schedule
from .validation import parse_jobs


def _positive_int(value: str) -> int:
    """argparse type: parse an integer and enforce it is >= 1.

    ``int(value)`` rejects booleans, floats, and non-numeric strings already;
    this adds the positive requirement with a clear message.
    """
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer value: {value!r}")
    if n < 1:
        raise argparse.ArgumentTypeError(f"workers must be >= 1, got {n}")
    return n


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Mini job scheduler with DAG dependency resolution. Validates a "
            "JSON job description and reports a topological order, a "
            "worker-limited stage schedule, critical-path analysis, and "
            "optional downstream failure propagation."
        ),
    )
    parser.add_argument("--input", required=True, help="path to a JSON input file")
    parser.add_argument(
        "--workers",
        type=_positive_int,
        default=None,
        help="worker limit (overrides the JSON 'workers' field)",
    )
    parser.add_argument(
        "--failed-job",
        default=None,
        help="simulate the failure of this job id and report skipped jobs",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser


def _load_json(path: str) -> Any:
    """Read and parse a JSON file; returns a parsed object or raises."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError([f"malformed JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})"])


def run(
    raw: Any,
    workers_override: Optional[int],
    failed_job: Optional[str],
) -> tuple[Schedule, int]:
    """Validate input and run all analyses; raises ``ValidationError`` on failure."""
    jobs, workers, errors = parse_jobs(raw, workers_override)
    if errors:
        raise ValidationError(errors)

    schedule = build_schedule(jobs, workers)

    if failed_job is not None:
        try:
            skipped = propagate_failure(jobs, failed_job)
        except ValueError as exc:
            raise ValidationError([str(exc)])
        schedule.skipped = skipped

    return schedule, workers


def format_text(schedule: Schedule, workers: int, failed_job: Optional[str]) -> str:
    lines: list[str] = []
    lines.append(f"Workers: {workers}")

    if schedule.topo_order:
        lines.append("Topological order: " + " -> ".join(schedule.topo_order))
    else:
        lines.append("Topological order: (empty graph)")

    lines.append("")
    lines.append("Execution stages:")
    if not schedule.stages:
        lines.append("  (none)")
    for i, stage in enumerate(schedule.stages, start=1):
        ids = ", ".join(stage.job_ids)
        lines.append(
            f"  Stage {i}: [{ids}]  duration={stage.duration:g}"
        )
    lines.append(f"Total completion time (worker-limited): {schedule.total_time:g}")

    lines.append("")
    if schedule.critical_path:
        lines.append("Critical path: " + " -> ".join(schedule.critical_path))
    else:
        lines.append("Critical path: (empty graph)")
    lines.append(
        f"Critical path duration (unlimited workers): {schedule.critical_path_duration:g}"
    )

    lines.append("")
    lines.append("Per-job timings (earliest start -> earliest finish):")
    for jid in sorted(schedule.job_times):
        t = schedule.job_times[jid]
        lines.append(
            f"  {jid}: {t.earliest_start:g} -> {t.earliest_finish:g}"
        )

    if failed_job is not None:
        lines.append("")
        lines.append(f"Failure simulation for {failed_job!r}:")
        if schedule.skipped:
            lines.append("  Skipped jobs: " + ", ".join(schedule.skipped))
        else:
            lines.append("  Skipped jobs: (none)")

    return "\n".join(lines)


def format_json(schedule: Schedule, workers: int) -> dict[str, Any]:
    return {
        "workers": workers,
        "topological_order": schedule.topo_order,
        "stages": [
            {"jobs": list(stage.job_ids), "duration": stage.duration}
            for stage in schedule.stages
        ],
        "total_completion_time": schedule.total_time,
        "critical_path": schedule.critical_path,
        "critical_path_duration": schedule.critical_path_duration,
        "job_timings": {
            jid: {
                "earliest_start": schedule.job_times[jid].earliest_start,
                "earliest_finish": schedule.job_times[jid].earliest_finish,
            }
            for jid in schedule.job_times
        },
        "skipped_jobs": schedule.skipped,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw = _load_json(args.input)
        schedule, workers = run(raw, args.workers, args.failed_job)
    except ValidationError as exc:
        for message in exc.errors:
            print(f"error: {message}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: cannot read {args.input!r}: {exc.strerror}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(format_json(schedule, workers), indent=2))
    else:
        print(format_text(schedule, workers, args.failed_job))

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
