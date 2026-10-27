"""DAG representation, validation, and topological sort.

Represents a collection of jobs as a Directed Acyclic Graph.  Every job
is a node; `dependsOn` entries become directed edges *from* the dependency
*toward* the dependent (i.e. the dependency must finish first).
"""

from __future__ import annotations

import copy
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """A single unit of work in the dependency graph."""

    id: str
    duration: float
    depends_on: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Job":
        """Parse a single job from a JSON dictionary entry."""
        if "id" not in raw:
            raise ValueError("Job dictionary is missing required key 'id'")
        if "duration" not in raw:
            raise ValueError(f"Job '{raw['id']}' is missing required key 'duration'")
        duration = raw["duration"]
        if not isinstance(duration, (int, float)) or duration < 0:
            raise ValueError(
                f"Job '{raw['id']}' duration must be a non-negative number, got {duration!r}"
            )
        depends_on = raw.get("dependsOn", [])
        if not isinstance(depends_on, list):
            raise ValueError(
                f"Job '{raw['id']}' dependsOn must be a list, got {type(depends_on).__name__}"
            )
        for dep in depends_on:
            if not isinstance(dep, str):
                raise ValueError(
                    f"Job '{raw['id']}' dependsOn entries must be strings, got {dep!r}"
                )
        return cls(id=raw["id"], duration=float(duration), depends_on=depends_on)


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

@dataclass
class DAG:
    """A validated Directed Acyclic Graph of Jobs.

    After construction the graph is guaranteed to be cycle-free and have
    no missing dependencies.  Use ``DAG.from_dicts()`` or
    ``DAG.from_json_file()`` to parse input.
    """

    jobs: Dict[str, Job] = field(default_factory=dict)
    # Adjacency list: job_id -> list of downstream (dependent) job ids
    _downstream: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dicts(cls, job_dicts: List[Dict[str, Any]]) -> "DAG":
        """Build and validate a DAG from a list of raw job dictionaries."""
        dag = cls()
        # Parse
        for raw in job_dicts:
            job = Job.from_dict(raw)
            if job.id in dag.jobs:
                raise ValueError(f"Duplicate job id: {job.id!r}")
            dag.jobs[job.id] = job

        # Build adjacency
        for job in dag.jobs.values():
            for dep in job.depends_on:
                dag._downstream[dep].append(job.id)

        # Validate
        dag._validate_no_missing_dependencies()
        dag._validate_no_cycles()
        return dag

    @classmethod
    def from_json_file(cls, path: str | Path) -> "DAG":
        """Load and validate a DAG from a JSON file on disk."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(
                f"Expected a JSON array of job objects, got {type(raw).__name__}"
            )
        return cls.from_dicts(raw)

    # ------------------------------------------------------------------
    # M1 – validation
    # ------------------------------------------------------------------

    def _validate_no_missing_dependencies(self) -> None:
        """Raise ``ValueError`` if any job references a non-existent dependency."""
        missing: List[Tuple[str, str]] = []
        for job in self.jobs.values():
            for dep in job.depends_on:
                if dep not in self.jobs:
                    missing.append((job.id, dep))
        if missing:
            detail = "; ".join(
                f"job '{jid}' depends on missing job '{dep}'" for jid, dep in missing
            )
            raise ValueError(f"Missing dependencies detected: {detail}")

    def _validate_no_cycles(self) -> None:
        """Raise ``ValueError`` with the cycle path if the graph is not acyclic.

        Uses a three-color DFS (WHITE / GRAY / BLACK).
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {jid: WHITE for jid in self.jobs}
        parent: Dict[str, Optional[str]] = {}

        # Sort for deterministic output
        sorted_ids = sorted(self.jobs.keys())

        def _cycle_path(start: str, end: str) -> List[str]:
            """Walk parent pointers from *start* back to *end* and reverse."""
            path: List[str] = [start]
            while path[-1] != end:
                p = parent.get(path[-1])
                if p is None:
                    return []
                path.append(p)
            path.reverse()
            return path

        # Iterative DFS to avoid recursion-depth issues on deep graphs
        for start in sorted_ids:
            if color[start] != WHITE:
                continue
            stack: List[Tuple[str, Iterator[str]]] = []
            color[start] = GRAY
            parent[start] = None
            neighbors = iter(sorted(self._downstream.get(start, [])))
            stack.append((start, neighbors))

            while stack:
                node, niter = stack[-1]
                try:
                    child = next(niter)
                except StopIteration:
                    color[node] = BLACK
                    stack.pop()
                    continue

                if color[child] == GRAY:
                    parent[child] = node
                    # _cycle_path walks from node back to child, then reverses,
                    # giving [child, ..., node].  Append child to close the loop.
                    cycle = _cycle_path(node, child)
                    cycle.append(child)
                    raise ValueError(
                        f"Cycle detected: {' -> '.join(cycle)}"
                    )
                if color[child] == BLACK:
                    continue
                color[child] = GRAY
                parent[child] = node
                stack.append((child, iter(sorted(self._downstream.get(child, [])))))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def job_ids(self) -> Set[str]:
        return set(self.jobs.keys())

    def downstream_of(self, job_id: str) -> List[str]:
        """Jobs that directly depend on *job_id*."""
        return list(self._downstream.get(job_id, []))

    def in_degree(self, job_id: str) -> int:
        """Number of unmet dependencies for *job_id*."""
        return len(self.jobs[job_id].depends_on)

    def roots(self) -> List[str]:
        """Jobs with no dependencies (in-degree == 0)."""
        return sorted(jid for jid, job in self.jobs.items() if not job.depends_on)

    def leaves(self) -> List[str]:
        """Jobs that nothing else depends on (out-degree == 0)."""
        return sorted(jid for jid in self.jobs if jid not in self._downstream)

    def __len__(self) -> int:
        return len(self.jobs)

    def __repr__(self) -> str:
        return f"<DAG jobs={len(self)} roots={self.roots()}>"