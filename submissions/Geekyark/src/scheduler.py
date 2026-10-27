"""Parallel stage scheduler (M3).

Groups jobs into parallel stages respecting a configurable worker limit N.
Implements a greedy "list scheduling" heuristic:

    Whenever a worker frees up, pick the next ready job (all dependencies
    satisfied) whose start time is minimal.  This yields the same makespan
    as critical-path scheduling for DAGs with no resource constraints, but
    also respects the worker cap.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .graph import DAG


@dataclass
class Stage:
    """A group of jobs that execute in parallel within one time-slice."""

    jobs: List[str] = field(default_factory=list)
    start_time: float = 0.0
    duration: float = 0.0  # max duration of jobs in this stage


@dataclass
class ScheduleResult:
    """The complete schedule produced by the scheduler."""

    stages: List[Stage] = field(default_factory=list)
    job_start_times: Dict[str, float] = field(default_factory=dict)
    job_finish_times: Dict[str, float] = field(default_factory=dict)
    total_time: float = 0.0
    total_jobs: int = 0
    worker_limit: int = 1


def schedule(dag: DAG, worker_limit: int = 1) -> ScheduleResult:
    """Schedule all jobs with at most *worker_limit* concurrent workers.

    This is a deterministic list-scheduling algorithm:

    1. Start with all source nodes (in-degree == 0).
    2. At each step, grab up to *worker_limit* ready jobs.
    3. Advance time by the shortest-running job in the current batch.
    4. Complete those jobs, unlock their successors, repeat.

    Args:
        dag: The validated DAG to schedule.
        worker_limit: Maximum number of jobs that may run concurrently.
                       Must be >= 1.

    Returns:
        ScheduleResult with stages, per-job times, and the total makespan.
    """
    if worker_limit < 1:
        raise ValueError("worker_limit must be >= 1")

    if dag.job_count == 0:
        return ScheduleResult(stages=[], total_jobs=0, worker_limit=worker_limit)

    # Remaining duration for each job (mutated as time advances).
    remaining = {jid: dag.jobs[jid].duration for jid in dag.jobs}

    # Completion callbacks: when job X finishes, decrement in-degree of
    # each of its successors; those that hit 0 become ready.
    in_degree = {jid: dag.in_degree(jid) for jid in dag.jobs}
    ready: deque[str] = deque(dag.source_nodes())

    start_times: Dict[str, float] = {}
    finish_times: Dict[str, float] = {}
    stages: List[Stage] = []
    completed: Set[str] = set()
    clock: float = 0.0

    while len(completed) < dag.job_count:
        # Pick up to worker_limit ready jobs.
        stage_jobs: List[str] = []
        while ready and len(stage_jobs) < worker_limit:
            jid = ready.popleft()
            stage_jobs.append(jid)

        if not stage_jobs:
            # Should not happen for a valid DAG, but guards against
            # disconnected components or all-ready-empty corner cases.
            raise RuntimeError(
                "Scheduling stalled — no ready jobs but some remain uncompleted. "
                "This may indicate a cycle or internal error."
            )

        # Start the stage at current clock.
        stage_duration = min(remaining[jid] for jid in stage_jobs)
        stage = Stage(
            jobs=list(stage_jobs),
            start_time=clock,
            duration=stage_duration,
        )
        stages.append(stage)

        for jid in stage_jobs:
            if jid not in start_times:
                start_times[jid] = clock

        # Advance time.
        clock += stage_duration

        # Complete jobs whose remaining time drops to zero.
        for jid in stage_jobs:
            remaining[jid] -= stage_duration
            if remaining[jid] <= 0:
                # Job finished — mark it complete.
                completed.add(jid)
                finish_times[jid] = clock
                # Unlock successors.
                for succ in dag.successors(jid):
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        ready.append(succ)
            else:
                # Job still has work — put it back in the ready queue.
                # This handles the case where stage_duration < job duration
                # due to a shorter sibling job in the same batch.
                ready.append(jid)

    return ScheduleResult(
        stages=stages,
        job_start_times=start_times,
        job_finish_times=finish_times,
        total_time=clock,
        total_jobs=dag.job_count,
        worker_limit=worker_limit,
    )