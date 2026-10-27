"""M2: Topological sort using Kahn's algorithm.

Returns a deterministic, lexicographic topo order using a min-heap
for the ready-set.  Raises ValueError if a cycle is present.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Dict, List, Set

from scheduler.models import JobGraph


def topological_sort(graph: JobGraph) -> List[str]:
    """Return a topological order of job ids using Kahn's algorithm.

    Uses a min-heap for the ready set, so output is deterministic
    (lexicographically smallest among valid orders).

    Raises:
        ValueError: If the graph contains a cycle.
    """
    if not graph.jobs:
        return []

    in_degree: Dict[str, int] = {}
    for jid in graph.id_set:
        in_degree[jid] = len(graph.depends_of(jid))

    # Min-heap for deterministic lexicographic order
    ready: List[str] = [jid for jid, deg in in_degree.items() if deg == 0]
    heapq.heapify(ready)

    order: List[str] = []

    while ready:
        jid = heapq.heappop(ready)
        order.append(jid)
        for dep in graph.dependents_of(jid):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                heapq.heappush(ready, dep)

    if len(order) != len(graph.id_set):
        remaining = graph.id_set - set(order)
        raise ValueError(
            f"Cycle detected: {len(remaining)} job(s) unreachable. "
            f"Run validation first for details."
        )

    return order