"""Test M1: Graph validation — cycle detection and missing dependencies."""

import pytest
from scheduler.models import load_graph
from scheduler.validation import validate


def test_valid_graph_no_issues():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
    ]})
    result = validate(graph)
    assert result.is_valid
    assert not result.cycles
    assert not result.missing_deps


def test_missing_dependency():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["X"]},
    ]})
    result = validate(graph)
    assert not result.is_valid
    assert result.missing_deps == ["X"]
    assert "Missing dependencies" in result.errors[0]


def test_simple_cycle():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1, "dependsOn": ["B"]},
        {"id": "B", "duration": 1, "dependsOn": ["A"]},
    ]})
    result = validate(graph)
    assert not result.is_valid
    assert len(result.cycles) >= 1
    # Both jobs should appear in the cycle
    cycle = result.cycles[0]
    assert "A" in cycle
    assert "B" in cycle


def test_self_cycle():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1, "dependsOn": ["A"]},
    ]})
    result = validate(graph)
    assert not result.is_valid
    assert len(result.cycles) >= 1


def test_three_node_cycle():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1, "dependsOn": ["B"]},
        {"id": "B", "duration": 1, "dependsOn": ["C"]},
        {"id": "C", "duration": 1, "dependsOn": ["A"]},
    ]})
    result = validate(graph)
    assert not result.is_valid
    assert len(result.cycles) >= 1
    cycle = result.cycles[0]
    assert len(cycle) >= 3


def test_cycle_and_missing_together():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1, "dependsOn": ["B"]},
        {"id": "B", "duration": 1, "dependsOn": ["A", "X"]},
    ]})
    result = validate(graph)
    assert not result.is_valid
    assert result.has_cycles
    assert result.has_missing_deps
    assert "X" in result.missing_deps


def test_empty_graph():
    graph = load_graph({"jobs": []})
    result = validate(graph)
    assert result.is_valid


def test_no_dependencies():
    graph = load_graph({"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 1},
        {"id": "C", "duration": 1},
    ]})
    result = validate(graph)
    assert result.is_valid