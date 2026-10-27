"""Tests for M2 – Topological sort."""

from scheduler.graph import DAG
from scheduler.topo import topological_sort, topological_sort_dfs


def _sample() -> DAG:
    return DAG.from_dicts([
        {"id": "A", "duration": 3, "dependsOn": []},
        {"id": "B", "duration": 5, "dependsOn": ["A"]},
        {"id": "C", "duration": 2, "dependsOn": ["A"]},
        {"id": "D", "duration": 4, "dependsOn": ["B", "C"]},
        {"id": "E", "duration": 1, "dependsOn": ["D"]},
    ])


def test_topological_order_covers_all_jobs():
    dag = _sample()
    order = topological_sort(dag)
    assert set(order) == dag.job_ids
    assert len(order) == len(dag)


def test_topological_order_respects_dependencies():
    dag = _sample()
    order = topological_sort(dag)
    pos = {jid: i for i, jid in enumerate(order)}
    for job in dag.jobs.values():
        for dep in job.depends_on:
            assert pos[dep] < pos[job.id], f"{dep} must come before {job.id}"


def test_topological_sort_dfs_also_valid():
    dag = _sample()
    order = topological_sort_dfs(dag)
    pos = {jid: i for i, jid in enumerate(order)}
    for job in dag.jobs.values():
        for dep in job.depends_on:
            assert pos[dep] < pos[job.id]


def test_linear_chain():
    dag = DAG.from_dicts([
        {"id": "1", "duration": 1, "dependsOn": []},
        {"id": "2", "duration": 1, "dependsOn": ["1"]},
        {"id": "3", "duration": 1, "dependsOn": ["2"]},
    ])
    assert topological_sort(dag) == ["1", "2", "3"]


def test_independent_jobs():
    dag = DAG.from_dicts([
        {"id": "C", "duration": 1, "dependsOn": []},
        {"id": "A", "duration": 1, "dependsOn": []},
        {"id": "B", "duration": 1, "dependsOn": []},
    ])
    # All independent — any order is valid, but Kahn gives sorted order
    assert topological_sort(dag) == ["A", "B", "C"]


def test_single_job():
    dag = DAG.from_dicts([{"id": "X", "duration": 5, "dependsOn": []}])
    assert topological_sort(dag) == ["X"]


def test_zero_duration_jobs():
    dag = DAG.from_dicts([
        {"id": "A", "duration": 0, "dependsOn": []},
        {"id": "B", "duration": 0, "dependsOn": ["A"]},
    ])
    assert topological_sort(dag) == ["A", "B"]