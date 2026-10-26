"""
Job Scheduler with DAG Dependency Resolution.

M1: Validate graph — detect cycles (report path) and missing dependencies.
M2: Valid execution order via topological sort.
M3: Parallel stages with configurable worker limit N.
M4: Critical path and minimum total completion time.
M5: Failure simulation — given a failed job, list every downstream skipped job.
"""

from collections import deque
import json


# ---------------------------------------------------------------------------
# M1 — Validate graph
# ---------------------------------------------------------------------------

def detect_cycles(jobs: list[dict]) -> list[str] | None:
    """Return a cycle path if one exists, otherwise None."""
    adj = {j["id"]: j.get("dependsOn", []) for j in jobs}

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {j["id"]: WHITE for j in jobs}
    parent = {}

    def dfs(u, path):
        color[u] = GRAY
        path.append(u)
        for v in adj.get(u, []):
            if color.get(v, WHITE) == GRAY:
                # Found a cycle — extract the loop portion
                cycle_start = path.index(v)
                return path[cycle_start:] + [v]
            if color.get(v, WHITE) == WHITE:
                parent[v] = u
                result = dfs(v, path)
                if result:
                    return result
        path.pop()
        color[u] = BLACK
        return None

    for job_id in adj:
        if color[job_id] == WHITE:
            cycle = dfs(job_id, [])
            if cycle:
                return cycle
    return None


def find_missing_dependencies(jobs: list[dict]) -> list[tuple[str, str]]:
    """Return (job_id, missing_dep) for every referenced dependency that
    does not exist in the job list."""
    all_ids = {j["id"] for j in jobs}
    missing = []
    for j in jobs:
        for dep in j.get("dependsOn", []):
            if dep not in all_ids:
                missing.append((j["id"], dep))
    return missing


def validate(jobs: list[dict]) -> dict:
    """Run both cycle and missing-dependency checks.  Return a report dict."""
    cycle = detect_cycles(jobs)
    missing = find_missing_dependencies(jobs)
    return {
        "valid": cycle is None and len(missing) == 0,
        "cycle": cycle,
        "missing_dependencies": missing,
    }


# ---------------------------------------------------------------------------
# M2 — Topological sort (Kahn's algorithm)
# ---------------------------------------------------------------------------

def topological_sort(jobs: list[dict]) -> list[str]:
    """Return a valid execution order as a list of job ids."""
    adj = {j["id"]: set(j.get("dependsOn", [])) for j in jobs}
    indeg = {j["id"]: 0 for j in jobs}
    for j in jobs:
        for dep in j.get("dependsOn", []):
            if dep in indeg:
                indeg[j["id"]] += 1

    queue = deque(uid for uid, deg in indeg.items() if deg == 0)
    result = []
    while queue:
        u = queue.popleft()
        result.append(u)
        # Find jobs that depend on u
        for j in jobs:
            if u in j.get("dependsOn", []):
                indeg[j["id"]] -= 1
                if indeg[j["id"]] == 0:
                    queue.append(j["id"])
    return result


# ---------------------------------------------------------------------------
# M3 — Parallel stages with worker limit N
# ---------------------------------------------------------------------------

def _job_map(jobs: list[dict]) -> dict:
    return {j["id"]: j for j in jobs}


def parallel_stages(jobs: list[dict], n_workers: int = 2) -> dict:
    """Group jobs into parallel stages, respecting the worker limit N.

    Returns a dict with the stage plan and the simulated timeline.
    """
    jmap = _job_map(jobs)

    # Compute "level" for each job = longest chain of dependencies before it
    adj = {j["id"]: set(j.get("dependsOn", [])) for j in jobs}
    indeg = {j["id"]: len(j.get("dependsOn", [])) for j in jobs}

    # Topological levels via BFS
    level = {}
    queue = deque()
    for j in jobs:
        if indeg[j["id"]] == 0:
            level[j["id"]] = 0
            queue.append(j["id"])

    while queue:
        u = queue.popleft()
        for j in jobs:
            if u in j.get("dependsOn", []):
                indeg[j["id"]] -= 1
                level[j["id"]] = max(level.get(j["id"], 0), level[u] + 1)
                if indeg[j["id"]] == 0:
                    queue.append(j["id"])

    # Group by level
    max_level = max(level.values()) if level else 0
    stages = [[] for _ in range(max_level + 1)]
    for jid, lvl in level.items():
        stages[lvl].append(jid)

    # Simulate execution with N workers
    timeline = []  # list of (time, event)
    finish_time = {}  # job_id → wall-clock finish time
    available_workers = n_workers
    pending = {jid for jid in level}  # not yet finished

    # Track which jobs are ready (all deps done)
    dep_map = {j["id"]: set(j.get("dependsOn", [])) for j in jobs}
    done = set()

    t = 0
    running = {}  # job_id → remaining duration

    while pending:
        # Check for newly ready jobs
        ready = []
        for jid in sorted(pending - set(running.keys())):
            if dep_map[jid].issubset(done):
                ready.append(jid)

        # Assign workers
        for jid in ready:
            if available_workers > 0:
                available_workers -= 1
                running[jid] = jmap[jid]["duration"]
                timeline.append((t, f"START {jid} (worker taken)"))

        if not running and not ready:
            break  # should not happen on valid DAG

        # Advance time to the next finish
        if running:
            next_finish = min(running.values())
            t += next_finish

            # Finish all jobs that complete at this time
            finished_now = []
            for jid, rem in list(running.items()):
                rem -= next_finish
                if rem == 0:
                    finished_now.append(jid)
                    del running[jid]
                    available_workers += 1
                else:
                    running[jid] = rem

            for jid in finished_now:
                done.add(jid)
                pending.discard(jid)
                finish_time[jid] = t
                timeline.append((t, f"FINISH {jid} (worker freed)"))

    makespan = t
    return {
        "stages": {f"stage_{i}": s for i, s in enumerate(stages)},
        "timeline": timeline,
        "finish_times": finish_time,
        "makespan": makespan,
        "workers_used": n_workers,
    }


# ---------------------------------------------------------------------------
# M4 — Critical path
# ---------------------------------------------------------------------------

def critical_path(jobs: list[dict]) -> dict:
    """Compute the critical path and minimum total completion time.

    Earliest-start / earliest-finish forward pass, then identify the path(s)
    whose total duration equals the longest chain from any source to any sink.
    """
    jmap = _job_map(jobs)
    topo = topological_sort(jobs)

    # Forward pass: ES, EF
    es = {}  # earliest start
    ef = {}  # earliest finish
    for jid in topo:
        preds = jmap[jid].get("dependsOn", [])
        es[jid] = max((ef[p] for p in preds if p in ef), default=0)
        ef[jid] = es[jid] + jmap[jid]["duration"]

    min_time = max(ef.values()) if ef else 0

    # Backward pass: LS, LF (for identifying critical jobs)
    lf = {}
    ls = {}
    for jid in reversed(topo):
        succs = [j["id"] for j in jobs if jid in j.get("dependsOn", [])]
        lf[jid] = min((ls[s] for s in succs if s in ls), default=min_time)
        ls[jid] = lf[jid] - jmap[jid]["duration"]

    # Critical jobs: slack = 0
    critical_jobs = [jid for jid in topo if es[jid] == ls[jid]]

    # Build the critical path (greedy: follow the chain)
    path = []
    if critical_jobs:
        current = topo[0]
        while current:
            path.append(current)
            succs = [j["id"] for j in jobs if current in j.get("dependsOn", [])]
            current = next((s for s in succs if s in critical_jobs), None)

    return {
        "minimum_completion_time": min_time,
        "critical_jobs": critical_jobs,
        "critical_path": path,
        "earliest_start": es,
        "earliest_finish": ef,
    }


# ---------------------------------------------------------------------------
# M5 — Failure simulation
# ---------------------------------------------------------------------------

def simulate_failure(jobs: list[dict], failed_job_id: str) -> dict:
    """Given a failed job, list every downstream job that would be skipped."""
    jmap = _job_map(jobs)

    # BFS from failed_job to find all transitive dependents
    dependents = set()
    queue = deque([failed_job_id])
    while queue:
        u = queue.popleft()
        for j in jobs:
            if u in j.get("dependsOn", []) and j["id"] not in dependents:
                dependents.add(j["id"])
                queue.append(j["id"])

    # Jobs that still run (not downstream of failure)
    still_run = sorted(set(jmap.keys()) - dependents - {failed_job_id})

    return {
        "failed_job": failed_job_id,
        "skipped_jobs": sorted(dependents),
        "skipped_count": len(dependents),
        "still_run": still_run,
        "total_jobs": len(jobs),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(jobs: list[dict], n_workers: int = 2, fail_job: str | None = None) -> dict:
    """Run the full pipeline and return a combined report."""
    report = {}

    # M1
    report["validation"] = validate(jobs)

    if not report["validation"]["valid"]:
        return report  # stop early on invalid graph

    # M2
    report["execution_order"] = topological_sort(jobs)

    # M3
    report["parallel_plan"] = parallel_stages(jobs, n_workers)

    # M4
    report["critical_path"] = critical_path(jobs)

    # M5 (optional)
    if fail_job:
        report["failure_simulation"] = simulate_failure(jobs, fail_job)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Default to sample input if no file given
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_jobs.json"
    with open(path) as f:
        data = json.load(f)

    result = run(data["jobs"], n_workers=3, fail_job=None)

    print("=" * 60)
    print("JOB SCHEDULER REPORT")
    print("=" * 60)

    v = result["validation"]
    print(f"\n[M1] VALIDATION — valid: {v['valid']}")
    if v["cycle"]:
        print(f"  Cycle detected: {' → '.join(v['cycle'])}")
    if v["missing_dependencies"]:
        for job, dep in v["missing_dependencies"]:
            print(f"  Missing dependency: {job} depends on {dep} (not found)")

    if not v["valid"]:
        sys.exit(1)

    print(f"\n[M2] EXECUTION ORDER: {' → '.join(result['execution_order'])}")

    pp = result["parallel_plan"]
    print(f"\n[M3] PARALLEL STAGES ({pp['workers_used']} workers):")
    for stage, job_ids in pp["stages"].items():
        print(f"  {stage}: {job_ids}")
    print(f"  Makespan: {pp['makespan']} time units")
    for ts, event in pp["timeline"]:
        print(f"    t={ts}: {event}")

    cp = result["critical_path"]
    print(f"\n[M4] CRITICAL PATH:")
    print(f"  Minimum completion time: {cp['minimum_completion_time']}")
    print(f"  Critical path: {' → '.join(cp['critical_path'])}")

    if "failure_simulation" in result:
        fs = result["failure_simulation"]
        print(f"\n[M5] FAILURE SIMULATION (failed: {fs['failed_job']}):")
        print(f"  Skipped ({fs['skipped_count']}): {fs['skipped_jobs']}")
        print(f"  Still run: {fs['still_run']}")