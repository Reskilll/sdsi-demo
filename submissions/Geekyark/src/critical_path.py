"""Critical path analysis (M4).

Computes the critical path through the DAG — the longest chain of
dependencies that determines the minimum total completion time.

Method:
  1. Forward pass (topological order) → earliest start / finish times.
  2. Backward pass (reverse order)    → latest start / finish times.
  3. Slack = LST − EST.  Jobs with zero slack are on the critical path.
     Paths are reconstructed by walking forward from sources, always
     following zero-slack successors.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .graph import DAG
from .toposort import topological_sort


@dataclass
class CriticalPathResult:
    """Result of critical-path analysis."""

    # Per-job timing
    earliest_start: Dict[str, float] = field(default_factory=dict)
    earliest_finish: Dict[str, float] = field(default_factory=dict)
    latest_start: Dict[str, float] = field(default_factory=dict)
    latest_finish: Dict[str, float] = field(default_factory=dict)
    slack: Dict[str, float] = field(default_factory=dict)

    # Critical path(s) — there may be multiple
    critical_paths: List[List[str]] = field(default_factory=list)

    # Minimum total completion time (makespan with unlimited workers)
    min_completion_time: float = 0.0


def compute_critical_path(dag: DAG) -> CriticalPathResult:
    """Analyze the critical path(s) of *dag*.

    Returns full timing information plus all critical paths found.
    """
    if dag.job_count == 0:
        return CriticalPathResult()

    order = topological_sort(dag)

    # ------------------------------------------------------------------
    # Forward pass — earliest start / finish
    # ------------------------------------------------------------------
    est: Dict[str, float] = {}
    eft: Dict[str, float] = {}

    for jid in order:
        preds = dag.predecessors(jid)
        if not preds:
            est[jid] = 0.0
        else:
            est[jid] = max(eft[p] for p in preds)
        eft[jid] = est[jid] + dag.jobs[jid].duration

    min_completion = max(eft.values())

    # ------------------------------------------------------------------
    # Backward pass — latest start / finish
    # ------------------------------------------------------------------
    lst: Dict[str, float] = {}
    lft: Dict[str, float] = {}

    for jid in reversed(order):
        succs = dag.successors(jid)
        if not succs:
            lft[jid] = min_completion
        else:
            lft[jid] = min(lst[s] for s in succs)
        lst[jid] = lft[jid] - dag.jobs[jid].duration

    # ------------------------------------------------------------------
    # Slack
    # ------------------------------------------------------------------
    slack = {jid: lst[jid] - est[jid] for jid in order}

    # ------------------------------------------------------------------
    # Reconstruct critical paths (DFS from sources, only zero-slack edges)
    # ------------------------------------------------------------------
    zero_slack = {jid for jid, s in slack.items() if abs(s) < 1e-9}

    critical_paths: List[List[str]] = []
    sources = [s for s in dag.source_nodes() if s in zero_slack]

    for src in sources:
        _collect_critical_paths(dag, zero_slack, eft, src, [], critical_paths, min_completion)

    return CriticalPathResult(
        earliest_start=est,
        earliest_finish=eft,
        latest_start=lst,
        latest_finish=lft,
        slack=slack,
        critical_paths=critical_paths,
        min_completion_time=min_completion,
    )


def _collect_critical_paths(
    dag: DAG,
    zero_slack: set[str],
    eft: Dict[str, float],
    current: str,
    path: List[str],
    results: List[List[str]],
    min_completion: float,
) -> None:
    path.append(current)
    zero_slack_succs = [s for s in dag.successors(current) if s in zero_slack]

    if not zero_slack_succs:
        # Leaf on the critical path — accept if it reaches the makespan.
        if abs(eft[current] - min_completion) < 1e-9:
            results.append(list(path))
    else:
        for succ in zero_slack_succs:
            _collect_critical_paths(dag, zero_slack, eft, succ, path, results, min_completion)

    path.pop()