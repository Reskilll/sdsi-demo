"""Tests for parallel scheduling."""

from dag_scheduler.graph import JobNode
from dag_scheduler.scheduler import group_stages, schedule_parallel


def _jobs(*pairs) -> dict[str, JobNode]:
    return {n: JobNode(name=n, duration=d, depends_on=deps) for n, d, deps in pairs}


# ---------------------------------------------------------------------------
# M3 — group_stages
# ---------------------------------------------------------------------------

def test_group_stages_diamond():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 1, ["A"]),
        ("C", 1, ["A"]),
        ("D", 1, ["B", "C"]),
    )
    stages = group_stages(jobs, worker_limit=4)
    # Level 0: A, Level 1: B/C, Level 2: D
    assert stages == [["A"], ["B", "C"], ["D"]]


def test_group_stages_respects_worker_limit():
    jobs = _jobs(
        ("A", 2, []),
        ("B", 3, []),
        ("C", 1, []),
        ("D", 4, []),
        ("E", 2, []),
    )
    stages = group_stages(jobs, worker_limit=2)
    # All at level 0 but capped at 2 per wave
    assert len(stages[0]) == 2
    assert len(stages[1]) == 2
    assert len(stages[2]) == 1


def test_group_stages_single_worker():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 1, ["A"]),
        ("C", 1, ["B"]),
    )
    stages = group_stages(jobs, worker_limit=1)
    assert all(len(s) == 1 for s in stages)


# ---------------------------------------------------------------------------
# M3 — schedule_parallel (list-scheduler simulation)
# ---------------------------------------------------------------------------

def test_schedule_makespan():
    jobs = _jobs(
        ("A", 2, []),
        ("B", 3, []),
        ("C", 1, ["A", "B"]),
    )
    report = schedule_parallel(jobs, worker_limit=2)
    # A and B start together at t=0; A finishes at 2, B at 3.
    # C starts at 3 (waits for B) and finishes at 4.
    # makespan = 4.0
    assert report.makespan == 4.0
    assert report.worker_limit == 2


def test_schedule_timeline_order():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 1, []),
        ("C", 1, ["A", "B"]),
    )
    report = schedule_parallel(jobs, worker_limit=2)
    entry_jobs = sorted(e.job for e in report.schedule)
    assert entry_jobs == ["A", "B", "C"]


def test_schedule_no_workers():
    jobs = _jobs(
        ("X", 1, []),
        ("Y", 2, ["X"]),
    )
    # worker_limit defaults to 1 when we pass 0 via CLI; test explicit 1
    report = schedule_parallel(jobs, worker_limit=1)
    # Sequential makespan = 1 + 2 = 3
    assert report.makespan == 3.0


def test_schedule_with_deep_chain():
    jobs = _jobs(
        ("s1", 5, []),
        ("s2", 5, ["s1"]),
        ("s3", 5, ["s2"]),
        ("s4", 5, ["s3"]),
        ("s5", 5, ["s4"]),
    )
    report = schedule_parallel(jobs, worker_limit=4)
    # Linear chain — parallelism doesn't help
    assert report.makespan == 25.0


def test_schedule_large_worker_limit():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, []),
        ("C", 3, []),
        ("D", 4, []),
    )
    report = schedule_parallel(jobs, worker_limit=10)
    # All run in parallel: makespan = max duration = 4.0
    assert report.makespan == 4.0


# ---------------------------------------------------------------------------
# Bonus: schedule respects dependency constraints
# ---------------------------------------------------------------------------

def test_schedule_respects_dependencies():
    """Every job must start only after all its dependencies have finished."""
    jobs = _jobs(
        ("A", 5, []),
        ("B", 2, ["A"]),
        ("C", 3, ["A"]),
        ("D", 1, ["B", "C"]),
    )
    report = schedule_parallel(jobs, worker_limit=4)
    timeline = {se.job: (se.start, se.end) for se in report.schedule}

    # B and C must start >= A's end (5)
    assert timeline["B"][0] >= timeline["A"][1]
    assert timeline["C"][0] >= timeline["A"][1]
    # D must start >= max(B_end, C_end)
    assert timeline["D"][0] >= max(timeline["B"][1], timeline["C"][1])