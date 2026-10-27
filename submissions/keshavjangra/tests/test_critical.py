"""Tests for M4 – Critical path and minimum completion time."""

from scheduler.graph import DAG
from scheduler.critical import critical_path, min_completion_time, job_schedule_times


def test_critical_path_sample1():
    """A(3) → B(5) ──→ D(4) → E(1).  C(2) ─┘
       Longest chain: A→B→D→E = 3+5+4+1 = 13
       A→C→D→E = 3+2+4+1 = 10
    """
    dag = DAG.from_dicts([
        {"id": "A", "duration": 3, "dependsOn": []},
        {"id": "B", "duration": 5, "dependsOn": ["A"]},
        {"id": "C", "duration": 2, "dependsOn": ["A"]},
        {"id": "D", "duration": 4, "dependsOn": ["B", "C"]},
        {"id": "E", "duration": 1, "dependsOn": ["D"]},
    ])
    path, total = critical_path(dag)
    assert path == ["A", "B", "D", "E"]
    assert total == 13.0
    assert min_completion_time(dag) == 13.0


def test_critical_path_sample2():
    """LINT(1) → BUILD_A(6)/BUILD_B(6)/TEST(4) → E2E(5) → DEPLOY(2)
       Longest: LINT → BUILD_A → E2E → DEPLOY = 1+6+5+2 = 14
    """
    dag = DAG.from_dicts([
        {"id": "LINT",    "duration": 1, "dependsOn": []},
        {"id": "TEST",    "duration": 4, "dependsOn": ["LINT"]},
        {"id": "BUILD_A", "duration": 6, "dependsOn": ["LINT"]},
        {"id": "BUILD_B", "duration": 6, "dependsOn": ["LINT"]},
        {"id": "E2E",     "duration": 5, "dependsOn": ["TEST", "BUILD_A", "BUILD_B"]},
        {"id": "DEPLOY",  "duration": 2, "dependsOn": ["E2E"]},
    ])
    path, total = critical_path(dag)
    assert path in (
        ["LINT", "BUILD_A", "E2E", "DEPLOY"],
        ["LINT", "BUILD_B", "E2E", "DEPLOY"],
    )
    assert total == 14.0


def test_single_node():
    dag = DAG.from_dicts([{"id": "A", "duration": 42, "dependsOn": []}])
    path, total = critical_path(dag)
    assert path == ["A"]
    assert total == 42.0


def test_independent_jobs():
    dag = DAG.from_dicts([
        {"id": "A", "duration": 10, "dependsOn": []},
        {"id": "B", "duration": 3,  "dependsOn": []},
        {"id": "C", "duration": 7,  "dependsOn": []},
    ])
    path, total = critical_path(dag)
    assert path == ["A"]
    assert total == 10.0


def test_diamond():
    """X → A → B, C.  B and C are both leaves.  Critical = X→A→B = 3."""
    dag = DAG.from_dicts([
        {"id": "X", "duration": 1, "dependsOn": []},
        {"id": "A", "duration": 1, "dependsOn": ["X"]},
        {"id": "B", "duration": 1, "dependsOn": ["A"]},
        {"id": "C", "duration": 1, "dependsOn": ["A"]},
    ])
    path, total = critical_path(dag)
    assert total == 3.0
    assert path in (["X", "A", "B"], ["X", "A", "C"])


def test_empty_dag():
    dag = DAG.from_dicts([])
    path, total = critical_path(dag)
    assert path == []
    assert total == 0.0


def test_job_schedule_times():
    dag = DAG.from_dicts([
        {"id": "A", "duration": 5, "dependsOn": []},
        {"id": "B", "duration": 3, "dependsOn": ["A"]},
        {"id": "C", "duration": 2, "dependsOn": ["A"]},
    ])
    times = job_schedule_times(dag)
    assert times["A"] == (0.0, 5.0)
    assert times["B"] == (5.0, 8.0)
    assert times["C"] == (5.0, 7.0)