"""Job and JobGraph data models with JSON loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Union


@dataclass
class Job:
    """A single job in the DAG."""
    id: str
    duration: float
    depends_on: List[str] = field(default_factory=list)


@dataclass
class JobGraph:
    """Full DAG representation with adjacency lookups."""

    jobs: List[Job]
    _by_id: Dict[str, Job] = field(default_factory=dict)
    _dependents: Dict[str, List[str]] = field(default_factory=dict)
    _id_set: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._by_id = {j.id: j for j in self.jobs}
        self._id_set = set(self._by_id)
        self._dependents = {jid: [] for jid in self._id_set}
        for j in self.jobs:
            for dep in j.depends_on:
                if dep in self._dependents:
                    self._dependents[dep].append(j.id)

    @property
    def id_set(self) -> Set[str]:
        return self._id_set

    def get(self, job_id: str) -> Job:
        """Return Job by id, or raise KeyError."""
        return self._by_id[job_id]

    def dependents_of(self, job_id: str) -> List[str]:
        """Jobs that depend on this one (outgoing edges)."""
        return self._dependents.get(job_id, [])

    def depends_of(self, job_id: str) -> List[str]:
        """Jobs this job depends on (incoming edges)."""
        return list(self._by_id[job_id].depends_on)

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._id_set


class GraphLoadError(Exception):
    """Raised when the input JSON has structural/schema problems."""


def _normalize_depends(raw: Any, job_id: str) -> List[str]:
    """Normalize dependsOn field: accept None/missing, single string, or list."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        if not all(isinstance(x, str) for x in raw):
            raise GraphLoadError(
                f"Job '{job_id}': dependsOn must be a string or list of strings"
            )
        return list(raw)
    raise GraphLoadError(
        f"Job '{job_id}': dependsOn must be a string, list of strings, or omitted"
    )


def load_graph(data: Union[str, Path, Dict[str, Any]]) -> JobGraph:
    """Load a JobGraph from a JSON file path, string, or dict.

    Args:
        data: File path (str/Path), JSON string, or already-parsed dict.

    Returns:
        Validated JobGraph.

    Raises:
        GraphLoadError: If the structure is invalid.
    """
    if isinstance(data, (str, Path)):
        path = Path(data)
        if isinstance(data, str) and data.strip().startswith("{"):
            # Inline JSON string
            try:
                raw = json.loads(data)
            except json.JSONDecodeError as e:
                raise GraphLoadError(f"Invalid JSON: {e}") from e
        else:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                raise GraphLoadError(f"File not found: {path}")
            except json.JSONDecodeError as e:
                raise GraphLoadError(f"Invalid JSON in {path}: {e}") from e
    elif isinstance(data, dict):
        raw = data
    else:
        raise GraphLoadError(f"Expected file path, JSON string, or dict; got {type(data).__name__}")

    if not isinstance(raw, dict):
        raise GraphLoadError("Top-level JSON must be an object")

    raw_jobs = raw.get("jobs")
    if not isinstance(raw_jobs, list):
        raise GraphLoadError("'jobs' must be a list")

    if len(raw_jobs) == 0:
        return JobGraph(jobs=[])

    seen_ids: Set[str] = set()
    jobs: List[Job] = []

    for i, entry in enumerate(raw_jobs):
        if not isinstance(entry, dict):
            raise GraphLoadError(f"jobs[{i}]: must be an object, got {type(entry).__name__}")

        jid = entry.get("id")
        if not isinstance(jid, str) or not jid.strip():
            raise GraphLoadError(f"jobs[{i}]: 'id' must be a non-empty string")

        if jid in seen_ids:
            raise GraphLoadError(f"Duplicate job id: '{jid}'")
        seen_ids.add(jid)

        dur = entry.get("duration")
        if dur is None:
            raise GraphLoadError(f"Job '{jid}': 'duration' is required")
        if not isinstance(dur, (int, float)):
            raise GraphLoadError(
                f"Job '{jid}': 'duration' must be a number, got {type(dur).__name__}"
            )
        if dur <= 0:
            raise GraphLoadError(f"Job '{jid}': 'duration' must be positive, got {dur}")

        deps = _normalize_depends(entry.get("dependsOn"), jid)
        jobs.append(Job(id=jid, duration=float(dur), depends_on=deps))

    return JobGraph(jobs=jobs)