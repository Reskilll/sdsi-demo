"""Test M4: Critical path and minimum completion time."""

import pytest
from scheduler.models import load_graph
from scheduler.critical_path import compute_critical_path


def test_critical_path_sample():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]})
    result = compute_critical_path(graph)
    # A(3) → C(4) → D(1) = 8 (longer than A → B → D = 6)
    assert result.critical_path == ["A", "C", "D"]
    assert result.critical_path_duration == 8.0
    assert result.min_completion_time == 8.0


def test_critical_path_chain():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 3, "dependsOn": ["B"]},
        {"id": "D", "duration": 4, "dependsOn": ["C"]},
    ]})
    result = compute_critical_path(graph)
    assert result.critical_path == ["A", "B", "C", "D"]
    assert result.critical_path_duration == 10.0
    assert result.min_completion_time == 10.0


def test_critical_path_disconnected():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 5},
        {"id": "B", "duration": 3},
        {"id": "C", "duration": 2, "dependsOn": ["A"]},
    ]})
    result = compute_critical_path(graph)
    # A(5) → C(2) = 7 ; B(3)
    assert result.min_completion_time == 7.0
    assert result.critical_path == ["A", "C"]


def test_critical_path_single_job():
    graph = load_graph({"jobs": [{"id": "X", "duration": 42}]})
    result = compute_critical_path(graph)
    assert result.critical_path == ["X"]
    assert result.critical_path_duration == 42.0
    assert result.min_completion_time == 42.0


def test_critical_path_empty():
    graph = load_graph({"jobs": []})
    result = compute_critical_path(graph)
    assert result.critical_path == []
    assert result.min_completion_time == 0.0


def test_critical_path_float_durations():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1.5},
        {"id": "B", "duration": 2.3, "dependsOn": ["A"]},
        {"id": "C", "duration": 0.7, "dependsOn": ["A"]},
        {"id": "D", "duration": 5.1, "dependsOn": ["B", "C"]},
    ]})
    result = compute_critical_path(graph)
    # A → B → D = 1.5 + 2.3 + 5.1 = 8.9
    assert result.critical_path == ["A", "B", "D"]
    assert result.critical_path_duration == pytest.approx(8.9)
    assert result.min_completion_time == pytest.approx(8.9)