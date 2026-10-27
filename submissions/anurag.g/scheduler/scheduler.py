"""Orchestrator: ties M1–M5 together into a single run() pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from scheduler.models import JobGraph, load_graph
from scheduler.validation import ValidationResult, validate
from scheduler.topo import topological_sort
from scheduler.stages import compute_stages
from scheduler.critical_path import CriticalPathResult, compute_critical_path
from scheduler.failure import FailureResult, simulate_failure


@dataclass
class Report:
    """Complete analysis report from a scheduler run."""

    graph: JobGraph
    validation: ValidationResult

    # M2
    topo_order: List[str] = field(default_factory=list)

    # M3
    stages: List[List[List[str]]] = field(default_factory=list)
    workers: int = 1

    # M4
    critical: Optional[CriticalPathResult] = None

    # M5
    failure: Optional[FailureResult] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "num_jobs": len(self.graph.jobs),
            "valid": self.validation.is_valid,
        }
        if self.validation.errors:
            d["errors"] = self.validation.errors
        if self.validation.cycles:
            d["cycles"] = [" -> ".join(c) for c in self.validation.cycles]
        if self.validation.missing_deps:
            d["missing_dependencies"] = self.validation.missing_deps

        if self.topo_order:
            d["topological_order"] = self.topo_order

        if self.stages:
            wave_count = sum(len(w) for w in self.stages)
            d["stages"] = {
                "total_stages": len(self.stages),
                "total_waves": wave_count,
                "workers_per_wave": self.workers,
                "schedule": self.stages,
            }

        if self.critical is not None:
            d["critical_path"] = {
                "path": self.critical.critical_path,
                "duration": self.critical.critical_path_duration,
            }
            d["min_completion_time"] = self.critical.min_completion_time

        if self.failure is not None:
            d["failure"] = {
                "failed_job": self.failure.failed_job,
                "skipped_jobs": self.failure.skipped_jobs,
                "unaffected_jobs": self.failure.unaffected_jobs,
            }

        return d

    def pretty(self) -> str:
        """Return a human-readable multi-line summary."""
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("  JOB SCHEDULER REPORT")
        lines.append("=" * 60)
        lines.append(f"  Total jobs: {len(self.graph.jobs)}")
        lines.append("")

        if not self.validation.is_valid:
            lines.append("  ❌ VALIDATION FAILED")
            for e in self.validation.errors:
                lines.append(f"     • {e}")
            lines.append("=" * 60)
            return "\n".join(lines)

        lines.append("  ✅ Graph is valid (no cycles, no missing dependencies)")
        lines.append("")

        # M2
        if self.topo_order:
            lines.append("  --- Topological Order ---")
            lines.append(f"  {' < '.join(self.topo_order)}")
            lines.append("")

        # M3
        if self.stages:
            lines.append(f"  --- Parallel Stages (workers={self.workers}) ---")
            total_waves = 0
            for s_idx, stage in enumerate(self.stages):
                for w_idx, wave in enumerate(stage):
                    total_waves += 1
                    lines.append(f"  Stage {s_idx + 1}, Wave {w_idx + 1}: [{', '.join(wave)}]")
            lines.append(f"  Total: {len(self.stages)} stage(s), {total_waves} wave(s)")
            lines.append("")

        # M4
        if self.critical is not None:
            lines.append("  --- Critical Path ---")
            lines.append(f"  Path: {' -> '.join(self.critical.critical_path)}")
            lines.append(f"  Critical path duration: {self.critical.critical_path_duration}")
            lines.append(f"  Min completion time (unlimited workers): {self.critical.min_completion_time}")
            lines.append("")

        # M5
        if self.failure is not None:
            lines.append("  --- Failure Simulation ---")
            lines.append(f"  Failed job: {self.failure.failed_job}")
            if self.failure.skipped_jobs:
                lines.append(f"  Skipped (downstream): {', '.join(self.failure.skipped_jobs)}")
            else:
                lines.append("  Skipped (downstream): (none)")
            if self.failure.unaffected_jobs:
                lines.append(f"  Unaffected: {', '.join(self.failure.unaffected_jobs)}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


def run(
    data: Any,
    workers: int = 1,
    fail: Optional[str] = None,
) -> Report:
    """Execute the full M1–M5 pipeline on a job graph.

    Args:
        data: JSON file path, JSON string, or dict.
        workers: Worker limit N for parallel stages (default 1).
        fail: Optional job id to simulate failure for.

    Returns:
        Complete Report.
    """
    graph = load_graph(data)
    report = Report(
        graph=graph,
        validation=validate(graph),
        workers=workers,
    )

    if not report.validation.is_valid:
        return report

    # M2
    try:
        report.topo_order = topological_sort(graph)
    except ValueError as e:
        report.validation.is_valid = False
        report.validation.errors.append(str(e))
        return report

    # M3
    if workers < 1:
        report.validation.is_valid = False
        report.validation.errors.append(f"Worker limit must be >= 1, got {workers}")
        return report
    report.stages = compute_stages(graph, workers)

    # M4
    report.critical = compute_critical_path(graph)

    # M5
    if fail is not None:
        report.failure = simulate_failure(graph, fail)

    return report