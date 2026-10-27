"""Test M2: Topological sort."""

import pytest
from scheduler.models import load_graph
from scheduler.topo import topological_sort


def test_topological_sort_simple():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]})
    order = topological_sort(graph)
    # A must come before B and C; B and C before D
    idx = {j: i for i, j in enumerate(order)}
    assert idx["A"] < idx["B"]
    assert idx["A"] < idx["C"]
    assert idx["B"] < idx["D"]
    assert idx["C"] < idx["D"]
    assert len(order) == 4


def test_topological_sort_chain():
    graph = load_graph({"jobs": [
        {"id": "E", "duration": 5, "dependsOn": ["D"]},
        {"id": "D", "duration": 4, "dependsOn": ["C"]},
        {"id": "C", "duration": 3, "dependsOn": ["B"]},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "A", "duration": 1},
    ]})
    order = topological_sort(graph)
    assert order == ["A", "B", "C", "D", "E"]


def test_topological_sort_disconnected():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 2},
        {"id": "B", "duration": 3},
        {"id": "C", "duration": 1, "dependsOn": ["A"]},
        {"id": "D", "duration": 4},
    ]})
    order = topological_sort(graph)
    idx = {j: i for i, j in enumerate(order)}
    assert idx["A"] < idx["C"]
    assert len(order) == 4
    # All jobs present
    assert set(order) == {"A", "B", "C", "D"}


def test_topological_sort_single_job():
    graph = load_graph({"jobs": [{"id": "X", "duration": 1}]})
    order = topological_sort(graph)
    assert order == ["X"]


def test_topological_sort_empty():
    graph = load_graph({"jobs": []})
    order = topological_sort(graph)
    assert order == []


def test_topological_sort_cycle_raises():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1, "dependsOn": ["B"]},
        {"id": "B", "duration": 1, "dependsOn": ["A"]},
    ]})
    with pytest.raises(ValueError, match="Cycle"):
        topological_sort(graph)