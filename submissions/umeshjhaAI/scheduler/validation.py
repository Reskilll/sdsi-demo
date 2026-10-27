"""Input parsing and full validation of the job description (M1).

The public entry point is :func:`parse_jobs`, which never raises on malformed
input. It returns ``(jobs, workers, errors)`` where ``errors`` is the
aggregated list of every independent problem found.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence, Tuple

from .errors import ValidationError
from .model import Job


def _is_int(value: Any) -> bool:
    """True only for a genuine ``int`` (``bool`` is a subclass of ``int`` and
    is therefore explicitly excluded)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    """True for a finite, non-bool real number (int or float)."""
    return _is_int(value) or (isinstance(value, float) and math.isfinite(value))


def parse_jobs(
    raw: Any,
    workers_override: Optional[int] = None,
) -> Tuple[list[Job], int, list[str]]:
    """Validate a parsed JSON document and return ``(jobs, workers, errors)``.

    ``raw`` is the already-deserialized JSON value (a Python object), not a
    string. ``workers_override`` is the CLI ``--workers`` value, already parsed
    to an ``int`` by argparse (or ``None``). It takes precedence over any
    ``workers`` field in the JSON.

    This function is total: it never raises. On structural problems it returns
    an empty job list and an empty worker count; callers must treat a
    non-empty ``errors`` list as a failure.
    """
    errors: list[str] = []

    # ---- top-level structure -------------------------------------------------
    if not isinstance(raw, dict):
        return [], 0, ["input must be a JSON object with a 'jobs' key"]
    if "jobs" not in raw:
        return [], 0, ["input is missing the required 'jobs' key"]
    if not isinstance(raw["jobs"], list):
        return [], 0, ["'jobs' must be a list"]

    raw_jobs: list = raw["jobs"]

    # ---- workers ------------------------------------------------------------
    workers = 1
    if "workers" in raw:
        w = raw["workers"]
        if not _is_int(w):
            errors.append(
                f"workers must be an integer >= 1, got {type(w).__name__}"
            )
        elif w < 1:
            errors.append(f"workers must be >= 1, got {w}")
        else:
            workers = w

    if workers_override is not None:
        if not _is_int(workers_override):
            errors.append(
                "workers must be an integer >= 1, "
                f"got {type(workers_override).__name__}"
            )
        elif workers_override < 1:
            errors.append(f"workers must be >= 1, got {workers_override}")
        else:
            workers = workers_override

    # ---- per-job structural validation -------------------------------------
    jobs: list[Job] = []
    seen_ids: dict[str, int] = {}  # id -> first index (1-based) where seen

    for idx, item in enumerate(raw_jobs, start=1):
        path = f"jobs[{idx - 1}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object, got {type(item).__name__}")
            continue

        # id
        jid = item.get("id")
        if jid is None:
            errors.append(f"{path} is missing required 'id'")
            # no usable id -> skip the rest of this job's checks
            continue
        if not isinstance(jid, str):
            errors.append(
                f"{path}.id must be a string, got {type(jid).__name__}"
            )
            continue
        if jid == "":
            errors.append(f"{path}.id must be a non-empty string")
            continue
        if jid in seen_ids:
            errors.append(
                f"duplicate job id {jid!r} at {path} "
                f"(first seen at jobs[{seen_ids[jid] - 1}])"
            )
            continue
        seen_ids[jid] = idx

        # duration
        dur = item.get("duration")
        if dur is None:
            errors.append(f"{path} is missing required 'duration'")
            continue
        if not _is_number(dur):
            if isinstance(dur, bool):
                errors.append(f"{path}.duration must be a number, not a boolean")
            elif isinstance(dur, float) and not math.isfinite(dur):
                errors.append(
                    f"{path}.duration must be finite, got {dur!r}"
                )
            else:
                errors.append(
                    f"{path}.duration must be a number, got {type(dur).__name__}"
                )
            continue
        if dur <= 0:
            errors.append(f"{path}.duration must be positive, got {dur}")
            continue

        # dependsOn
        depends: list[str] = []
        raw_deps = item.get("dependsOn")
        if raw_deps is None:
            raw_deps = []
        if not isinstance(raw_deps, list):
            errors.append(f"{path}.dependsOn must be a list")
            continue
        for d in raw_deps:
            if not isinstance(d, str):
                errors.append(
                    f"{path}.dependsOn entries must be strings, "
                    f"got {type(d).__name__}"
                )
                continue
            if d == "":
                errors.append(f"{path}.dependsOn entries must be non-empty strings")
                continue
            depends.append(d)

        # de-duplicate dependency edges but keep first-seen order
        deduped: list[str] = []
        for d in depends:
            if d not in deduped:
                deduped.append(d)

        jobs.append(Job(id=jid, duration=float(dur), depends_on=tuple(deduped)))

    # ---- cross-job dependency checks ----------------------------------------
    if not errors:
        known = {job.id for job in jobs}
        for job in jobs:
            for dep in job.depends_on:
                if dep == job.id:
                    errors.append(
                        f"job {job.id!r} cannot depend on itself"
                    )
                elif dep not in known:
                    errors.append(
                        f"job {job.id!r} depends on missing job {dep!r}"
                    )

    # Only check for cycles once everything else is structurally sound; a
    # cycle among already-invalid nodes would produce confusing noise.
    if not errors:
        cycle = _find_cycle(jobs)
        if cycle is not None:
            errors.append("dependency cycle detected: " + " -> ".join(cycle))

    if errors:
        return [], 0, errors

    return jobs, workers, []


def _find_cycle(jobs: Sequence[Job]) -> Optional[list[str]]:
    """Return a representative directed cycle as ``[A, B, C, A]`` or ``None``.

    Implemented as Kahn's algorithm (mirrors ``graph.topological_order``) so a
    cycle is reported only when no topological order exists. The remaining
    nodes are guaranteed to contain a cycle; we walk dependents from one of
    them until a node repeats.
    """
    adj: dict[str, list[str]] = {job.id: [] for job in jobs}
    indegree: dict[str, int] = {job.id: 0 for job in jobs}
    for job in jobs:
        for dep in job.depends_on:
            adj[dep].append(job.id)
            indegree[job.id] += 1

    # ready = nodes with zero indegree; use a plain list (order irrelevant
    # here, we only care about whether everything drains)
    ready = [nid for nid, deg in indegree.items() if deg == 0]
    remaining = set(indegree)
    while ready:
        node = ready.pop()
        remaining.discard(node)
        for nxt in adj[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)

    if not remaining:
        return None

    # Remaining nodes form at least one cycle. Walk forward from an arbitrary
    # remaining node (smallest id for determinism) until we revisit a node.
    start = min(remaining)
    path: list[str] = []
    seen: set[str] = set()
    current = start
    while current not in seen:
        seen.add(current)
        path.append(current)
        # pick smallest-dependent-id edge that stays inside `remaining`
        nxts = [n for n in adj[current] if n in remaining]
        current = min(nxts) if nxts else start

    # trim the prefix before the first occurrence of the repeated node
    first = path.index(current)
    cycle = path[first:] + [current]
    return cycle
