"""Graph data structure for the DAG job scheduler.

Represents a directed graph of jobs with durations and dependencies.
Provides the common foundation all other modules build on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Job:
    """A single job node in the DAG."""

    id: str
    duration: float
    depends_on: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.duration < 0:
            raise ValueError(
                f"Job '{self.id}' has negative duration ({self.duration}). "
                "Durations must be >= 0."
            )


@dataclass
class DAG:
    """A directed acyclic graph of jobs.

    The primary data structure.  Construct it from parsed JSON, then pass it
    to the validator, scheduler, critical-path calculator, and failure
    simulator.

    Attributes:
        jobs:  dict of job-id → Job.
        adj:   adjacency list (job-id → list of successor ids).
        rev:   reverse adjacency (job-id → list of predecessor ids).
    """

    jobs: Dict[str, Job] = field(default_factory=dict)

    # Derived on construction — do not mutate from outside.
    adj: Dict[str, List[str]] = field(default_factory=dict)
    rev: Dict[str, List[str]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory / I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_list(cls, raw: list[dict]) -> "DAG":
        """Parse a list of job dicts (the JSON input format) into a DAG.

        Each dict must have:
            id        : str   — unique job identifier
            duration  : float — job runtime (>= 0)
            dependsOn : list[str] — ids this job waits on (may be missing / empty)

        Raises ValueError on malformed input.
        """
        if not isinstance(raw, list):
            raise ValueError("Input must be a JSON array of job objects.")

        jobs: Dict[str, Job] = {}
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Item at index {i} is not a JSON object."
                )
            job_id = item.get("id")
            if job_id is None:
                raise ValueError(
                    f"Job at index {i} is missing required field 'id'."
                )
            if not isinstance(job_id, str):
                raise ValueError(
                    f"Job at index {i} has non-string 'id': {job_id!r}."
                )
            if job_id in jobs:
                raise ValueError(
                    f"Duplicate job id '{job_id}' at index {i}."
                )

            duration = item.get("duration")
            if duration is None:
                raise ValueError(
                    f"Job '{job_id}' is missing required field 'duration'."
                )
            if not isinstance(duration, (int, float)):
                raise ValueError(
                    f"Job '{job_id}' has non-numeric duration: {duration!r}."
                )
            if duration < 0:
                raise ValueError(
                    f"Job '{job_id}' has negative duration: {duration}."
                )

            depends_on = item.get("dependsOn", [])

            if not isinstance(depends_on, list):
                raise ValueError(
                    f"Job '{job_id}' has non-list 'dependsOn': {depends_on!r}."
                )

            for d in depends_on:
                if not isinstance(d, str):
                    raise ValueError(
                        f"Job '{job_id}' dependsOn contains non-string value: {d!r}."
                    )

            jobs[job_id] = Job(id=job_id, duration=float(duration), depends_on=list(depends_on))

        return cls.from_jobs(jobs)

    @classmethod
    def from_jobs(cls, jobs: Dict[str, Job]) -> "DAG":
        """Build a DAG from an already-parsed dict of Job objects."""
        adj: Dict[str, List[str]] = {jid: [] for jid in jobs}
        rev: Dict[str, List[str]] = {jid: [] for jid in jobs}

        for jid, job in jobs.items():
            for dep in job.depends_on:
                adj.setdefault(dep, []).append(jid)
                rev.setdefault(jid, []).append(dep)
                # Ensure dep has entries even if it's a missing dependency
                # (the validator will catch that case)
                if dep not in adj:
                    adj[dep] = [jid]
                else:
                    adj[dep].append(jid)

        return cls(jobs=jobs, adj=adj, rev=rev)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def edge_count(self) -> int:
        return sum(len(deps) for deps in self.rev.values())

    def predecessors(self, job_id: str) -> List[str]:
        """Jobs that must finish before *job_id* can start."""
        return list(self.rev.get(job_id, []))

    def successors(self, job_id: str) -> List[str]:
        """Jobs that cannot start until *job_id* finishes."""
        return list(self.adj.get(job_id, []))

    def in_degree(self, job_id: str) -> int:
        return len(self.predecessors(job_id))

    def out_degree(self, job_id: str) -> int:
        return len(self.successors(job_id))

    def source_nodes(self) -> List[str]:
        """Jobs with no dependencies (in-degree == 0)."""
        return [jid for jid in self.jobs if self.in_degree(jid) == 0]

    def sink_nodes(self) -> List[str]:
        """Jobs that nothing depends on (out-degree == 0)."""
        return [jid for jid in self.jobs if self.out_degree(jid) == 0]

    # ------------------------------------------------------------------
    # Sub-graph / traversal helpers
    # ------------------------------------------------------------------

    def downstream_of(self, job_id: str) -> Set[str]:
        """All jobs reachable from *job_id* (transitive closure of successors).

        Performs a BFS/DFS starting at *job_id*.  Returns the set of
        downstream job ids (not including *job_id* itself).
        """
        visited: Set[str] = set()
        stack = [job_id]
        while stack:
            current = stack.pop()
            for nxt in self.successors(current):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        return visited

    def upstream_of(self, job_id: str) -> Set[str]:
        """All jobs that can reach *job_id* (transitive closure of predecessors)."""
        visited: Set[str] = set()
        stack = [job_id]
        while stack:
            current = stack.pop()
            for prev in self.predecessors(current):
                if prev not in visited:
                    visited.add(prev)
                    stack.append(prev)
        return visited