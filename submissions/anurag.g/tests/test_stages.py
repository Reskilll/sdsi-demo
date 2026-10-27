"""Test M3: Parallel stages with worker limit."""

import pytest
from scheduler.models import load_graph
from scheduler.stages import compute_stages, WorkerLimitError


def test_stages_single_worker():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]})
    stages = compute_stages(graph, workers=1)
    # With 1 worker: A alone, then B alone, then C alone, then D alone (or B/C swapped)
    # But B and C are on same level, so they form 1 stage with 2 waves
    assert len(stages) == 3  # level 0 (A), level 1 (B,C), level 2 (D)
    # Each wave should have exactly 1 job
    for stage in stages:
        for wave in stage:
            assert len(wave) == 1


def test_stages_unlimited_workers():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]})
    stages = compute_stages(graph, workers=10)
    # Level 0: [A]
    # Level 1: [B, C] in one wave
    # Level 2: [D]
    assert len(stages) == 3
    assert len(stages[1]) == 1
    assert len(stages[1][0]) == 2
    assert set(stages[1][0]) == {"B", "C"}


def test_stages_worker_limit_batching():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 1, "dependsOn": ["A"]},
        {"id": "C", "duration": 1, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["A"]},
        {"id": "E", "duration": 1, "dependsOn": ["A"]},
    ]})
    stages = compute_stages(graph, workers=2)
    assert len(stages) == 2  # level 0: A, level 1: B,C,D,E
    # Level 1 has 4 jobs, workers=2 → 2 waves of 2
    assert len(stages[1]) == 2
    assert len(stages[1][0]) == 2
    assert len(stages[1][1]) == 2


def test_stages_chain():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 3, "dependsOn": ["B"]},
    ]})
    stages = compute_stages(graph, workers=5)
    # Each is on its own level
    assert len(stages) == 3


def test_stages_single_job():
    graph = load_graph({"jobs": [{"id": "X", "duration": 1}]})
    stages = compute_stages(graph, workers=1)
    assert len(stages) == 1
    assert stages[0] == [["X"]]


def test_stages_empty():
    graph = load_graph({"jobs": []})
    stages = compute_stages(graph, workers=1)
    assert stages == []


def test_worker_limit_zero_raises():
    graph = load_graph({"jobs": [{"id": "A", "duration": 1}]})
    with pytest.raises(WorkerLimitError):
        compute_stages(graph, workers=0)


def test_worker_limit_negative_raises():
    graph = load_graph({"jobs": [{"id": "A", "duration": 1}]})
    with pytest.raises(WorkerLimitError):
        compute_stages(graph, workers=-1)