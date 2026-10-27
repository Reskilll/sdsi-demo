"""M4 – Critical path and minimum completion time.

Computes the *longest* path through the DAG weighted by job durations.
This determines the theoretical minimum wall-clock time (assuming
unlimited workers).  Each job is scheduled at its earliest possible
start time via a longest-path-from-source algorithm on the DAG.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .graph import DAG, Job


def critical_path(dag: DAG) -> Tuple[List[str], float]:
    """Return the critical path (longest-duration chain) and its total duration.

    A critical path is a sequence of jobs where each depends on the
    previous one, and the sum of their durations is the maximum among all
    such chains.  If multiple paths tie for the longest, the first one
    found via a deterministic traversal is returned.

    Uses dynamic programming on the DAG:
      longest[j] = duration[j] + max(longest[p] for p in predecessors of j)
    """
    if len(dag) == 0:
        return [], 0.0

    # ---- Topological order for DP -----------------------------------------
    # We rebuild in-degree and use Kahn so we process in topological order.
    from collections import deque

    indeg: Dict[str, int] = {jid: dag.in_degree(jid) for jid in dag.jobs}
    queue: deque[str] = deque(dag.roots())
    topo: List[str] = []

    while queue:
        node = queue.popleft()
        topo.append(node)
        for child in sorted(dag.downstream_of(node)):
            indeg[child] -= 1
            if indeg[child] == 0:
                queue.append(child)

    # ---- DP: earliest-start & longest-to-here -----------------------------
    earliest_start: Dict[str, float] = {}
    longest_to: Dict[str, float] = {}
    pred_best: Dict[str, Optional[str]] = {}

    for jid in topo:
        duration = dag.jobs[jid].duration
        # Best predecessor = the one that gives the latest finish into jid
        best_pred: Optional[str] = None
        best_finish: float = 0.0
        for dep in sorted(dag.jobs[jid].depends_on):
            dep_finish = earliest_start.get(dep, 0.0) + dag.jobs[dep].duration
            if dep_finish > best_finish:
                best_finish = dep_finish
                best_pred = dep
        earliest_start[jid] = best_finish
        longest_to[jid] = best_finish + duration
        pred_best[jid] = best_pred

    # ---- Identify the end node with the longest path ----------------------
    end_node = max(longest_to, key=lambda j: longest_to[j])
    total = longest_to[end_node]

    # ---- Walk backwards to reconstruct the path ---------------------------
    path: List[str] = []
    cur: Optional[str] = end_node
    while cur is not None:
        path.append(cur)
        cur = pred_best.get(cur)
    path.reverse()

    return path, total


def min_completion_time(dag: DAG) -> float:
    """Minimum total completion time (the length of the critical path)."""
    _, duration = critical_path(dag)
    return duration


def job_schedule_times(dag: DAG) -> Dict[str, Tuple[float, float]]:
    """Return earliest (start, finish) times for every job assuming unlimited workers.

    Returns
    -------
    dict
        Maps job id → (earliest_start, earliest_finish).
    """
    from collections import deque

    indeg: Dict[str, int] = {jid: dag.in_degree(jid) for jid in dag.jobs}
    queue: deque[str] = deque(dag.roots())
    topo: List[str] = []

    while queue:
        node = queue.popleft()
        topo.append(node)
        for child in sorted(dag.downstream_of(node)):
            indeg[child] -= 1
            if indeg[child] == 0:
                queue.append(child)

    start: Dict[str, float] = {}
    for jid in topo:
        best = 0.0
        for dep in dag.jobs[jid].depends_on:
            dep_finish = start.get(dep, 0.0) + dag.jobs[dep].duration
            if dep_finish > best:
                best = dep_finish
        start[jid] = best

    return {jid: (start[jid], start[jid] + dag.jobs[jid].duration) for jid in dag.jobs}