"""Graph validation — cycle detection and missing-dependency checks (M1).

Exports a single function `validate()` that returns a list of issues
(or an empty list when the DAG is healthy).
"""

from __future__ import annotations

from typing import List, Set, Tuple

from .graph import DAG


class ValidationIssue:
    """A single problem found during validation."""

    def __init__(self, kind: str, message: str, detail: object = None) -> None:
        self.kind = kind          # "cycle" | "missing_dependency" | "duplicate_id"
        self.message = message
        self.detail = detail      # cycle path (List[str]) or missing id (str)


def validate(dag: DAG) -> List[ValidationIssue]:
    """Run all validation checks against *dag*.

    Returns a list of issues.  An empty list means the DAG is valid.
    """
    issues: List[ValidationIssue] = []

    # --- missing dependencies ---
    all_ids = set(dag.jobs.keys())
    for jid, job in dag.jobs.items():
        for dep in job.depends_on:
            if dep not in all_ids:
                issues.append(
                    ValidationIssue(
                        kind="missing_dependency",
                        message=f"Job '{jid}' depends on '{dep}' which is not defined.",
                        detail=dep,
                    )
                )

    # --- cycles ---
    issues.extend(_detect_cycles(dag))

    return issues


# ---------------------------------------------------------------------------
# Cycle detection via iterative DFS with a colour map (Tarjan-style).
# We find *all* cycles, not just the first one.
# ---------------------------------------------------------------------------

WHITE = 0   # unvisited
GREY = 1    # on the current recursion stack
BLACK = 2   # fully processed


def _detect_cycles(dag: DAG) -> List[ValidationIssue]:
    colour: dict[str, int] = {jid: WHITE for jid in dag.jobs}
    issues: List[ValidationIssue] = []

    for jid in dag.jobs:
        if colour[jid] == WHITE:
            _dfs_visit(dag, jid, colour, [], issues)

    return issues


def _dfs_visit(
    dag: DAG,
    node: str,
    colour: dict[str, int],
    path: List[str],
    issues: List[ValidationIssue],
) -> None:
    colour[node] = GREY
    path.append(node)

    for neighbour in dag.successors(node):
        if colour.get(neighbour) == WHITE:
            _dfs_visit(dag, neighbour, colour, path, issues)
        elif colour.get(neighbour) == GREY:
            # Cycle found — extract the sub-path from neighbour to end
            try:
                idx = path.index(neighbour)
            except ValueError:
                idx = 0
            cycle = path[idx:] + [neighbour]
            issues.append(
                ValidationIssue(
                    kind="cycle",
                    message=(
                        f"Cycle detected: {' → '.join(cycle)}. "
                        f"Job '{neighbour}' is both an ancestor and descendant of itself."
                    ),
                    detail=cycle,
                )
            )
        # BLACK neighbours are harmless — forward/cross edge

    path.pop()
    colour[node] = BLACK