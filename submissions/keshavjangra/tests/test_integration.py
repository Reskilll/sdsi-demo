"""End-to-end / integration tests using fixture JSON files."""

import json
import sys
from pathlib import Path

import pytest

from scheduler.graph import DAG
from scheduler.topo import topological_sort
from scheduler.parallel import parallel_stages, parallel_schedule, estimated_makespan
from scheduler.critical import critical_path
from scheduler.failure import downstream_impact

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> DAG:
    return DAG.from_json_file(FIXTURE_DIR / name)


# ---------------------------------------------------------------------------
# sample1.json
# ---------------------------------------------------------------------------

class TestSample1:
    dag = _load("sample1.json")

    def test_structure(self):
        assert len(self.dag) == 5
        assert self.dag.roots() == ["A"]
        assert self.dag.leaves() == ["E"]

    def test_topo(self):
        order = topological_sort(self.dag)
        pos = {jid: i for i, jid in enumerate(order)}
        assert pos["A"] < pos["B"]
        assert pos["A"] < pos["C"]
        assert pos["B"] < pos["D"]
        assert pos["C"] < pos["D"]
        assert pos["D"] < pos["E"]

    def test_stages(self):
        stages = parallel_stages(self.dag)
        assert len(stages) == 4

    def test_critical(self):
        path, total = critical_path(self.dag)
        assert total == 13.0  # A(3)+B(5)+D(4)+E(1)

    def test_failure_on_b(self):
        skipped = downstream_impact(self.dag, "B")
        assert "D" in skipped
        assert "E" in skipped


# ---------------------------------------------------------------------------
# sample2.json
# ---------------------------------------------------------------------------

class TestSample2:
    dag = _load("sample2.json")

    def test_topo(self):
        order = topological_sort(self.dag)
        assert order[0] == "LINT"
        assert order[-1] == "DEPLOY"

    def test_parallel_stages(self):
        stages = parallel_stages(self.dag)
        assert len(stages) == 4

    def test_worker_schedule(self):
        sched = parallel_schedule(self.dag, worker_limit=2)
        # Every slice is ≤ 2
        assert all(len(s) <= 2 for s in sched)

    def test_makespan_unlimited(self):
        assert estimated_makespan(self.dag) == 14.0


# ---------------------------------------------------------------------------
# linear10.json – edge case: deep linear chain
# ---------------------------------------------------------------------------

class TestLinear10:
    dag = _load("linear10.json")

    def test_topological_order_is_linear(self):
        order = topological_sort(self.dag)
        assert order == [f"step{i}" for i in range(1, 11)]

    def test_critical_path_is_entire_chain(self):
        path, total = critical_path(self.dag)
        assert len(path) == 10
        assert total == 10.0

    def test_no_parallelism_possible(self):
        stages = parallel_stages(self.dag)
        assert all(len(s) == 1 for s in stages)


# ---------------------------------------------------------------------------
# independent.json – all jobs are independent
# ---------------------------------------------------------------------------

class TestIndependent:
    dag = _load("independent.json")

    def test_single_stage(self):
        stages = parallel_stages(self.dag)
        assert len(stages) == 1
        assert stages[0] == {"A", "B", "C", "D"}

    def test_critical_path_is_longest_duration(self):
        path, total = critical_path(self.dag)
        assert total == 4.0


# ---------------------------------------------------------------------------
# Validation of invalid inputs
# ---------------------------------------------------------------------------

class TestValidation:
    def test_cycle_file_rejected(self):
        with pytest.raises(ValueError, match="Cycle detected"):
            _load("cycle.json")

    def test_missing_dep_file_rejected(self):
        with pytest.raises(ValueError, match="Missing dependencies"):
            _load("missing_dep.json")


# ---------------------------------------------------------------------------
# fan.json
# ---------------------------------------------------------------------------

class TestFan:
    dag = _load("fan.json")

    def test_critical_path_fan(self):
        path, total = critical_path(self.dag)
        # A(10) → B(1)/C(1) → D/E → F(5) → G(3)
        # A→B→D→F→G = 10+1+1+5+3 = 20
        # A→C→E→F→G = same
        assert total == 20.0

    def test_failure_on_f_skips_g(self):
        skipped = downstream_impact(self.dag, "F")
        assert "G" in skipped


# ---------------------------------------------------------------------------
# zero_duration.json
# ---------------------------------------------------------------------------

class TestZeroDuration:
    dag = _load("zero_duration.json")

    def test_critical_path_zero(self):
        path, total = critical_path(self.dag)
        assert total == 0.0

    def test_topo_works(self):
        assert topological_sort(self.dag) == ["A", "B"]


# ---------------------------------------------------------------------------
# no_edges.json
# ---------------------------------------------------------------------------

class TestNoEdges:
    dag = _load("no_edges.json")

    def test_all_are_roots_and_leaves(self):
        assert self.dag.roots() == ["A", "B", "C"]
        assert self.dag.leaves() == ["A", "B", "C"]

    def test_critical_path_is_longest(self):
        path, total = critical_path(self.dag)
        assert total == 3.0  # B has duration 3


# ---------------------------------------------------------------------------
# diamond.json
# ---------------------------------------------------------------------------

class TestDiamond:
    dag = _load("diamond.json")

    def test_stages(self):
        stages = parallel_stages(self.dag)
        # X → A → B, C (B and C are independent)
        assert len(stages) == 3
        assert stages[1] == {"A"}
        assert stages[2] == {"B", "C"}