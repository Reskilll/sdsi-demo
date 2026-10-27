"""Graph representation and graph algorithms for the scheduler.

:class:`Graph` is the single, immutable representation of a job dependency DAG.
It is built **once** in O(V + E) from a validated job list and then reused by
every analysis (topological sort, stage scheduling, critical path, failure
propagation), so the adjacency structure is never rebuilt and edge scanning is
never duplicated.

All algorithms assume the input has already passed :mod:`validation` (ids are
unique, every referenced dependency exists, no cycles), so they need not
re-check those invariants.
"""

from __future__ import annotations

import heapq
from typing import Mapping, Optional, Sequence

from .model import Job, JobTiming, Stage


class Graph:
    """Immutable dependency DAG built from a validated list of :class:`Job`.

    Edges point from a prerequisite to its dependent. Two adjacencies are
    materialised once in the constructor:

    * ``dependencies[id]`` — the prerequisite ids of ``id`` (forward, aliasing
      the ``Job.depends_on`` tuples).
    * ``dependents[id]`` — the ids that depend on ``id`` (reverse, built here).
    """

    __slots__ = ("_ids", "_durations", "_dependencies", "_dependents")

    def __init__(self, jobs: Sequence[Job]) -> None:
        self._ids: list[str] = [job.id for job in jobs]
        self._durations: dict[str, float] = {job.id: job.duration for job in jobs}
        self._dependencies: dict[str, tuple[str, ...]] = {
            job.id: job.depends_on for job in jobs
        }
        self._dependents: dict[str, list[str]] = {job.id: [] for job in jobs}
        for job in jobs:
            for dep in job.depends_on:
                self._dependents[dep].append(job.id)

    # -- read-only views ------------------------------------------------------

    @property
    def ids(self) -> list[str]:
        """Job ids in their original (input) order."""
        return self._ids

    @property
    def durations(self) -> Mapping[str, float]:
        """Map of job id -> duration."""
        return self._durations

    @property
    def dependencies(self) -> Mapping[str, tuple[str, ...]]:
        """Map of job id -> prerequisite ids."""
        return self._dependencies

    @property
    def dependents(self) -> Mapping[str, list[str]]:
        """Map of job id -> dependent ids (reverse adjacency)."""
        return self._dependents

    def __len__(self) -> int:
        return len(self._ids)

    # -- algorithms -----------------------------------------------------------

    def _initial_indegree(self) -> dict[str, int]:
        """Fresh indegree counts for Kahn-style draining."""
        return {jid: len(deps) for jid, deps in self._dependencies.items()}

    def topological_order(self) -> list[str]:
        """Return one valid topological order (Kahn's algorithm).

        Tie-breaking is lexicographic on job id via a min-heap, so the result
        is deterministic. Handles disconnected components, independent jobs,
        and the empty list (returns ``[]``).

        Raises ``ValueError`` if the graph contains a cycle.
        """
        indegree = self._initial_indegree()
        heap = [jid for jid, deg in indegree.items() if deg == 0]
        heapq.heapify(heap)

        order: list[str] = []
        while heap:
            node = heapq.heappop(heap)
            order.append(node)
            for nxt in self._dependents[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    heapq.heappush(heap, nxt)

        if len(order) != len(self._ids):
            raise ValueError("graph contains a cycle; no topological order exists")
        return order

    def find_cycle(self) -> Optional[list[str]]:
        """Return a representative directed cycle as ``[A, B, C, A]`` or ``None``.

        Drains the graph with Kahn's algorithm; any nodes left over are
        guaranteed to contain a cycle. A forward walk over the residual subgraph
        then yields a real cycle path, not merely a set of involved nodes.
        """
        indegree = self._initial_indegree()
        ready = [jid for jid, deg in indegree.items() if deg == 0]
        remaining = set(self._ids)
        while ready:
            node = ready.pop()
            remaining.discard(node)
            for nxt in self._dependents[node]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)

        if not remaining:
            return None

        # Every residual node has at least one residual dependent, so the walk
        # below always terminates on a repeated node.
        start = min(remaining)
        path: list[str] = []
        seen: set[str] = set()
        current = start
        while current not in seen:
            seen.add(current)
            path.append(current)
            nxts = [n for n in self._dependents[current] if n in remaining]
            current = min(nxts) if nxts else start

        first = path.index(current)
        return path[first:] + [current]

    def schedule_stages(self, workers: int) -> tuple[list[Stage], float]:
        """Partition jobs into barrier-based stages under a worker limit.

        Each stage runs at most ``workers`` jobs whose prerequisites have all
        completed in earlier stages. At every step the lexicographically
        smallest ready jobs are chosen first (min-heap), so the schedule is
        deterministic. A stage's duration is the maximum duration of its jobs;
        the total completion time is the sum of stage durations.
        """
        indegree = self._initial_indegree()
        heap = [jid for jid, deg in indegree.items() if deg == 0]
        heapq.heapify(heap)

        stages: list[Stage] = []
        while heap:
            batch: list[str] = []
            for _ in range(min(workers, len(heap))):
                batch.append(heapq.heappop(heap))

            stage_duration = max(self._durations[jid] for jid in batch)
            stages.append(Stage(job_ids=tuple(batch), duration=stage_duration))

            for jid in batch:
                for nxt in self._dependents[jid]:
                    indegree[nxt] -= 1
                    if indegree[nxt] == 0:
                        heapq.heappush(heap, nxt)

        total = sum(stage.duration for stage in stages)
        return stages, total

    def critical_path_analysis(
        self, order: Sequence[str]
    ) -> tuple[dict[str, JobTiming], float, list[str]]:
        """Compute critical-path timing over the DAG (unlimited workers).

        ``order`` must be a valid topological order (every prerequisite precedes
        its dependent) so that a job's predecessors are timed before it.

        Returns ``(job_times, critical_path_duration, critical_path)``:

        * ``job_times[id]`` holds earliest start/finish, where a job's start is
          the maximum finish among its prerequisites (0 if it has none).
        * ``critical_path_duration`` is the longest weighted path (max finish
          over all jobs; 0 for an empty graph).
        * ``critical_path`` is one representative longest path, tie-broken by
          smallest id at every choice, giving deterministic output.
        """
        job_times: dict[str, JobTiming] = {}
        prev: dict[str, Optional[str]] = {}

        for jid in order:
            deps = self._dependencies[jid]
            if deps:
                # predecessor with the greatest finish time; ties by smallest id
                best_dep = min(deps, key=lambda d: (-job_times[d].earliest_finish, d))
                start = job_times[best_dep].earliest_finish
                prev[jid] = best_dep
            else:
                start = 0.0
                prev[jid] = None
            finish = start + self._durations[jid]
            job_times[jid] = JobTiming(earliest_start=start, earliest_finish=finish)

        if not job_times:
            return {}, 0.0, []

        # endpoint of the longest path, tie-broken by smallest id
        endpoint = min(job_times, key=lambda jid: (-job_times[jid].earliest_finish, jid))
        critical_duration = job_times[endpoint].earliest_finish

        path: list[str] = []
        node: Optional[str] = endpoint
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()

        return job_times, critical_duration, path

    def downstream(self, failed_id: str) -> list[str]:
        """Return all transitive downstream dependents of ``failed_id``.

        Includes direct and indirect dependents only; excludes the failed job
        itself, its prerequisites, and unrelated jobs. The result is sorted
        lexicographically. Raises ``ValueError`` for an unknown ``failed_id``.
        """
        if failed_id not in self._dependents:
            raise ValueError(f"unknown failed job id {failed_id!r}")

        skipped: set[str] = set()
        stack = list(self._dependents[failed_id])
        while stack:
            node = stack.pop()
            if node in skipped:
                continue
            skipped.add(node)
            stack.extend(self._dependents[node])

        return sorted(skipped)


def topological_order(jobs: Sequence[Job]) -> list[str]:
    """Return a valid topological order of ``jobs`` (see :meth:`Graph.topological_order`)."""
    return Graph(jobs).topological_order()
