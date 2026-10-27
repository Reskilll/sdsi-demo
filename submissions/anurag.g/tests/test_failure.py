"""Test M5: Failure simulation — downstream skipped jobs."""

import pytest
from scheduler.models import load_graph
from scheduler.failure import simulate_failure


def test_failure_root_drops_all_downstream():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]})
    result = simulate_failure(graph, "A")
    assert result.failed_job == "A"
    assert set(result.skipped_jobs) == {"B", "C", "D"}
    assert result.unaffected_jobs == []


def test_failure_mid_job():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]})
    result = simulate_failure(graph, "B")
    assert set(result.skipped_jobs) == {"D"}
    assert set(result.unaffected_jobs) == {"A", "C"}


def test_failure_leaf_no_skipped():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
    ]})
    result = simulate_failure(graph, "B")
    assert result.skipped_jobs == []
    assert set(result.unaffected_jobs) == {"A"}


def test_failure_disconnected():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 2},
        {"id": "B", "duration": 3},
    ]})
    result = simulate_failure(graph, "A")
    assert result.skipped_jobs == []
    assert result.unaffected_jobs == ["B"]


def test_failure_unknown_job_raises():
    graph = load_graph({"jobs": [{"id": "A", "duration": 1}]})
    with pytest.raises(ValueError, match="Unknown job"):
        simulate_failure(graph, "Z")


def test_failure_chain():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 3, "dependsOn": ["B"]},
        {"id": "D", "duration": 4, "dependsOn": ["C"]},
    ]})
    result = simulate_failure(graph, "B")
    assert set(result.skipped_jobs) == {"C", "D"}
    assert result.unaffected_jobs == ["A"]


def test_failure_only_job():
    graph = load_graph({"jobs": [{"id": "X", "duration": 1}]})
    result = simulate_failure(graph, "X")
    assert result.skipped_jobs == []
    assert result.unaffected_jobs == []