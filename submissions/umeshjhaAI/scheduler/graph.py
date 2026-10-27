"""Graph construction and deterministic topological sorting (M2)."""

from __future__ import annotations

import heapq
from typing import Sequence

from .model import Job


def build_adjacency(
    jobs: Sequence[Job],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Return ``(adj, indegree)`` for the dependency DAG.

    ``adj[id]`` lists the *dependents* of ``id`` (edges point prerequisite ->
    dependent). ``indegree[id]`` is the number of prerequisites of ``id``.
    Each edge is stored only once (duplicate dependency entries were already
    de-duplicated during validation).
    """
    adj: dict[str, list[str]] = {job.id: [] for job in jobs}
    indegree: dict[str, int] = {job.id: 0 for job in jobs}
    for job in jobs:
        for dep in job.depends_on:
            adj[dep].append(job.id)
            indegree[job.id] += 1
    return adj, indegree


def topological_order(jobs: Sequence[Job]) -> list[str]:
    """Return one valid topological order of ``jobs`` (Kahn's algorithm).

    Tie-breaking is lexicographic on job id via a min-heap, so the result is
    deterministic. Handles disconnected components, independent jobs, and the
    empty list (returns ``[]``).

    Raises ``ValueError`` if the graph contains a cycle; callers are expected
    to have validated the graph first.
    """
    adj, indegree = build_adjacency(jobs)

    heap = [jid for jid, deg in indegree.items() if deg == 0]
    heapq.heapify(heap)

    order: list[str] = []
    while heap:
        node = heapq.heappop(heap)
        order.append(node)
        for nxt in adj[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                heapq.heappush(heap, nxt)

    if len(order) != len(jobs):
        raise ValueError("graph contains a cycle; no topological order exists")

    return order
