"""
Job Scheduler with Dependency Resolution (DAG)
==============================================
A mini build/ETL orchestrator that reads a JSON job graph, validates it as a
DAG, produces a topological execution order, groups jobs into parallel stages
with a configurable worker limit, computes the critical path, and simulates
failure propagation.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """A single unit of work in the graph."""

    name: str
    duration: float
    depends_on: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.duration < 0:
            raise ValueError(f"Job '{self.name}': duration must be >= 0, got {self.duration}")


@dataclass
class ValidationError:
    """Represents a single validation problem."""

    kind: str          # "cycle" | "missing_dependency"
    detail: str
    path: list[str] | None = None   # the cycle path when kind == "cycle"


@dataclass
class ValidationReport:
    """The result of validating a job graph."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)

    def add(self, error: ValidationError) -> None:
        self.errors.append(error)
        self.is_valid = False


# ---------------------------------------------------------------------------
# Core scheduler
# ---------------------------------------------------------------------------

class JobGraph:
    """A directed acyclic graph of jobs with scheduling utilities.

    Usage::

        >>> jobs = {"a": {"duration": 1, "dependsOn": []},
        ...         "b": {"duration": 2, "dependsOn": ["a"]}}
        >>> graph = JobGraph.from_dict(jobs)
        >>> graph.validate()
        ValidationReport(is_valid=True, errors=[])
        >>> graph.topological_order()
        ['a', 'b']
    """

    def __init__(self, jobs: dict[str, Job]) -> None:
        self.jobs = jobs
        self._adj: dict[str, list[str]] = {}
        self._rev_adj: dict[str, list[str]] = {}
        self._in_degree: dict[str, int] = {}
        self._build_adjacency()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, raw: dict[str, dict[str, Any]]) -> JobGraph:
        """Build a JobGraph from a plain dict (e.g. parsed JSON)."""
        if not isinstance(raw, dict):
            raise TypeError("Input must be a JSON object mapping job names to definitions")

        jobs: dict[str, Job] = {}
        for name, spec in raw.items():
            if not isinstance(spec, dict):
                raise TypeError(f"Job '{name}': definition must be an object, got {type(spec).__name__}")
            if "duration" not in spec:
                raise KeyError(f"Job '{name}': missing required field 'duration'")
            try:
                duration = float(spec["duration"])
            except (ValueError, TypeError):
                raise ValueError(f"Job '{name}': 'duration' must be a number, got {spec['duration']!r}")
            depends_on = spec.get("dependsOn", [])
            if not isinstance(depends_on, list):
                raise TypeError(f"Job '{name}': 'dependsOn' must be an array, got {type(depends_on).__name__}")
            if not all(isinstance(d, str) for d in depends_on):
                raise TypeError(f"Job '{name}': every entry in 'dependsOn' must be a string")
            jobs[name] = Job(name=name, duration=duration, depends_on=depends_on)

        if not jobs:
            raise ValueError("Job graph must contain at least one job")

        return cls(jobs)

    @classmethod
    def from_file(cls, path: str | Path) -> JobGraph:
        """Load a JobGraph from a JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    def _build_adjacency(self) -> None:
        """Pre-compute adjacency lists and in-degree counts.

        Missing dependencies are silently skipped here — validation catches
        them later via ``validate()`` so the graph can still be constructed
        and all errors reported at once.
        """
        self._adj = {name: [] for name in self.jobs}
        self._rev_adj = {name: [] for name in self.jobs}
        self._in_degree = {name: 0 for name in self.jobs}

        for name, job in self.jobs.items():
            for dep in job.depends_on:
                if dep not in self.jobs:
                    continue  # skip undefined deps; validate() reports them
                self._adj[dep].append(name)        # dep → name (forward edge)
                self._rev_adj[name].append(dep)     # name → dep (reverse edge)
                self._in_degree[name] += 1

    # ------------------------------------------------------------------
    # M1 — Validation
    # ------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Validate the graph: detect missing dependencies and cycles.

        Returns a ``ValidationReport``.  If ``is_valid`` is ``True`` the graph
        is a well-formed DAG and all remaining methods will succeed.

        Cycle detection reports the *full cycle path*, not just the nodes
        involved.
        """
        report = ValidationReport(is_valid=True)

        # --- Missing dependencies ---
        all_names = set(self.jobs)
        for name, job in self.jobs.items():
            for dep in job.depends_on:
                if dep not in all_names:
                    report.add(ValidationError(
                        kind="missing_dependency",
                        detail=f"Job '{name}' depends on '{dep}', which is not defined in the graph.",
                    ))

        # If any dependency is missing we still try cycle detection on the
        # sub-graph that *is* defined (ignoring edges pointing outside), so the
        # caller sees all problems at once.
        defined = all_names

        # --- Cycle detection (iterative DFS with three-colour marking) ---
        # Iterative to avoid recursion limits on deep graphs.
        WHITE, GREY, BLACK = 0, 1, 2
        colour: dict[str, int] = {n: WHITE for n in self.jobs}
        parent: dict[str, str | None] = {n: None for n in self.jobs}

        def _reconstruct_cycle(start: str, end: str) -> list[str]:
            """Walk back through parent pointers to build the cycle path."""
            path = []
            cur = start
            while cur is not None and cur != end:
                path.append(cur)
                cur = parent[cur]
            path.append(end)
            path.append(start)
            path.reverse()
            return path

        for root in self.jobs:
            if colour[root] != WHITE:
                continue

            # Stack entries: (node, iterator_index)
            stack: list[tuple[str, int]] = [(root, 0)]
            colour[root] = GREY

            while stack:
                node, idx = stack[-1]
                neighbours = [n for n in self._adj.get(node, []) if n in defined]

                if idx < len(neighbours):
                    stack[-1] = (node, idx + 1)
                    neighbour = neighbours[idx]

                    if colour[neighbour] == GREY:
                        parent[neighbour] = node
                        cycle = _reconstruct_cycle(node, neighbour)
                        report.add(ValidationError(
                            kind="cycle",
                            detail=f"Cycle detected involving jobs: {' → '.join(cycle)}",
                            path=cycle,
                        ))
                    elif colour[neighbour] == WHITE:
                        parent[neighbour] = node
                        colour[neighbour] = GREY
                        stack.append((neighbour, 0))
                else:
                    colour[node] = BLACK
                    stack.pop()

        return report

    # ------------------------------------------------------------------
    # M2 — Topological order (Kahn's algorithm)
    # ------------------------------------------------------------------

    def topological_order(self) -> list[str]:
        """Return a valid topological execution order.

        Requires a valid DAG (call ``validate()`` first).
        Uses Kahn's algorithm — stable and iterative.
        """
        report = self.validate()
        if not report.is_valid:
            raise ValueError(
                "Graph is not a valid DAG. Call validate() for details.\n"
                + "\n".join(f"  - {e.detail}" for e in report.errors)
            )

        in_deg = dict(self._in_degree)
        queue: deque[str] = deque(n for n, d in in_deg.items() if d == 0)
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbour in self._adj[node]:
                in_deg[neighbour] -= 1
                if in_deg[neighbour] == 0:
                    queue.append(neighbour)

        return order

    # ------------------------------------------------------------------
    # M3 — Parallel stages
    # ------------------------------------------------------------------

    def parallel_stages(self, worker_limit: int = 0) -> list[list[str]]:
        """Group jobs into parallel execution stages respecting *worker_limit*.

        ``worker_limit`` must be a positive integer, or 0 for unlimited.

        Jobs in the same stage have all their dependencies satisfied and can
        run concurrently.  When a stage has more jobs than *worker_limit*, it
        is split into sub-stages (each capped at *worker_limit*) so the caller
        knows exactly which subset of the stage runs together.
        """
        if worker_limit < 0:
            raise ValueError(f"worker_limit must be >= 0, got {worker_limit}")

        report = self.validate()
        if not report.is_valid:
            raise ValueError(
                "Graph is not a valid DAG. Call validate() for details.\n"
                + "\n".join(f"  - {e.detail}" for e in report.errors)
            )

        in_deg = dict(self._in_degree)
        available: deque[str] = deque(n for n, d in in_deg.items() if d == 0)
        stages: list[list[str]] = []

        while available:
            # All jobs in *available* are ready — group them respecting the cap.
            # worker_limit == 0 means unlimited: take all available jobs.
            take = len(available) if worker_limit == 0 else min(len(available), worker_limit)
            stage: list[str] = []
            for _ in range(take):
                job = available.popleft()
                stage.append(job)
            stages.append(stage)

            # Release dependants of every job in this stage
            for job in stage:
                for neighbour in self._adj[job]:
                    in_deg[neighbour] -= 1
                    if in_deg[neighbour] == 0:
                        available.append(neighbour)

        return stages

    # ------------------------------------------------------------------
    # M4 — Critical path
    # ------------------------------------------------------------------

    def critical_path(self) -> tuple[list[str], float]:
        """Compute the critical path — the longest path through the DAG.

        Returns ``(path, total_duration)``.  The critical path determines the
        minimum possible completion time of the whole schedule.
        """
        report = self.validate()
        if not report.is_valid:
            raise ValueError(
                "Graph is not a valid DAG. Call validate() for details.\n"
                + "\n".join(f"  - {e.detail}" for e in report.errors)
            )

        topo = self.topological_order()

        # Earliest start time for each job
        est: dict[str, float] = {name: 0.0 for name in self.jobs}
        # Predecessor on the longest incoming path
        prev: dict[str, str | None] = {name: None for name in self.jobs}

        for node in topo:
            for dep in self._rev_adj[node]:
                finish_time = est[dep] + self.jobs[dep].duration
                if finish_time > est[node]:
                    est[node] = finish_time
                    prev[node] = dep

        # Find the job with the latest finish time
        max_time = 0.0
        sink = topo[0]
        for node in topo:
            finish = est[node] + self.jobs[node].duration
            if finish > max_time:
                max_time = finish
                sink = node

        # Reconstruct path
        path: list[str] = []
        cur: str | None = sink
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()

        return path, max_time

    # ------------------------------------------------------------------
    # M5 — Failure simulation
    # ------------------------------------------------------------------

    def downstream_jobs(self, failed_job: str) -> list[str]:
        """Return every job transitively dependent on *failed_job*.

        These are the jobs that must be skipped when *failed_job* fails.
        The list is returned in topological order.
        """
        if failed_job not in self.jobs:
            raise KeyError(f"Job '{failed_job}' not found in the graph")

        # BFS/DFS from failed_job through forward edges
        visited: set[str] = set()
        queue: deque[str] = deque([failed_job])
        visited.add(failed_job)

        while queue:
            node = queue.popleft()
            for neighbour in self._adj[node]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)

        # Remove the failed job itself; caller wants *downstream*
        visited.discard(failed_job)

        # Return in topological order for determinism
        topo = self.topological_order()
        return [j for j in topo if j in visited]

    # ------------------------------------------------------------------
    # Full schedule (convenience)
    # ------------------------------------------------------------------

    def schedule(self, worker_limit: int = 0) -> dict[str, Any]:
        """Run the full analysis and return a dictionary of results."""
        report = self.validate()
        if not report.is_valid:
            return {
                "valid": False,
                "errors": [
                    {"kind": e.kind, "detail": e.detail, "path": e.path}
                    for e in report.errors
                ],
            }

        critical, min_time = self.critical_path()
        stages = self.parallel_stages(worker_limit)

        return {
            "valid": True,
            "job_count": len(self.jobs),
            "topological_order": self.topological_order(),
            "parallel_stages": stages,
            "stage_count": len(stages),
            "critical_path": critical,
            "min_completion_time_seconds": min_time,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for command-line usage.

    Usage::

        python scheduler.py sample.json [--worker-limit N] [--fail JOB]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Job Scheduler — validate & analyse a DAG of jobs.",
    )
    parser.add_argument(
        "input", type=Path,
        help="Path to a JSON job-graph file.",
    )
    parser.add_argument(
        "--worker-limit", "-w", type=int, default=0,
        help="Max concurrent workers (0 = unlimited).",
    )
    parser.add_argument(
        "--fail", "-f", type=str, default=None,
        help="Simulate failure of a job and list skipped downstream jobs.",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"File not found: {args.input}")

    graph = JobGraph.from_file(args.input)

    result = graph.schedule(worker_limit=args.worker_limit)
    print(json.dumps(result, indent=2))

    if args.fail:
        print(f"\n--- Failure simulation: job '{args.fail}' failed ---")
        try:
            skipped = graph.downstream_jobs(args.fail)
        except KeyError as exc:
            print(f"  Error: {exc}")
        else:
            if skipped:
                print(f"  Skipped downstream jobs: {', '.join(skipped)}")
            else:
                print("  No downstream jobs affected.")


if __name__ == "__main__":
    main()