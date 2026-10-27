"""Orchestrator — the main entry point that ties all modules together.

Takes a JSON payload and runs the full pipeline:
  M1  → validate
  M2  → topological sort
  M3  → parallel schedule (with worker limit N)
  M4  → critical path
  M5  → failure simulation (optional job-failure input)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .critical_path import CriticalPathResult, compute_critical_path
from .failure import FailureResult, simulate_failure
from .graph import DAG
from .scheduler import ScheduleResult, schedule
from .toposort import topological_sort
from .validator import ValidationIssue, validate


@dataclass
class PipelineResult:
    """Full pipeline output."""

    dag: DAG

    # M1
    is_valid: bool = False
    validation_issues: List[ValidationIssue] = field(default_factory=list)

    # M2
    topological_order: List[str] = field(default_factory=list)

    # M3
    schedule_result: Optional[ScheduleResult] = None

    # M4
    critical_path_result: Optional[CriticalPathResult] = None

    # M5 (only populated when a failure job is given)
    failure_result: Optional[FailureResult] = None

    # Metadata
    worker_limit: int = 1
    input_summary: Dict[str, Any] = field(default_factory=dict)


def run(
    input_source: Union[str, Path, List[dict]],
    worker_limit: int = 1,
    fail_job: Optional[str] = None,
) -> PipelineResult:
    """Run the complete scheduling pipeline.

    Args:
        input_source: Path to a JSON file, JSON string, or already-parsed list of dicts.
        worker_limit: Maximum concurrent workers (M3).  Defaults to 1.
        fail_job:     Optional job id to simulate a failure for (M5).

    Returns:
        PipelineResult with all module outputs.
    """
    # --- parse input ---
    if isinstance(input_source, (str, Path)):
        raw = _load_json(input_source)
    elif isinstance(input_source, list):
        raw = input_source
    else:
        raise TypeError(
            f"input_source must be a Path, JSON string, or list of dicts; "
            f"got {type(input_source).__name__}."
        )

    # --- build DAG ---
    dag = DAG.from_list(raw)
    result = PipelineResult(
        dag=dag,
        worker_limit=worker_limit,
        input_summary={
            "job_count": dag.job_count,
            "edge_count": dag.edge_count,
        },
    )

    # --- M1: validate ---
    issues = validate(dag)
    result.validation_issues = issues
    result.is_valid = len(issues) == 0

    if not result.is_valid:
        # Skip remaining steps for invalid graphs.
        return result

    # --- M2: topological sort ---
    result.topological_order = topological_sort(dag)

    # --- M3: parallel schedule ---
    result.schedule_result = schedule(dag, worker_limit=worker_limit)

    # --- M4: critical path ---
    result.critical_path_result = compute_critical_path(dag)

    # --- M5: failure simulation (optional) ---
    if fail_job is not None:
        result.failure_result = simulate_failure(dag, fail_job)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(source: Union[str, Path]) -> list:
    """Load and parse JSON from a file path or embedded JSON string."""
    path = Path(source)
    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        # Treat as an inline JSON string.
        text = str(source)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            "Top-level JSON must be an array of job objects."
        )

    return data


def format_pipeline_result(result: PipelineResult) -> str:
    """Render a human-readable summary of the pipeline result."""
    lines: List[str] = []

    lines.append("=" * 60)
    lines.append("  JOB SCHEDULER — PIPELINE RESULT")
    lines.append("=" * 60)
    lines.append(
        f"  Jobs: {result.input_summary.get('job_count', 0)}  |  "
        f"Edges: {result.input_summary.get('edge_count', 0)}  |  "
        f"Worker limit: {result.worker_limit}"
    )
    lines.append("")

    # M1
    lines.append("-" * 60)
    lines.append("  M1 — GRAPH VALIDATION")
    lines.append("-" * 60)
    if result.is_valid:
        lines.append("  ✓ No issues found.")
    else:
        for issue in result.validation_issues:
            lines.append(f"  ✗ [{issue.kind}] {issue.message}")
    lines.append("")

    if not result.is_valid:
        return "\n".join(lines)

    # M2
    lines.append("-" * 60)
    lines.append("  M2 — TOPOLOGICAL ORDER")
    lines.append("-" * 60)
    lines.append(f"  {' → '.join(result.topological_order)}")
    lines.append("")

    # M3
    if result.schedule_result:
        sched = result.schedule_result
        lines.append("-" * 60)
        lines.append("  M3 — PARALLEL EXECUTION STAGES")
        lines.append("-" * 60)
        for i, stage in enumerate(sched.stages, start=1):
            lines.append(
                f"  Stage {i:3d}  @ t={stage.start_time:6.1f}  "
                f"dur={stage.duration:6.1f}  jobs: {', '.join(stage.jobs)}"
            )
        lines.append(f"  Total completion time: {sched.total_time:.1f}")
        lines.append("")

    # M4
    if result.critical_path_result:
        cp = result.critical_path_result
        lines.append("-" * 60)
        lines.append("  M4 — CRITICAL PATH")
        lines.append("-" * 60)
        for i, cpath in enumerate(cp.critical_paths, start=1):
            lines.append(f"  Critical path {i}: {' → '.join(cpath)}")
        lines.append(f"  Minimum completion time: {cp.min_completion_time:.1f}")
        lines.append("")
        lines.append("  Per-job slack (zero = on critical path):")
        for jid in result.topological_order:
            s = cp.slack.get(jid, 0)
            marker = " ★" if abs(s) < 1e-9 else ""
            lines.append(f"    {jid:20s}  slack={s:6.1f}{marker}")
        lines.append("")

    # M5
    if result.failure_result:
        fr = result.failure_result
        lines.append("-" * 60)
        lines.append("  M5 — FAILURE SIMULATION")
        lines.append("-" * 60)
        lines.append(f"  Failed job: {fr.failed_job}")
        lines.append(f"  Skipped ({len(fr.skipped_jobs)}): {', '.join(fr.skipped_jobs)}")
        lines.append(f"  Surviving ({len(fr.surviving_jobs)}): {', '.join(fr.surviving_jobs)}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)