"""Tests for M3 – Parallel stages and worker-limited scheduling."""

import pytest

from scheduler.graph import DAG
from scheduler.parallel import (
    estimated_makespan,
    parallel_schedule,
    parallel_stages,
)


def _build_fixture() -> DAG:
    """sample2.json — CI pipeline with LINT → TEST, BUILD_A, BUILD_B → E2E → DEPLOY."""
    return DAG.from_dicts([
        {"id": "LINT",    "duration": 1, "dependsOn": []},
        {"id": "TEST",    "duration": 4, "dependsOn": ["LINT"]},
        {"id": "BUILD_A", "duration": 6, "dependsOn": ["LINT"]},
        {"id": "BUILD_B", "duration": 6, "dependsOn": ["LINT"]},
        {"id": "E2E",     "duration": 5, "dependsOn": ["TEST", "BUILD_A", "BUILD_B"]},
        {"id": "DEPLOY",  "duration": 2, "dependsOn": ["E2E"]},
    ])


def test_parallel_stages_counts():
    dag = _build_fixture()
    stages = parallel_stages(dag)
    # Stage 0: LINT (only), Stage 1: TEST, BUILD_A, BUILD_B,
    # Stage 2: E2E, Stage 3: DEPLOY
    assert len(stages) == 4
    assert stages[0] == {"LINT"}
    assert stages[1] == {"TEST", "BUILD_A", "BUILD_B"}
    assert stages[2] == {"E2E"}
    assert stages[3] == {"DEPLOY"}


def test_parallel_stages_no_overlap():
    dag = _build_fixture()
    stages = parallel_stages(dag)
    seen = set()
    for s in stages:
        assert seen.isdisjoint(s), f"Job from stage {s} appeared in earlier stage"
        seen |= s
    assert seen == dag.job_ids


def test_worker_schedule_respects_limit():
    dag = _build_fixture()
    sched = parallel_schedule(dag, worker_limit=2)
    for slc in sched:
        assert len(slc) <= 2, f"Slice {slc} exceeded worker limit"


def test_worker_schedule_covers_all():
    dag = _build_fixture()
    sched = parallel_schedule(dag, worker_limit=1)
    flat = [j for slc in sched for j in slc]
    assert set(flat) == dag.job_ids


def test_worker_limit_zero_raises():
    dag = _build_fixture()
    with pytest.raises(ValueError, match="worker_limit"):
        parallel_schedule(dag, 0)


def test_estimated_makespan_unlimited():
    dag = _build_fixture()
    # Unlimited: stages = 4; max per stage: 1, 6, 5, 2 = 14
    ms = estimated_makespan(dag)
    assert ms == 14.0


def test_estimated_makespan_with_limit_1():
    dag = _build_fixture()
    # All serial: sum of all durations = 1+4+6+6+5+2 = 24
    ms = estimated_makespan(dag, worker_limit=1)
    assert ms == 24.0


def test_estimated_makespan_with_limit_3():
    dag = _build_fixture()
    # 3 workers can run TEST, BUILD_A, BUILD_B together → 4 stages of max durations
    ms = estimated_makespan(dag, worker_limit=3)
    assert ms == 14.0


def test_independent_all_parallel():
    dag = DAG.from_dicts([
        {"id": "A", "duration": 5, "dependsOn": []},
        {"id": "B", "duration": 3, "dependsOn": []},
        {"id": "C", "duration": 7, "dependsOn": []},
    ])
    stages = parallel_stages(dag)
    assert len(stages) == 1
    assert stages[0] == {"A", "B", "C"}


def test_linear_no_parallelism():
    dag = DAG.from_dicts([
        {"id": "A", "duration": 1, "dependsOn": []},
        {"id": "B", "duration": 1, "dependsOn": ["A"]},
        {"id": "C", "duration": 1, "dependsOn": ["B"]},
    ])
    stages = parallel_stages(dag)
    # Each stage has exactly one job
    assert all(len(s) == 1 for s in stages)