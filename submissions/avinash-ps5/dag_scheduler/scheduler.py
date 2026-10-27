"""M3 — Parallel-stage scheduling with a configurable worker limit."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Dict, List

from .graph import JobNode, build_adjacency, build_parent_map


@dataclass
class ScheduleEntry:
    """One job's execution window."""

    job: str
    start: float
    end: float
    worker: int  # 0-indexed worker slot


@dataclass
class StageReport:
    """Result of parallel-stage scheduling."""

    stages: List[List[str]]   # jobs grouped into parallel waves (≤ worker_limit)
    makespan: float           # total wall-clock time with N workers
    schedule: List[ScheduleEntry]
    worker_limit: int


def group_stages(jobs: Dict[str, JobNode], worker_limit: int) -> List[List[str]]:
    """Group jobs into parallel stages using longest-path levels, capped by N.

    Each job's *level* is its longest distance (in edges) from any source.
    Jobs at the same level are mutually independent and form a natural stage.
    Any stage larger than the worker limit is split into waves of at most N.
    """
    n_workers = max(1, worker_limit)

    # Longest-path level via topological order (edge length 1)
    topo = _topo_order(jobs)
    level: Dict[str, int] = {name: 0 for name in jobs}
    adj = build_adjacency(jobs)

    for u in topo:
        for v in adj.get(u, []):
            level[v] = max(level[v], level[u] + 1)

    # Bucket by level
    by_level: Dict[int, List[str]] = {}
    for name, lvl in level.items():
        by_level.setdefault(lvl, []).append(name)

    stages: List[List[str]] = []
    for lvl in sorted(by_level):
        wave = sorted(by_level[lvl])  # deterministic
        # Split waves larger than the worker limit
        for i in range(0, len(wave), n_workers):
            stages.append(wave[i : i + n_workers])

    return stages


def schedule_parallel(jobs: Dict[str, JobNode], worker_limit: int) -> StageReport:
    """Greedy list-scheduler simulation honouring the worker limit.

    Dispatches jobs as soon as (a) their dependencies are done and (b) a worker
    is free. This is the classic ASAP list-scheduling heuristic — it produces a
    valid schedule and a near-optimal makespan. Returns the per-worker timeline
    and groups jobs into parallel waves by their start time.
    """
    n_workers = max(1, worker_limit)

    in_deg = build_parent_map(jobs)
    adj = build_adjacency(jobs)
    dur = {name: node.duration for name, node in jobs.items()}

    # Ready pool — sorted by name for deterministic output
    ready = sorted(name for name, deg in in_deg.items() if deg == 0)

    free: List[int] = list(range(n_workers))      # free worker IDs
    heapq.heapify(free)
    busy: List[tuple] = []                        # (finish_time, worker, job)

    time = 0.0
    schedule: List[ScheduleEntry] = []
    done: set = set()

    while len(done) < len(jobs):
        # 1. Dispatch ready jobs onto free workers at the current time.
        while ready and free:
            job = ready.pop(0)
            worker = heapq.heappop(free)
            end = time + dur[job]
            schedule.append(ScheduleEntry(job=job, start=time, end=end, worker=worker))
            heapq.heappush(busy, (end, worker, job))

        if not busy:
            # No running jobs and nothing to dispatch: means a cycle slipped
            # through (defensive — validator catches this earlier).
            raise ValueError("Scheduler stalled: dependency cycle or missing job")

        # 2. Advance to the next job completion.
        time = busy[0][0]

        # 3. Release every worker whose job finishes at this time.
        while busy and busy[0][0] <= time + 1e-9:
            _, worker, finished_job = heapq.heappop(busy)
            done.add(finished_job)
            heapq.heappush(free, worker)
            for child in adj.get(finished_job, []):
                in_deg[child] -= 1
                if in_deg[child] == 0:
                    ready.append(child)
        ready.sort()

    # Group jobs into waves by start time (each wave ≤ worker_limit by
    # construction since we never dispatch more than N at once).
    wave_map: Dict[float, List[str]] = {}
    for entry in schedule:
        wave_map.setdefault(entry.start, []).append(entry.job)
    stages = [sorted(jobs) for _, jobs in sorted(wave_map.items())]

    makespan = max(entry.end for entry in schedule) if schedule else 0.0

    return StageReport(
        stages=stages,
        makespan=makespan,
        schedule=schedule,
        worker_limit=n_workers,
    )


def _topo_order(jobs: Dict[str, JobNode]) -> List[str]:
    """Kahn's algorithm — returns a valid topological order (raises on cycle)."""
    in_deg = build_parent_map(jobs)
    adj = build_adjacency(jobs)
    ready = sorted(name for name, deg in in_deg.items() if deg == 0)
    order: List[str] = []

    while ready:
        u = ready.pop(0)
        order.append(u)
        for v in adj.get(u, []):
            in_deg[v] -= 1
            if in_deg[v] == 0:
                ready.append(v)
        ready.sort()

    if len(order) != len(jobs):
        raise ValueError("Graph contains a cycle")
    return order