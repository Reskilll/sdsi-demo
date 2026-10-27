"""Data models for the job scheduler."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class JobSpec:
    """A single job definition loaded from JSON."""

    id: str
    duration: int
    dependsOn: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> JobSpec:
        """Construct and validate a JobSpec from a raw dictionary."""
        if not isinstance(d, dict):
            raise TypeError(f"Expected a JSON object, got {type(d).__name__}")
        if "id" not in d:
            raise KeyError("Job entry missing required field 'id'")
        if "duration" not in d:
            raise KeyError(f"Job '{d.get('id', '?')}' missing required field 'duration'")
        if not isinstance(d["id"], str) or not d["id"].strip():
            raise ValueError(f"Job 'id' must be a non-empty string, got {d['id']!r}")
        if not isinstance(d["duration"], (int, float)) or d["duration"] < 0:
            raise ValueError(
                f"Job '{d['id']}': 'duration' must be a non-negative number, "
                f"got {d['duration']!r}"
            )
        deps = d.get("dependsOn", [])
        if not isinstance(deps, list):
            raise TypeError(f"Job '{d['id']}': 'dependsOn' must be an array")
        for dep in deps:
            if not isinstance(dep, str):
                raise TypeError(
                    f"Job '{d['id']}': each dependency must be a string, got {dep!r}"
                )
        # Deduplicate dependencies while preserving order
        cleaned: list[str] = []
        seen: set[str] = set()
        for dep in deps:
            dep = dep.strip()
            if dep and dep not in seen:
                cleaned.append(dep)
                seen.add(dep)

        return JobSpec(
            id=d["id"].strip(),
            duration=int(d["duration"]),
            dependsOn=cleaned,
        )


@dataclass
class Stage:
    """One parallel execution stage."""

    jobs: list[str]
    start_time: int
    end_time: int

    @property
    def duration(self) -> int:
        return self.end_time - self.start_time


@dataclass
class ScheduledJob:
    """A single job's placement in a concrete worker schedule."""

    id: str
    start: int
    finish: int
    worker: int

    @property
    def duration(self) -> int:
        return self.finish - self.start


@dataclass
class Schedule:
    """A concrete parallel schedule produced by list scheduling."""

    jobs: list[ScheduledJob]
    makespan: int
    worker_count: int


@dataclass
class SlackInfo:
    """Float/slack analysis for a single job."""

    id: str
    earliest_start: int
    earliest_finish: int
    latest_start: int
    latest_finish: int
    total_slack: int

    @property
    def is_critical(self) -> bool:
        return self.total_slack == 0


@dataclass
class ValidationResult:
    """Result of DAG validation (canonical definition, imported by engine.py)."""

    valid: bool
    cycle_path: Optional[list[str]] = None
    missing_dependencies: list[tuple[str, str]] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """Full analysis produced by the orchestrator."""

    jobs: list[JobSpec]
    worker_limit: int
    valid: bool
    validation: ValidationResult

    topological_order: Optional[list[str]] = None
    stages: Optional[list[Stage]] = None
    critical_path: Optional[list[str]] = None
    critical_path_time: Optional[int] = None

    failed_job: Optional[str] = None
    failed_jobs: list[str] = field(default_factory=list)
    skipped_jobs: Optional[list[str]] = None

    schedule: Optional[Schedule] = None
    slack: Optional[list[SlackInfo]] = None

    # ------------------------------------------------------------------
    # Formatted output
    # ------------------------------------------------------------------

    def print(self) -> None:
        """Print a human-readable report to stdout."""
        print("=" * 60)
        print("  JOB SCHEDULER — Dependency-Aware DAG Execution Plan")
        print("=" * 60)
        print(f"  Jobs:           {len(self.jobs)}")
        print(f"  Worker limit:   {self.worker_limit}")
        print()

        if not self.valid:
            print("  ❌ INVALID GRAPH")
            print()
            for err in self.validation.errors:
                print(f"  • {err}")
            return

        print("  ✅ Graph is a valid DAG — no cycles, all dependencies satisfied.")
        print()

        # Topological order
        print("─" * 60)
        print("  TOPOLOGICAL ORDER")
        print(f"  {' → '.join(self.topological_order)}" if self.topological_order else "  N/A")
        print()

        # Stages
        print("─" * 60)
        print("  PARALLEL EXECUTION STAGES")
        if self.stages:
            total_timeline = 0
            for i, s in enumerate(self.stages, 1):
                total_timeline = max(total_timeline, s.end_time)
                print(f"  Stage {i:2d}  t={s.start_time:3d}→{s.end_time:3d}  "
                      f"({s.duration:2d}s)  {', '.join(s.jobs)}")
            print(f"  {'':>13}Total timeline: {total_timeline}s")
        print()

        # Critical path
        print("─" * 60)
        print("  CRITICAL PATH")
        if self.critical_path:
            print(f"  Path:            {' → '.join(self.critical_path)}")
            print(f"  Minimum time:    {self.critical_path_time}s")
        print()

        # Concrete schedule (list scheduling)
        print("─" * 60)
        print("  CONCRETE SCHEDULE (list scheduling)")
        if self.schedule:
            for s in self.schedule.jobs:
                print(f"  t={s.start:3d}→{s.finish:3d}  worker {s.worker}  {s.id}")
            print(f"  Makespan:        {self.schedule.makespan}s "
                  f"with {self.schedule.worker_count} worker(s)")
        print()

        # Slack analysis
        print("─" * 60)
        print("  SLACK ANALYSIS (total float)")
        for s in self.slack or []:
            crit = "CRITICAL" if s.is_critical else f"slack {s.total_slack}s"
            print(f"  {s.id:<16} ES {s.earliest_start:3d}  LS {s.latest_start:3d}  {crit}")
        print()

        # Failure simulation
        if self.failed_jobs:
            print("─" * 60)
            print("  FAILURE SIMULATION")
            print(f"  Failed job(s):   {', '.join(self.failed_jobs)}")
            if self.skipped_jobs is not None:
                if self.skipped_jobs:
                    print(f"  Skipped:         {', '.join(self.skipped_jobs)}")
                    print(f"  Count:           {len(self.skipped_jobs)} job(s) affected")
                else:
                    print("  Skipped:         (none — no downstream jobs)")
        print()

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict of the full plan."""
        d: dict = {
            "valid": self.valid,
            "job_count": len(self.jobs),
            "worker_limit": self.worker_limit,
        }
        d["validation"] = {
            "valid": self.validation.valid,
            "errors": self.validation.errors,
            "cycle_path": self.validation.cycle_path,
            "missing_dependencies": [
                {"job": j, "missing": m}
                for j, m in self.validation.missing_dependencies
            ],
            "duplicate_ids": self.validation.duplicate_ids,
        }
        if self.valid:
            d["topological_order"] = self.topological_order
            d["stages"] = [
                {
                    "stage": i + 1,
                    "jobs": s.jobs,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration": s.duration,
                }
                for i, s in enumerate(self.stages or [])
            ]
            d["critical_path"] = {
                "path": self.critical_path,
                "total_time": self.critical_path_time,
            }
            if self.schedule:
                d["schedule"] = {
                    "makespan": self.schedule.makespan,
                    "worker_count": self.schedule.worker_count,
                    "jobs": [
                        {"id": s.id, "start": s.start, "finish": s.finish, "worker": s.worker}
                        for s in self.schedule.jobs
                    ],
                }
            d["slack"] = [
                {
                    "id": s.id,
                    "earliest_start": s.earliest_start,
                    "earliest_finish": s.earliest_finish,
                    "latest_start": s.latest_start,
                    "latest_finish": s.latest_finish,
                    "total_slack": s.total_slack,
                    "critical": s.is_critical,
                }
                for s in (self.slack or [])
            ]
            if self.failed_jobs:
                d["failure_simulation"] = {
                    "failed_jobs": self.failed_jobs,
                    "skipped_jobs": self.skipped_jobs,
                }
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def load_jobs(path: str | Path) -> list[JobSpec]:
    """Load and validate job definitions from a JSON file.

    Handles file-not-found, invalid JSON, and schema issues with clear messages.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"Error: file not found — {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Error: invalid JSON in {path}\n  {e}")

    if not isinstance(raw, list):
        raise SystemExit("Error: top-level JSON must be an array of job objects")

    if len(raw) == 0:
        raise SystemExit("Error: job list is empty")

    jobs: list[JobSpec] = []
    for i, entry in enumerate(raw):
        try:
            jobs.append(JobSpec.from_dict(entry))
        except (TypeError, KeyError, ValueError) as e:
            raise SystemExit(f"Error at job index {i}: {e}")

    return jobs
