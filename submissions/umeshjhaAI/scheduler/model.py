"""Core data model for the scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Job:
    """A single unit of work.

    ``depends_on`` preserves the original declaration order but with duplicate
    entries removed; scheduling uses it only as a set of prerequisite ids.
    """

    id: str
    duration: float
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Stage:
    """One barrier-based execution stage: all jobs run together and finish
    before the next stage begins."""

    job_ids: tuple[str, ...]
    duration: float


@dataclass(frozen=True)
class JobTiming:
    """Critical-path timing for a single job (unlimited workers)."""

    earliest_start: float
    earliest_finish: float


@dataclass(frozen=True)
class CriticalPathReason:
    """Explanation of why one job lies on the critical path."""

    job_id: str
    duration: float
    earliest_start: float
    earliest_finish: float
    reason: str


@dataclass
class Schedule:
    """Full analysis result for a valid job graph."""

    topo_order: list[str]
    stages: list[Stage]
    total_time: float
    critical_path: list[str]
    critical_path_duration: float
    job_times: dict[str, JobTiming] = field(default_factory=dict)
    skipped: Optional[list[str]] = None
    critical_path_reasons: list[CriticalPathReason] = field(default_factory=list)
