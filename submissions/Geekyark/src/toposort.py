"""Topological sort (M2).

Kahn's algorithm — greedy, breadth-first, naturally groups by "wave".
"""

from __future__ import annotations

from collections import deque
from typing import List

from .graph import DAG


def topological_sort(dag: DAG) -> List[str]:
    """Return a topological ordering of all jobs.

    Uses Kahn's algorithm (BFS-based).  Raises ValueError if the graph
    contains a cycle — call `validate()` first.

    Complexity: O(V + E).
    """
    in_degree = {jid: dag.in_degree(jid) for jid in dag.jobs}

    queue: deque[str] = deque(dag.source_nodes())
    order: List[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for successor in dag.successors(node):
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)

    if len(order) != dag.job_count:
        raise ValueError(
            "Cannot produce topological sort — the graph contains a cycle. "
            "Run validate() first to identify the cycle."
        )

    return order