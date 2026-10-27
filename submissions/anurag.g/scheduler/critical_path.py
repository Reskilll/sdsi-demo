"""M4: Critical path and minimum total completion time.

Uses longest-path DP over the topological order.
  earliest_finish[j] = duration[j] + max(earliest_finish[dep] for dep in deps[j])
  (0 if j has no dependencies)

Minimum completion time = max(earliest_finish)  [unlimited-worker lower bound]
A critical path is one longest path reconstructed via back-pointers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from scheduler.models import JobGraph


@dataclass
class CriticalPathResult:
    """Critical path analysis result."""

    critical_path: List[str] = field(default_factory=list)
    critical_path_duration: float = 0.0
    min_completion_time: float = 0.0
    earliest_finish: Dict[str, float] = field(default_factory=dict)


def compute_critical_path(graph: JobGraph) -> CriticalPathResult:
    """Compute the critical path and minimum completion time.

    Args:
        graph: A validated, acyclic JobGraph.

    Returns:
        CriticalPathResult with path, its duration, and overall min time.
    """
    if not graph.jobs:
        return CriticalPathResult()

    from scheduler.topo import topological_sort
    topo_order = topological_sort(graph)

    earliest_finish: Dict[str, float] = {}
    best_parent: Dict[str, str] = {}

    for jid in topo_order:
        job = graph.get(jid)
        if not job.depends_on:
            earliest_finish[jid] = job.duration
            best_parent[jid] = ""  # sentinel for start
        else:
            best_time = -1.0
            best_dep = ""
            for dep in job.depends_on:
                t = earliest_finish[dep]
                if t > best_time:
                    best_time = t
                    best_dep = dep
            earliest_finish[jid] = job.duration + best_time
            best_parent[jid] = best_dep

    # Find the job(s) with the latest finish time
    min_completion_time = max(earliest_finish.values()) if earliest_finish else 0.0

    # Find the last job on the longest path
    last_job = max(
        earliest_finish, key=lambda jid: earliest_finish[jid]
    ) if earliest_finish else ""

    # Reconstruct path backward
    path: List[str] = []
    cur = last_job
    while cur:
        path.append(cur)
        cur = best_parent.get(cur, "")
        if cur == "":
            break
    path.reverse()

    return CriticalPathResult(
        critical_path=path,
        critical_path_duration=earliest_finish.get(last_job, 0.0),
        min_completion_time=min_completion_time,
        earliest_finish=earliest_finish,
    )