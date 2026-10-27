"""M1: Graph validation — cycle detection and missing dependency reporting.

Uses iterative 3-color DFS to detect cycles (with path reconstruction) and
checks that every dependency references an existing job id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from scheduler.models import JobGraph

WHITE, GRAY, BLACK = 0, 1, 2


@dataclass
class ValidationResult:
    """Result of DAG validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    missing_deps: List[str] = field(default_factory=list)

    @property
    def has_cycles(self) -> bool:
        return len(self.cycles) > 0

    @property
    def has_missing_deps(self) -> bool:
        return len(self.missing_deps) > 0


def validate(graph: JobGraph) -> ValidationResult:
    """Validate the job graph for structural correctness.

    Checks:
      1. Missing dependencies (dependsOn referencing non-existent jobs)
      2. Cycles (returns the cycle path for each detected cycle)

    Returns a ValidationResult with aggregated errors.
    """
    result = ValidationResult(is_valid=True)

    # --- missing dependencies ---
    missing: Set[str] = set()
    for job in graph.jobs:
        for dep in job.depends_on:
            if dep not in graph:
                missing.add(dep)
    result.missing_deps = sorted(missing)
    if missing:
        result.is_valid = False
        result.errors.append(
            f"Missing dependencies: {', '.join(sorted(missing))}"
        )

    # --- cycle detection (iterative 3-color DFS) ---
    cycles = _detect_cycles_iterative(graph)
    result.cycles = cycles
    if cycles:
        result.is_valid = False
        for cycle in cycles:
            cycle_path = " -> ".join(cycle)
            result.errors.append(f"Cycle detected: {cycle_path}")

    return result


def _detect_cycles_iterative(graph: JobGraph) -> List[List[str]]:
    """Iterative DFS cycle detection with path reconstruction.

    Uses an explicit stack to avoid recursion limits on large graphs.
    Each stack entry is (job_id, iterator_index, state) where state:
      - 0: just entered (GRAY)
      - 1: done with children (BLACK)
    """
    color: Dict[str, int] = {}
    parent: Dict[str, Optional[str]] = {}

    for jid in graph.id_set:
        color[jid] = WHITE
        parent[jid] = None

    cycles: List[List[str]] = []

    for start in graph.id_set:
        if color[start] != WHITE:
            continue

        # Stack: (job_id, neighbor_index, visited_for_path)
        # visited_for_path tracks nodes on current path for cycle reconstruction
        stack: List[str] = []
        stack.append(start)
        color[start] = GRAY
        parent[start] = None

        # We need an explicit DFS stack for traversal order
        dfs_stack: List[tuple] = [(start, 0)]

        while dfs_stack:
            jid, idx = dfs_stack[-1]
            deps = graph.depends_of(jid)

            if idx < len(deps):
                dfs_stack[-1] = (jid, idx + 1)
                dep = deps[idx]

                if color.get(dep) == GRAY:
                    # Back edge: reconstruct cycle
                    cycle = [dep, jid]
                    cur = jid
                    while cur is not None and cur != dep:
                        cur = parent.get(cur)  # type: ignore
                        if cur and cur != dep:
                            cycle.append(cur)
                    cycle.append(dep)
                    cycle.reverse()
                    # Deduplicate trailing node
                    cycles.append(cycle)

                elif color.get(dep) == WHITE:
                    color[dep] = GRAY
                    parent[dep] = jid
                    dfs_stack.append((dep, 0))
            else:
                # All neighbors processed
                dfs_stack.pop()
                color[jid] = BLACK

    return cycles