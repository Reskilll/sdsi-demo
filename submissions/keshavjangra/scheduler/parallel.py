"""M3 – Parallel-stage grouping with a configurable worker limit.

Each "stage" is a set of jobs that are independent of each other
and can execute concurrently.  Stages are serialized: all jobs in stage N
must finish before stage N+1 begins.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Set

from .graph import DAG, Job


def parallel_stages(dag: DAG) -> List[Set[str]]:
    """Group jobs into parallel stages (unlimited workers).

    Each stage contains jobs whose remaining dependencies (from prior
    stages) have all completed.  This yields the *minimum* number of
    stages for the given dependency constraints.
    """
    in_degree: Dict[str, int] = {jid: dag.in_degree(jid) for jid in dag.jobs}
    ready: Set[str] = set(dag.roots())
    completed: Set[str] = set()
    stages: List[Set[str]] = []

    while ready:
        stage = set(ready)
        stages.append(stage)
        completed |= stage

        # Free the next set of ready jobs
        next_ready: Set[str] = set()
        for job_id in stage:
            for child in dag.downstream_of(job_id):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_ready.add(child)
        ready = next_ready

    return stages


def parallel_schedule(
    dag: DAG, worker_limit: int
) -> List[List[str]]:
    """Produce a schedule respecting *worker_limit*.

    Returns a list of time-slices.  Each slice has at most *worker_limit*
    jobs.  Within each parallel stage, jobs are dispatched in sorted order
    to maintain determinism.

    When *worker_limit* < |ready_jobs| the stage is split into multiple
    slices so the limit is never exceeded.
    """
    if worker_limit < 1:
        raise ValueError(f"worker_limit must be >= 1, got {worker_limit}")

    stages = parallel_stages(dag)
    schedule: List[List[str]] = []

    for stage in stages:
        sorted_ids = sorted(stage)
        # Slice the stage into groups of at most worker_limit
        for i in range(0, len(sorted_ids), worker_limit):
            schedule.append(sorted_ids[i : i + worker_limit])

    return schedule


def estimated_makespan(
    dag: DAG, worker_limit: int | None = None
) -> float:
    """Compute the estimated makespan (total wall-clock time).

    - If *worker_limit* is None, assumes unlimited workers — one stage per
      set of mutually independent jobs; makespan = sum of max durations in
      each stage.
    - If a limit is given, takes the schedule from ``parallel_schedule``
      and sums the max duration of each slice.
    """
    if worker_limit is None:
        stages = parallel_stages(dag)
        return sum(max(dag.jobs[j].duration for j in s) for s in stages if s)

    slices = parallel_schedule(dag, worker_limit)
    return sum(max(dag.jobs[j].duration for j in slc) for slc in slices if slc)