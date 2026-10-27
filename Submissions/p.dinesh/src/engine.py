"""Core DAG engine: validation, topological sort, staging, critical path, failure simulation."""

from collections import deque
from dataclasses import dataclass
from typing import Optional

from .models import (
    JobSpec,
    ExecutionPlan,
    Stage,
    ValidationResult,
    ScheduledJob,
    Schedule,
    SlackInfo,
)


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _build_adjacency(jobs: list[JobSpec]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Return (adjacency list, in-degree map)."""
    adj: dict[str, list[str]] = {j.id: [] for j in jobs}
    indeg: dict[str, int] = {j.id: 0 for j in jobs}

    for job in jobs:
        for dep in job.dependsOn:
            if dep in adj:
                adj[dep].append(job.id)
                indeg[job.id] += 1
            # missing dep handled by validate()
    return adj, indeg


# ---------------------------------------------------------------------------
# M1: Validate
# ---------------------------------------------------------------------------

def validate(jobs: list[JobSpec]) -> ValidationResult:
    """Validate the job graph.

    Checks:
    - No duplicate job IDs
    - All dependencies exist as declared jobs
    - No cycles (DFS-based detection with path reporting)
    """
    result = ValidationResult(valid=True)

    # -- duplicate IDs --------------------------------------------------------
    seen: dict[str, int] = {}
    for i, job in enumerate(jobs):
        if job.id in seen:
            result.duplicate_ids.append(job.id)
            result.errors.append(f"Duplicate job ID '{job.id}' at index {i} (first at {seen[job.id]})")
            result.valid = False
        seen[job.id] = i

    if result.duplicate_ids:
        return result  # bail early — can't reason about identity

    ids = {j.id for j in jobs}

    # -- missing dependencies -------------------------------------------------
    for job in jobs:
        for dep in job.dependsOn:
            if dep not in ids:
                result.missing_dependencies.append((job.id, dep))
                result.errors.append(f"Job '{job.id}' depends on '{dep}', which does not exist")
                result.valid = False

    # -- cycle detection (DFS) ------------------------------------------------
    # Standard 3-colour DFS: 0=white, 1=gray (in current path), 2=black (done)
    colour: dict[str, int] = {j.id: 0 for j in jobs}
    parent: dict[str, Optional[str]] = {j.id: None for j in jobs}
    cycle_nodes: list[str] = []

    def dfs(u: str) -> bool:
        """Return True if a cycle was found."""
        colour[u] = 1  # gray — visiting
        for v in adj[u]:
            if colour[v] == 1:
                # Found a back-edge — extract the cycle path
                cycle = [v, u]
                cur = u
                while parent[cur] is not None and parent[cur] != v:
                    cur = parent[cur]
                    cycle.append(cur)
                cycle.append(v)
                cycle.reverse()
                cycle_nodes.extend(cycle)
                return True
            if colour[v] == 0:
                parent[v] = u
                if dfs(v):
                    return True
        colour[u] = 2  # black — finished
        return False

    adj, _ = _build_adjacency(jobs)

    for node in adj:
        if colour[node] == 0:
            if dfs(node):
                result.cycle_path = cycle_nodes
                result.valid = False
                result.errors.append(
                    f"Cycle detected: {' → '.join(cycle_nodes)}"
                )
                break

    return result


# ---------------------------------------------------------------------------
# M2: Topological sort (Kahn's algorithm)
# ---------------------------------------------------------------------------

def topological_sort(jobs: list[JobSpec]) -> list[str]:
    """Return a valid execution order using Kahn's algorithm (BFS).

    Raises ValueError if the graph is not a valid DAG — call `validate` first.
    """
    adj, indeg = _build_adjacency(jobs)

    q: deque[str] = deque(n for n, d in indeg.items() if d == 0)
    order: list[str] = []

    while q:
        u = q.popleft()
        order.append(u)
        for v in adj.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    if len(order) != len(jobs):
        raise ValueError("Graph contains a cycle — cannot produce topological order")

    return order


# ---------------------------------------------------------------------------
# M3: Group into parallel stages with worker limit N
# ---------------------------------------------------------------------------

def plan_stages(
    jobs: list[JobSpec],
    worker_limit: int,
) -> list[Stage]:
    """Partition jobs into parallel execution stages respecting dependencies.

    Stages are formed by level-scheduling: jobs whose dependencies are all
    satisfied go into the current stage.  At most *worker_limit* jobs run
    concurrently per stage.  If a stage holds more jobs than the limit, the
    excess spill into the next stage (with no new dependencies).

    Returns a list of Stage objects, each holding the job IDs that can run
    together and their cumulative start/end times.
    """
    if worker_limit < 1:
        raise ValueError(f"worker_limit must be >= 1, got {worker_limit}")

    id_to_dur = {j.id: j.duration for j in jobs}
    adj, indeg = _build_adjacency(jobs)

    # copy of in-degree for mutable tracking
    remaining: dict[str, int] = dict(indeg)
    ready: deque[str] = deque(n for n, d in remaining.items() if d == 0)

    stages: list[Stage] = []
    current_time = 0

    while ready:
        # Select up to worker_limit jobs for this stage
        stage_jobs: list[str] = []
        for _ in range(min(worker_limit, len(ready))):
            stage_jobs.append(ready.popleft())

        # Jobs left that couldn't be scheduled now stay in ready
        # and will go into the next stage

        # Compute stage duration = max of its jobs
        stage_duration = max(id_to_dur[j] for j in stage_jobs) if stage_jobs else 0

        stage = Stage(
            jobs=stage_jobs,
            start_time=current_time,
            end_time=current_time + stage_duration,
        )
        stages.append(stage)

        # "Complete" these jobs — decrement dependents' in-degree
        for job in stage_jobs:
            for child in adj.get(job, []):
                remaining[child] -= 1
                if remaining[child] == 0:
                    ready.append(child)

        current_time += stage_duration

    return stages


# ---------------------------------------------------------------------------
# M4: Critical path & minimum completion time
# ---------------------------------------------------------------------------

@dataclass
class CriticalPathResult:
    path: list[str]
    """Longest (critical) path from any source to any sink."""

    total_time: int
    """Minimum total completion time (sum of durations along critical path)."""


def critical_path(jobs: list[JobSpec]) -> CriticalPathResult:
    """Compute the critical path and minimum total completion time.

    Uses longest-path-in-DAG via topological ordering (O(V+E)).
    """
    if not jobs:
        return CriticalPathResult(path=[], total_time=0)

    id_to_dur = {j.id: j.duration for j in jobs}

    # Topological order
    order = topological_sort(jobs)

    # Earliest start time (EST) and predecessor tracking
    est: dict[str, int] = {j.id: 0 for j in jobs}
    pred: dict[str, Optional[str]] = {j.id: None for j in jobs}

    adj, _ = _build_adjacency(jobs)

    for u in order:
        for v in adj.get(u, []):
            candidate = est[u] + id_to_dur[u]
            if candidate > est[v]:
                est[v] = candidate
                pred[v] = u

    # Find the sink with the largest EST + its own duration
    sink = max(jobs, key=lambda j: est[j.id] + j.duration)
    total = est[sink.id] + sink.duration

    # Reconstruct the path backwards
    path: list[str] = []
    cur: Optional[str] = sink.id
    while cur is not None:
        path.append(cur)
        cur = pred[cur]
    path.reverse()

    return CriticalPathResult(path=path, total_time=total)


# ---------------------------------------------------------------------------
# M5: Failure simulation
# ---------------------------------------------------------------------------

def downstream_of(jobs: list[JobSpec], failed_id: str) -> list[str]:
    """Return every job transitively downstream of *failed_id*.

    If *failed_id* does not exist, return an empty list.
    """
    return downstream_of_many(jobs, [failed_id])


def downstream_of_many(jobs: list[JobSpec], failed_ids: list[str]) -> list[str]:
    """Return every job transitively downstream of *any* of *failed_ids*.

    The union of BFS reachability from each failed node, emitted in
    first-encounter order.  Non-existent failed IDs are ignored.
    """
    adj, _ = _build_adjacency(jobs)

    visited: set[str] = set()
    q: deque[str] = deque()
    for fid in failed_ids:
        if fid in adj and fid not in visited:
            visited.add(fid)
            q.append(fid)

    result: list[str] = []
    while q:
        u = q.popleft()
        for v in adj.get(u, []):
            if v not in visited:
                visited.add(v)
                result.append(v)
                q.append(v)

    return result


# ---------------------------------------------------------------------------
# Bonus: Concrete list scheduling (worker allocation)
# ---------------------------------------------------------------------------

def list_schedule(
    jobs: list[JobSpec],
    worker_limit: int,
) -> Schedule:
    """Build a concrete parallel schedule assigning each job to a worker.

    Greedy *list scheduling* on the CP-sorted job list (a classic 2-approx for
    P | prec | C_max): jobs are released as soon as all their dependencies
    finish and packed onto the first free worker.  This is more faithful than
    stage scheduling — a worker whose job finishes early picks up the next
    ready job immediately rather than waiting for the whole stage to drain.

    Returns a Schedule holding every job's (start, finish, worker) and the
    makespan.  Raises ValueError for worker_limit < 1.
    """
    if worker_limit < 1:
        raise ValueError(f"worker_limit must be >= 1, got {worker_limit}")

    id_to_dur = {j.id: j.duration for j in jobs}
    adj, indeg = _build_adjacency(jobs)
    remaining = dict(indeg)

    # Priority: longest-duration-first, then topological order for determinism.
    topo = topological_sort(jobs)
    topo_rank = {jid: i for i, jid in enumerate(topo)}

    worker_busy_until = [0] * worker_limit  # time each worker is free
    finish_times: dict[str, int] = {}
    scheduled: list[ScheduledJob] = []
    done: set[str] = set()

    while len(done) < len(jobs):
        # Ready = all dependencies satisfied, not yet scheduled.
        ready = [jid for jid, d in remaining.items() if d == 0 and jid not in done]
        ready.sort(key=lambda jid: (-id_to_dur[jid], topo_rank[jid]))
        if not ready:
            raise ValueError("Deadlock: no ready jobs but graph not fully scheduled")

        for jid in ready:
            release = max((finish_times[d] for d in _deps_of(jobs, jid)), default=0)

            w, wfree = min(
                enumerate(worker_busy_until),
                key=lambda pair: (max(pair[1], release), pair[0]),
            )
            start = max(wfree, release)
            finish = start + id_to_dur[jid]
            worker_busy_until[w] = finish
            finish_times[jid] = finish
            scheduled.append(ScheduledJob(id=jid, start=start, finish=finish, worker=w))
            done.add(jid)

            for child in adj.get(jid, []):
                remaining[child] -= 1

    makespan = max(finish_times.values(), default=0)
    scheduled.sort(key=lambda s: (s.start, s.worker))
    return Schedule(jobs=scheduled, makespan=makespan, worker_count=worker_limit)


def _deps_of(jobs: list[JobSpec], job_id: str) -> list[str]:
    """Return the direct dependencies of *job_id* (lookup helper)."""
    for j in jobs:
        if j.id == job_id:
            return j.dependsOn
    return []


# ---------------------------------------------------------------------------
# Bonus: Slack / float analysis (criticality per node)
# ---------------------------------------------------------------------------

def slack_analysis(jobs: list[JobSpec]) -> list[SlackInfo]:
    """Compute total float (slack) for every job via forward/backward pass.

    Total float = latest_start - earliest_start.  Jobs with zero float lie on
    *some* critical path.  Complements ``critical_path`` (a single path) by
    flagging *every* critical job, including ties.
    """
    id_to_dur = {j.id: j.duration for j in jobs}
    order = topological_sort(jobs)
    adj, _ = _build_adjacency(jobs)

    # Forward pass: earliest start/finish
    es: dict[str, int] = {j.id: 0 for j in jobs}
    for u in order:
        for v in adj.get(u, []):
            es[v] = max(es[v], es[u] + id_to_dur[u])
    ef = {j.id: es[j.id] + id_to_dur[j.id] for j in jobs}

    # Backward pass: latest finish/start
    makespan = max(ef.values(), default=0)
    lf: dict[str, int] = {j.id: makespan for j in jobs}
    for u in reversed(order):
        for v in adj.get(u, []):
            lf[u] = min(lf[u], lf[v] - id_to_dur[v])
    ls = {j.id: lf[j.id] - id_to_dur[j.id] for j in jobs}

    return [
        SlackInfo(
            id=j.id,
            earliest_start=es[j.id],
            earliest_finish=ef[j.id],
            latest_start=ls[j.id],
            latest_finish=lf[j.id],
            total_slack=ls[j.id] - es[j.id],
        )
        for j in jobs
    ]


# ---------------------------------------------------------------------------
# Bonus: Graphviz DOT output
# ---------------------------------------------------------------------------

def to_dot(
    jobs: list[JobSpec],
    *,
    critical_path_nodes: Optional[list[str]] = None,
    failed_node: Optional[str] = None,
    skipped_nodes: Optional[list[str]] = None,
) -> str:
    """Generate a Graphviz DOT representation of the DAG.

    Optionally highlights the critical path (bold red) and skipped nodes
    (dashed, gray) from a failure simulation.
    """
    lines: list[str] = [
        "digraph DAG {",
        "  rankdir=LR;",
        "  node [shape=box, style=rounded, fontname=\"Helvetica\"];",
    ]

    id_to_dur = {j.id: j.duration for j in jobs}
    cp_set = set(critical_path_nodes or [])
    skip_set = set(skipped_nodes or [])
    adj, _ = _build_adjacency(jobs)

    for job in jobs:
        label = f"{job.id} ({job.duration}s)"

        attrs = []
        if job.id in cp_set:
            attrs.append('color=red')
            attrs.append('penwidth=2')
        if job.id in skip_set:
            attrs.append('style="filled,dashed"')
            attrs.append('fillcolor="#eeeeee"')
            attrs.append('fontcolor="#999999"')
        if job.id == failed_node:
            attrs.append('style=filled')
            attrs.append('fillcolor="#ffcccc"')
            attrs.append('penwidth=2')

        attr_str = ", ".join(attrs)
        lines.append(f'  "{job.id}" [label="{label}"{", " + attr_str if attr_str else ""}];')

    # Edges
    for job in jobs:
        for dep in job.dependsOn:
            style = ""
            if job.id in skip_set:
                style = ' [style=dashed, color="#cccccc"]'
            elif dep in cp_set and job.id in cp_set:
                style = ' [color=red, penwidth=2]'
            lines.append(f'  "{dep}" -> "{job.id}"{style};')

    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestrator — ties all modules together
# ---------------------------------------------------------------------------

def build_plan(
    jobs: list[JobSpec],
    worker_limit: int = 4,
    *,
    failed_job: Optional[str] = None,
    failed_jobs: Optional[list[str]] = None,
) -> ExecutionPlan:
    """Run the full pipeline: validate → sort → stage → critical path → failure.

    Returns an ExecutionPlan dataclass with all results.  ``failed_jobs``
    (plural) accepts multiple failing jobs; ``failed_job`` is kept for
    single-failure convenience.  When both are given, they are merged.
    """
    if worker_limit < 1:
        raise ValueError(f"worker_limit must be >= 1, got {worker_limit}")

    # Normalise failure inputs to a single ordered, de-duplicated list.
    fails: list[str] = []
    if failed_jobs:
        fails.extend(failed_jobs)
    if failed_job:
        fails.append(failed_job)
    fails = list(dict.fromkeys(fails))  # de-duplicate, preserving order

    validation = validate(jobs)
    if not validation.valid:
        return ExecutionPlan(
            jobs=jobs,
            worker_limit=worker_limit,
            valid=False,
            validation=validation,
            failed_job=failed_job,
            failed_jobs=fails,
        )

    topo_order = topological_sort(jobs)
    stages = plan_stages(jobs, worker_limit)
    cp = critical_path(jobs)
    skipped = downstream_of_many(jobs, fails) if fails else None
    sched = list_schedule(jobs, worker_limit)
    slack = slack_analysis(jobs)

    return ExecutionPlan(
        jobs=jobs,
        worker_limit=worker_limit,
        valid=True,
        validation=validation,
        topological_order=topo_order,
        stages=stages,
        critical_path=cp.path,
        critical_path_time=cp.total_time,
        failed_job=failed_job,
        failed_jobs=fails,
        skipped_jobs=skipped,
        schedule=sched,
        slack=slack,
    )