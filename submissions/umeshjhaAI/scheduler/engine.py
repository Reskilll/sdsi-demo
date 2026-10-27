"""Scheduling engine: barrier stages (M3), critical path (M4), failure (M5)."""

from __future__ import annotations

import heapq
from typing import Sequence

from .graph import build_adjacency, topological_order
from .model import Job, JobTiming, Schedule, Stage


def build_stages(jobs: Sequence[Job], workers: int) -> tuple[list[Stage], float]:
    """Partition jobs into barrier-based stages under a worker limit.

    Each stage runs at most ``workers`` jobs whose prerequisites have all
    completed in earlier stages. At every step the lexicographically smallest
    ready jobs are chosen first (min-heap), so the schedule is deterministic.
    A stage's duration is the maximum duration of its jobs; the total
    completion time is the sum of stage durations.
    """
    adj, indegree = build_adjacency(jobs)
    durations = {job.id: job.duration for job in jobs}

    heap = [jid for jid, deg in indegree.items() if deg == 0]
    heapq.heapify(heap)

    stages: list[Stage] = []
    while heap:
        # pop up to `workers` ready jobs in lexicographic order
        batch: list[str] = []
        for _ in range(min(workers, len(heap))):
            batch.append(heapq.heappop(heap))

        stage_duration = max(durations[jid] for jid in batch)
        stages.append(Stage(job_ids=tuple(batch), duration=stage_duration))

        # release newly-ready dependents
        for jid in batch:
            for nxt in adj[jid]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    heapq.heappush(heap, nxt)

    total = sum(stage.duration for stage in stages)
    return stages, total


def critical_path_analysis(
    jobs: Sequence[Job], order: Sequence[str]
) -> tuple[dict[str, JobTiming], float, list[str]]:
    """Compute critical-path timing over the DAG (unlimited workers).

    Returns ``(job_times, critical_path_duration, critical_path)``:

    * ``job_times[id]`` holds earliest start/finish, where a job's start is the
      maximum finish among its prerequisites (0 if it has none).
    * ``critical_path_duration`` is the longest weighted path (max finish over
      all jobs; 0 for an empty graph).
    * ``critical_path`` is one representative longest path, tie-broken by
      smallest id at every choice, giving deterministic output.
    """
    deps = {job.id: set(job.depends_on) for job in jobs}
    durations = {job.id: job.duration for job in jobs}

    job_times: dict[str, JobTiming] = {}
    prev: dict[str, str | None] = {}

    for jid in order:
        if deps[jid]:
            best_dep = min(deps[jid])
            best_finish = job_times[best_dep].earliest_finish
            for dep in deps[jid]:
                f = job_times[dep].earliest_finish
                if f > best_finish or (f == best_finish and dep < best_dep):
                    best_finish = f
                    best_dep = dep
            start = best_finish
            prev[jid] = best_dep
        else:
            start = 0.0
            prev[jid] = None
        finish = start + durations[jid]
        job_times[jid] = JobTiming(earliest_start=start, earliest_finish=finish)

    if not job_times:
        return {}, 0.0, []

    # endpoint of the longest path, tie-broken by smallest id
    endpoint = min(job_times, key=lambda jid: (-job_times[jid].earliest_finish, jid))
    critical_duration = job_times[endpoint].earliest_finish

    path: list[str] = []
    node: str | None = endpoint
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()

    return job_times, critical_duration, path


def propagate_failure(jobs: Sequence[Job], failed_id: str) -> list[str]:
    """Return all transitive downstream dependents of ``failed_id``.

    Includes direct and indirect dependents only; excludes the failed job
    itself, its prerequisites, and unrelated jobs. The result is sorted
    lexicographically. Raises ``ValueError`` for an unknown ``failed_id``.
    """
    known = {job.id for job in jobs}
    if failed_id not in known:
        raise ValueError(f"unknown failed job id {failed_id!r}")

    dependents: dict[str, list[str]] = {job.id: [] for job in jobs}
    for job in jobs:
        for dep in job.depends_on:
            dependents[dep].append(job.id)

    # BFS over the dependent graph starting from failed_id's dependents.
    skipped: set[str] = set()
    frontier = list(dependents[failed_id])
    while frontier:
        node = frontier.pop()
        if node in skipped:
            continue
        skipped.add(node)
        frontier.extend(dependents[node])

    return sorted(skipped)


def build_schedule(jobs: Sequence[Job], workers: int) -> Schedule:
    """Assemble the full analysis for a validated job list."""
    order = topological_order(jobs)
    stages, total_time = build_stages(jobs, workers)
    job_times, cp_duration, cp_path = critical_path_analysis(jobs, order)
    return Schedule(
        topo_order=order,
        stages=stages,
        total_time=total_time,
        critical_path=cp_path,
        critical_path_duration=cp_duration,
        job_times=job_times,
    )
