"""M5: Failure simulation — given a failed job, list all downstream skipped jobs.

Uses BFS over the outgoing (dependents) edges.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import List, Set

from scheduler.models import JobGraph


@dataclass
class FailureResult:
    """Result of simulating a job failure."""

    failed_job: str
    skipped_jobs: List[str] = field(default_factory=list)
    unaffected_jobs: List[str] = field(default_factory=list)


def simulate_failure(graph: JobGraph, failed_job_id: str) -> FailureResult:
    """Simulate failure of a job and list all downstream skipped jobs.

    Args:
        graph: The job DAG.
        failed_job_id: The id of the job that failed.

    Returns:
        FailureResult listing skipped (downstream) and unaffected jobs.

    Raises:
        ValueError: If failed_job_id is not a known job id.
    """
    if failed_job_id not in graph:
        raise ValueError(f"Unknown job id: '{failed_job_id}'")

    # BFS from failed job through outgoing edges (dependents)
    visited: Set[str] = {failed_job_id}
    queue: deque[str] = deque([failed_job_id])

    while queue:
        jid = queue.popleft()
        for dep in graph.dependents_of(jid):
            if dep not in visited:
                visited.add(dep)
                queue.append(dep)

    # Everything in visited except the failed job itself is skipped
    skipped = sorted(visited - {failed_job_id})
    unaffected = sorted(graph.id_set - visited)

    return FailureResult(
        failed_job=failed_job_id,
        skipped_jobs=skipped,
        unaffected_jobs=unaffected,
    )