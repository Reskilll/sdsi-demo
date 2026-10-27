"""M2 – Topological sort yielding a valid linear execution order."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .graph import DAG


def topological_sort(dag: DAG) -> List[str]:
    """Return a valid topological order of all jobs.

    Uses Kahn's algorithm (BFS-based, stable with respect to sorted input).
    """
    in_degree: Dict[str, int] = {jid: dag.in_degree(jid) for jid in dag.jobs}
    queue: deque[str] = deque(dag.roots())
    order: List[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for child in sorted(dag.downstream_of(node)):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # If we didn't see every job the DAG must've been invalid — should never
    # happen because the DAG constructor already validated acyclicity.
    if len(order) != len(dag):
        remaining = set(dag.jobs) - set(order)
        raise RuntimeError(
            f"Topological sort did not cover all jobs; unvisited: {sorted(remaining)}"
        )
    return order


def topological_sort_dfs(dag: DAG) -> List[str]:
    """Alternative topological sort using post-order DFS (for testing/verification).

    Returns a different — but still valid — ordering than the Kahn variant.
    """
    visited: Set[str] = set()
    order: List[str] = []

    def _dfs(node: str) -> None:
        if node in visited:
            return
        visited.add(node)
        for child in sorted(dag.downstream_of(node)):
            _dfs(child)
        order.append(node)

    for root in dag.roots():
        _dfs(root)
    order.reverse()
    return order