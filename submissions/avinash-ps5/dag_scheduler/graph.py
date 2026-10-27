"""DAG graph model: representation, cycle detection, topological sort."""

from __future__ import annotations

import copy
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .validator import JobSpec


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

@dataclass
class JobNode:
    """A single job in the DAG."""

    name: str
    duration: float  # must be >= 0
    depends_on: List[str] = field(default_factory=list)


@dataclass
class CycleReport:
    """Result of a cycle-detection pass."""

    has_cycle: bool
    cycle_path: List[str]  # list of node names forming the cycle


@dataclass
class TopoReport:
    """Result of topological sort."""

    order: List[str]
    levels: List[List[str]]  # level-order grouping (BFS layers)


# ---------------------------------------------------------------------------
# Graph helper
# ---------------------------------------------------------------------------

def build_adjacency(jobs: Dict[str, JobNode]) -> Dict[str, List[str]]:
    """Return adjacency list from job dict (outgoing edges: x -> children)."""
    adj: Dict[str, List[str]] = defaultdict(list)
    for name, node in jobs.items():
        for dep in node.depends_on:
            adj[dep].append(name)  # dep must finish before name starts
    return dict(adj)


def build_parent_map(jobs: Dict[str, JobNode]) -> Dict[str, int]:
    """Return in-degree map (number of direct dependencies per node)."""
    in_deg: Dict[str, int] = {name: len(node.depends_on) for name, node in jobs.items()}
    return in_deg


# ---------------------------------------------------------------------------
# M1 — Cycle detection (DFS with colouring)
# ---------------------------------------------------------------------------

def detect_cycle(jobs: Dict[str, JobNode]) -> CycleReport:
    """Detect whether the dependency graph contains a cycle.

    Uses tri-colour DFS: 0 = WHITE (unvisited), 1 = GRAY (in-progress),
    2 = BLACK (done).  Returns the first cycle path found.
    """
    adj = build_adjacency(jobs)

    WHITE, GRAY, BLACK = 0, 1, 2
    colour: Dict[str, int] = {name: WHITE for name in jobs}

    # Parent pointers to reconstruct the cycle
    parent: Dict[str, Optional[str]] = {name: None for name in jobs}

    def _dfs(node: str) -> Optional[List[str]]:
        colour[node] = GRAY
        for neighbour in adj.get(node, []):
            if colour[neighbour] == GRAY:
                # Back-edge found → reconstruct cycle
                path: List[str] = [node]
                cur = node
                while cur is not None and cur != neighbour:
                    cur = parent.get(cur, None)  # type: ignore[assignment]
                    if cur is not None:
                        path.append(cur)
                path.append(neighbour)
                path.reverse()
                return path
            elif colour[neighbour] == WHITE:
                parent[neighbour] = node
                result = _dfs(neighbour)
                if result is not None:
                    return result
        colour[node] = BLACK
        return None

    for name in jobs:
        if colour[name] == WHITE:
            cycle = _dfs(name)
            if cycle is not None:
                return CycleReport(has_cycle=True, cycle_path=cycle)

    return CycleReport(has_cycle=False, cycle_path=[])


# ---------------------------------------------------------------------------
# M2 — Topological sort (Kahn's algorithm)
# ---------------------------------------------------------------------------

def topological_sort(jobs: Dict[str, JobNode]) -> TopoReport:
    """Return a valid execution order using Kahn's algorithm.

    Raises ValueError if a cycle is detected.

    Also produces a BFS level grouping: level 0 are the sources, and each
    child sits exactly one level below its furthest parent. Jobs within a
    level are mutually independent.
    """
    in_deg = build_parent_map(jobs)
    adj = build_adjacency(jobs)

    queue: deque[str] = deque(name for name, deg in in_deg.items() if deg == 0)
    order: List[str] = []

    # Level of each node = longest distance from any source (edge = 1).
    level: Dict[str, int] = {name: 0 for name in jobs}

    while queue:
        node = queue.popleft()
        order.append(node)

        for child in adj.get(node, []):
            level[child] = max(level[child], level[node] + 1)
            in_deg[child] -= 1
            if in_deg[child] == 0:
                queue.append(child)

    if len(order) != len(jobs):
        raise ValueError("Graph contains a cycle — cannot produce a topological order")

    # Bucket by level, preserving deterministic (sorted) order within levels.
    by_level: Dict[int, List[str]] = {}
    for name, lvl in level.items():
        by_level.setdefault(lvl, []).append(name)
    levels = [sorted(by_level[lvl]) for lvl in sorted(by_level)]

    return TopoReport(order=order, levels=levels)


# ---------------------------------------------------------------------------
# M4 helper — Longest path / critical path
# ---------------------------------------------------------------------------

@dataclass
class CriticalPathReport:
    """Critical path analysis result."""

    path: List[str]
    total_time: float


def critical_path(jobs: Dict[str, JobNode]) -> CriticalPathReport:
    """Compute the critical (longest) path through the DAG.

    Returns both the sequence of job names and the total duration.
    Uses DP over topological order — O(V + E).
    """
    topo = topological_sort(jobs)
    order = topo.order

    # Longest distance to each node
    dist: Dict[str, float] = {name: 0.0 for name in jobs}
    prev: Dict[str, Optional[str]] = {name: None for name in jobs}

    # Forward-DP: relax edges
    for u in order:
        for v in _children(u, jobs):
            candidate = dist[u] + jobs[u].duration
            if candidate > dist[v]:
                dist[v] = candidate
                prev[v] = u

    # Locate the farthest node (consider all nodes, not just sinks)
    sink = max(dist, key=lambda n: dist[n] + jobs[n].duration)
    total = dist[sink] + jobs[sink].duration

    # Reconstruct path
    path: List[str] = []
    cur: Optional[str] = sink
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()

    return CriticalPathReport(path=path, total_time=total)


def _children(name: str, jobs: Dict[str, JobNode]) -> List[str]:
    """Return immediate downstream jobs (those that depend on *name*)."""
    result: List[str] = []
    for other, node in jobs.items():
        if name in node.depends_on:
            result.append(other)
    return result


# ---------------------------------------------------------------------------
# M5 — Failure simulation
# ---------------------------------------------------------------------------

@dataclass
class FailureReport:
    """Result of simulating a single job failure."""

    failed_job: str
    directly_skipped: List[str]   # immediate downstream
    all_skipped: List[str]        # transitive closure of downstream
    still_runnable: List[str]     # jobs unaffected


def simulate_failure(jobs: Dict[str, JobNode], failed_job: str) -> FailureReport:
    """Given *failed_job*, compute every downstream job that is skipped (transitive closure)."""
    # BFS/DFS from failed_job to collect all transitive dependents
    adj = build_adjacency(jobs)

    visited: Set[str] = set()
    stack: List[str] = [failed_job]
    visited.add(failed_job)

    while stack:
        cur = stack.pop()
        for child in adj.get(cur, []):
            if child not in visited:
                visited.add(child)
                stack.append(child)

    visited.discard(failed_job)  # the failed job itself is not "skipped"
    all_skipped = sorted(visited)

    # Direct downstream = immediate children
    direct = sorted(adj.get(failed_job, []))

    # Still runnable = everything not in transitive closure (incl. failed_job)
    all_affected = visited | {failed_job}
    still_runnable = sorted(set(jobs) - all_affected)

    return FailureReport(
        failed_job=failed_job,
        directly_skipped=direct,
        all_skipped=all_skipped,
        still_runnable=still_runnable,
    )