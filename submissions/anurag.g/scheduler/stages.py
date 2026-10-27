"""M3: Parallel stage computation with configurable worker limit.

Each job gets a 'level' = longest-path distance from sources (0 for sources).
Jobs at the same level are independent.
Within each level, jobs are batched into waves of at most N workers.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List

from scheduler.models import JobGraph


class WorkerLimitError(ValueError):
    """Raised when the worker count N is invalid."""
    pass


def compute_stages(graph: JobGraph, workers: int = 1) -> List[List[List[str]]]:
    """Compute parallel execution stages respecting a worker limit.

    Args:
        graph: Validated DAG.
        workers: Maximum concurrent workers (N >= 1).

    Returns:
        List of stages. Each stage is a list of waves; each wave is a
        list of up to N job ids that can run concurrently.

    Raises:
        WorkerLimitError: If workers < 1.
    """
    if workers < 1:
        raise WorkerLimitError(f"Worker limit must be >= 1, got {workers}")

    if not graph.jobs:
        return []

    # Compute level (longest-path distance from sources)
    levels: Dict[str, int] = {}
    for jid in graph.id_set:
        if not graph.depends_of(jid):
            levels[jid] = 0

    # Sort topologically to process in order
    from scheduler.topo import topological_sort
    topo_order = topological_sort(graph)

    for jid in topo_order:
        if graph.depends_of(jid):
            levels[jid] = max(levels.get(d, 0) for d in graph.depends_of(jid)) + 1

    # Group by level
    max_level = max(levels.values()) if levels else -1
    level_groups: Dict[int, List[str]] = {lvl: [] for lvl in range(max_level + 1)}
    for jid in topo_order:
        level_groups[levels[jid]].append(jid)

    # Within each level, batch into waves of size workers
    stages: List[List[List[str]]] = []
    for lvl in range(max_level + 1):
        jobs_at_level = level_groups[lvl]
        waves: List[List[str]] = []
        for i in range(0, len(jobs_at_level), workers):
            waves.append(jobs_at_level[i : i + workers])
        stages.append(waves)

    return stages