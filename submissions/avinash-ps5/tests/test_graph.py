"""Tests for DAG graph operations: cycle detection, topo-sort, critical path."""

import pytest

from dag_scheduler.graph import (
    JobNode,
    build_adjacency,
    build_parent_map,
    critical_path,
    detect_cycle,
    simulate_failure,
    topological_sort,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _jobs(*pairs) -> dict[str, JobNode]:
    """Build a job dict from (name, duration, [deps]) tuples."""
    return {n: JobNode(name=n, duration=d, depends_on=deps) for n, d, deps in pairs}


# ---------------------------------------------------------------------------
# M1 — Cycle detection
# ---------------------------------------------------------------------------

def test_no_cycle_dag():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, ["A"]),
        ("C", 3, ["A"]),
        ("D", 1, ["B", "C"]),
    )
    report = detect_cycle(jobs)
    assert not report.has_cycle
    assert report.cycle_path == []


def test_simple_cycle():
    jobs = _jobs(
        ("X", 1, ["Y"]),
        ("Y", 1, ["Z"]),
        ("Z", 1, ["X"]),
    )
    report = detect_cycle(jobs)
    assert report.has_cycle
    # The cycle should contain all three nodes in order
    assert len(report.cycle_path) >= 3


def test_self_cycle():
    jobs = _jobs(("A", 1, ["A"]),)
    report = detect_cycle(jobs)
    assert report.has_cycle


def test_diamond_no_cycle():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, ["A"]),
        ("C", 3, ["A"]),
        ("D", 1, ["B", "C"]),
    )
    assert not detect_cycle(jobs).has_cycle


def test_single_node():
    jobs = _jobs(("S", 5, []),)
    assert not detect_cycle(jobs).has_cycle


# ---------------------------------------------------------------------------
# M2 — Topological sort
# ---------------------------------------------------------------------------

def test_topo_simple():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, ["A"]),
        ("C", 3, ["A"]),
        ("D", 1, ["B", "C"]),
    )
    topo = topological_sort(jobs)
    # A must come before B and C; B and C before D
    idx = {name: i for i, name in enumerate(topo.order)}
    assert idx["A"] < idx["B"]
    assert idx["A"] < idx["C"]
    assert idx["B"] < idx["D"]
    assert idx["C"] < idx["D"]
    assert len(topo.order) == 4


def test_topo_levels():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, ["A"]),
        ("C", 3, []),
        ("D", 1, ["B", "C"]),
    )
    topo = topological_sort(jobs)
    # Two sources → level 0: A, C
    assert set(topo.levels[0]) == {"A", "C"}
    assert set(topo.levels[1]) == {"B"}
    assert set(topo.levels[2]) == {"D"}


def test_topo_raises_on_cycle():
    jobs = _jobs(
        ("X", 1, ["Y"]),
        ("Y", 1, ["X"]),
    )
    with pytest.raises(ValueError, match="cycle"):
        topological_sort(jobs)


# ---------------------------------------------------------------------------
# M4 — Critical path
# ---------------------------------------------------------------------------

def test_critical_path_linear():
    jobs = _jobs(
        ("A", 3, []),
        ("B", 5, ["A"]),
        ("C", 2, ["B"]),
    )
    cp = critical_path(jobs)
    assert cp.path == ["A", "B", "C"]
    assert cp.total_time == 10.0


def test_critical_path_diamond():
    jobs = _jobs(
        ("A", 1, []),
        ("B_short", 1, ["A"]),
        ("B_long", 5, ["A"]),
        ("C", 1, ["B_short", "B_long"]),
    )
    cp = critical_path(jobs)
    # Critical path should go through B_long (1 + 5 + 1 = 7) not B_short
    assert cp.total_time == 7.0
    assert "B_long" in cp.path
    assert "B_short" not in cp.path


def test_critical_path_parallel_sources():
    jobs = _jobs(
        ("A", 10, []),
        ("B", 1, []),
        ("C", 1, ["B"]),
    )
    cp = critical_path(jobs)
    # Longest path is just A (10) vs B→C (2)
    assert cp.total_time == 10.0


# ---------------------------------------------------------------------------
# M5 — Failure simulation
# ---------------------------------------------------------------------------

def test_failure_mid_pipeline():
    jobs = _jobs(
        ("fetch", 2, []),
        ("clean", 3, ["fetch"]),
        ("train", 5, ["clean"]),
        ("eval", 2, ["train"]),
    )
    result = simulate_failure(jobs, "clean")
    assert set(result.directly_skipped) == {"train"}
    assert set(result.all_skipped) == {"train", "eval"}
    assert set(result.still_runnable) == {"fetch"}


def test_failure_no_downstream():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 1, ["A"]),
        ("C", 1, ["A"]),
    )
    result = simulate_failure(jobs, "B")
    assert result.directly_skipped == []
    assert result.all_skipped == []
    assert set(result.still_runnable) == {"A", "C"}


def test_failure_source_node():
    jobs = _jobs(
        ("root", 1, []),
        ("mid", 2, ["root"]),
        ("leaf", 3, ["mid"]),
    )
    result = simulate_failure(jobs, "root")
    assert set(result.all_skipped) == {"mid", "leaf"}
    assert result.still_runnable == []


# ---------------------------------------------------------------------------
# Adjacency helpers
# ---------------------------------------------------------------------------

def test_build_adjacency():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, ["A"]),
        ("C", 3, ["A"]),
    )
    adj = build_adjacency(jobs)
    assert set(adj["A"]) == {"B", "C"}
    assert adj.get("B", []) == []
    assert adj.get("C", []) == []


def test_build_parent_map():
    jobs = _jobs(
        ("A", 1, []),
        ("B", 2, ["A"]),
        ("C", 3, ["A"]),
    )
    in_deg = build_parent_map(jobs)
    assert in_deg["A"] == 0
    assert in_deg["B"] == 1
    assert in_deg["C"] == 1