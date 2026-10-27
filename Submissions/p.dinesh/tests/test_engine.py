"""Tests for the DAG job scheduler."""

import os
import sys
import pytest

# Make `src` importable when running tests from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import JobSpec, load_jobs
from src.engine import (
    validate,
    topological_sort,
    plan_stages,
    critical_path,
    downstream_of,
    build_plan,
    to_dot,
    ValidationResult,
    Stage,
    CriticalPathResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _jobs(*specs: tuple[str, int, list[str]]) -> list[JobSpec]:
    """Quick builder: _jobs(('A',3,[]), ('B',2,['A']))."""
    return [JobSpec(id=n, duration=d, dependsOn=deps) for n, d, deps in specs]


# ===================================================================
# M1 — Validation
# ===================================================================

class TestValidation:
    def test_valid_dag(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]), ("C", 1, ["A"]), ("D", 4, ["B", "C"]))
        v = validate(j)
        assert v.valid is True
        assert v.cycle_path is None
        assert v.missing_dependencies == []
        assert v.errors == []

    def test_cycle_detection(self):
        j = _jobs(("X", 2, ["Z"]), ("Y", 3, ["X"]), ("Z", 1, ["Y"]))
        v = validate(j)
        assert v.valid is False
        assert v.cycle_path is not None
        # The cycle path must contain X, Y, Z in cyclic order
        assert set(v.cycle_path) == {"X", "Y", "Z"}
        assert len(v.cycle_path) >= 3

    def test_self_loop(self):
        j = _jobs(("A", 1, ["A"]),)
        v = validate(j)
        assert v.valid is False
        assert v.cycle_path is not None
        assert "A" in v.cycle_path

    def test_missing_dependency(self):
        j = _jobs(("P", 5, ["Q"]), ("Q", 2, ["R"]))
        v = validate(j)
        assert v.valid is False
        assert len(v.missing_dependencies) > 0
        assert ("Q", "R") in v.missing_dependencies or any(
            m == "R" for _, m in v.missing_dependencies
        )

    def test_duplicate_id(self):
        j = _jobs(("A", 1, []), ("A", 2, []))
        v = validate(j)
        assert v.valid is False
        assert v.duplicate_ids == ["A"]

    def test_empty_graph(self):
        v = validate([])
        assert v.valid is True

    def test_single_node(self):
        v = validate(_jobs(("X", 1, []),))
        assert v.valid is True

    def test_pipeline(self):
        """A→B→C→D linear pipeline — always valid."""
        j = _jobs(
            ("A", 2, []),
            ("B", 3, ["A"]),
            ("C", 4, ["B"]),
            ("D", 1, ["C"]),
        )
        v = validate(j)
        assert v.valid is True

    def test_diamond(self):
        """A → B, C; B, C → D — valid diamond."""
        j = _jobs(
            ("A", 2, []),
            ("B", 3, ["A"]),
            ("C", 4, ["A"]),
            ("D", 1, ["B", "C"]),
        )
        v = validate(j)
        assert v.valid is True


# ===================================================================
# M2 — Topological sort
# ===================================================================

class TestTopologicalSort:
    def test_basic_order(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]), ("C", 1, ["A"]), ("D", 4, ["B", "C"]))
        order = topological_sort(j)
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_linear_pipeline(self):
        j = _jobs(
            ("A", 2, []),
            ("B", 3, ["A"]),
            ("C", 4, ["B"]),
            ("D", 1, ["C"]),
        )
        order = topological_sort(j)
        assert order == ["A", "B", "C", "D"]

    def test_independent_jobs(self):
        j = _jobs(("A", 1, []), ("B", 2, []), ("C", 3, []))
        order = topological_sort(j)
        assert set(order) == {"A", "B", "C"}
        assert len(order) == 3

    def test_cycle_raises(self):
        j = _jobs(("X", 2, ["Z"]), ("Y", 3, ["X"]), ("Z", 1, ["Y"]))
        with pytest.raises(ValueError, match="cycle"):
            topological_sort(j)


# ===================================================================
# M3 — Parallel stages & worker limit
# ===================================================================

class TestStages:
    def test_basic_stages(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]), ("C", 1, ["A"]), ("D", 4, ["B", "C"]))
        stages = plan_stages(j, worker_limit=4)
        assert stages[0].jobs == ["A"]
        assert set(stages[1].jobs) == {"B", "C"}
        assert stages[2].jobs == ["D"]

    def test_worker_limit_enforced(self):
        """With worker_limit=1, independent jobs must be serialised."""
        j = _jobs(("A", 1, []), ("B", 1, []), ("C", 1, []))
        stages = plan_stages(j, worker_limit=1)
        # Each stage gets exactly 1 job because limit is 1
        for s in stages:
            assert len(s.jobs) == 1

    def test_worker_limit_two(self):
        j = _jobs(("A", 1, []), ("B", 1, []), ("C", 1, []), ("D", 1, []))
        stages = plan_stages(j, worker_limit=2)
        # Four independent jobs, limit 2 → 2 stages of 2 jobs each
        assert len(stages[0].jobs) == 2
        assert len(stages[1].jobs) == 2

    def test_complex_pipeline_stages(self):
        j = _jobs(
            ("fetch", 5, []),
            ("clean_a", 3, ["fetch"]),
            ("clean_b", 2, ["fetch"]),
            ("train_a", 8, ["clean_a"]),
            ("train_b", 6, ["clean_b"]),
            ("validate", 4, ["train_a", "train_b"]),
            ("deploy", 2, ["validate"]),
            ("notify", 1, ["deploy"]),
        )
        stages = plan_stages(j, worker_limit=4)
        assert stages[0].jobs == ["fetch"]
        assert set(stages[1].jobs) == {"clean_a", "clean_b"}
        assert set(stages[2].jobs) == {"train_a", "train_b"}
        assert stages[3].jobs == ["validate"]
        assert stages[4].jobs == ["deploy"]
        assert stages[5].jobs == ["notify"]

    def test_stage_timing(self):
        """Stage durations should be the max of their jobs."""
        j = _jobs(("A", 5, []), ("B", 3, []))
        stages = plan_stages(j, worker_limit=2)
        assert stages[0].duration == 5
        assert stages[0].start_time == 0
        assert stages[0].end_time == 5


# ===================================================================
# M4 — Critical path
# ===================================================================

class TestCriticalPath:
    def test_linear(self):
        j = _jobs(
            ("A", 2, []),
            ("B", 3, ["A"]),
            ("C", 4, ["B"]),
        )
        cp = critical_path(j)
        assert cp.path == ["A", "B", "C"]
        assert cp.total_time == 9  # 2+3+4

    def test_diamond(self):
        """A→(B,C)→D — critical path is the longer branch."""
        j = _jobs(
            ("A", 2, []),
            ("B", 5, ["A"]),
            ("C", 3, ["A"]),
            ("D", 1, ["B", "C"]),
        )
        cp = critical_path(j)
        assert cp.path == ["A", "B", "D"]
        assert cp.total_time == 8  # 2+5+1

    def test_independent_chains(self):
        """Two independent chains: A→B (5+6=11) and C→D (3+4=7)."""
        j = _jobs(
            ("A", 5, []),
            ("B", 6, ["A"]),
            ("C", 3, []),
            ("D", 4, ["C"]),
        )
        cp = critical_path(j)
        assert cp.total_time == 11
        assert cp.path == ["A", "B"]

    def test_single_node(self):
        j = _jobs(("X", 42, []),)
        cp = critical_path(j)
        assert cp.path == ["X"]
        assert cp.total_time == 42

    def test_complex(self):
        j = _jobs(
            ("fetch", 5, []),
            ("clean_a", 3, ["fetch"]),
            ("clean_b", 2, ["fetch"]),
            ("train_a", 8, ["clean_a"]),
            ("train_b", 6, ["clean_b"]),
            ("validate", 4, ["train_a", "train_b"]),
            ("deploy", 2, ["validate"]),
            ("notify", 1, ["deploy"]),
        )
        cp = critical_path(j)
        # Critical path: fetch→clean_a→train_a→validate→deploy→notify = 5+3+8+4+2+1 = 23
        assert cp.total_time == 23
        assert cp.path == ["fetch", "clean_a", "train_a", "validate", "deploy", "notify"]


# ===================================================================
# M5 — Failure simulation
# ===================================================================

class TestFailureSimulation:
    def test_basic_downstream(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]), ("C", 1, ["A"]), ("D", 4, ["B", "C"]))
        assert set(downstream_of(j, "B")) == {"D"}
        assert set(downstream_of(j, "A")) == {"B", "C", "D"}
        assert downstream_of(j, "D") == []

    def test_fail_non_existent(self):
        j = _jobs(("A", 1, []),)
        assert downstream_of(j, "Z") == []

    def test_fail_sink(self):
        """Failing a leaf node skips nothing downstream."""
        j = _jobs(
            ("A", 1, []),
            ("B", 2, ["A"]),
            ("C", 3, ["B"]),
        )
        assert downstream_of(j, "C") == []

    def test_fail_source(self):
        """Failing the root skips everything downstream."""
        j = _jobs(
            ("A", 1, []),
            ("B", 2, ["A"]),
            ("C", 3, ["A"]),
            ("D", 4, ["B", "C"]),
            ("E", 5, []),  # independent
        )
        skipped = downstream_of(j, "A")
        assert set(skipped) == {"B", "C", "D"}
        assert "E" not in skipped  # E is independent

    def test_transitive_downstream(self):
        """A→B→C→D: failing B skips C and D."""
        j = _jobs(
            ("A", 1, []),
            ("B", 1, ["A"]),
            ("C", 1, ["B"]),
            ("D", 1, ["C"]),
        )
        skipped = downstream_of(j, "B")
        assert set(skipped) == {"C", "D"}


# ===================================================================
# build_plan integration
# ===================================================================

class TestBuildPlan:
    def test_valid_plan(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]))
        plan = build_plan(j, worker_limit=4)
        assert plan.valid is True
        assert plan.topological_order is not None
        assert plan.stages is not None
        assert plan.critical_path is not None
        assert plan.critical_path_time is not None

    def test_invalid_plan_short_circuits(self):
        j = _jobs(("X", 2, ["Z"]), ("Y", 3, ["X"]), ("Z", 1, ["Y"]))
        plan = build_plan(j)
        assert plan.valid is False
        assert plan.topological_order is None
        assert plan.stages is None

    def test_failure_mode(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]), ("C", 1, ["A"]))
        plan = build_plan(j, failed_job="A", worker_limit=4)
        assert plan.failed_job == "A"
        assert set(plan.skipped_jobs or []) == {"B", "C"}

    def test_to_dict_and_json(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]))
        plan = build_plan(j, worker_limit=4)
        d = plan.to_dict()
        assert d["valid"] is True
        assert "topological_order" in d
        json_str = plan.to_json()
        assert '"valid": true' in json_str


# ===================================================================
# JobSpec model
# ===================================================================

class TestJobSpec:
    def test_valid_from_dict(self):
        d = {"id": "A", "duration": 3, "dependsOn": ["B", "C"]}
        j = JobSpec.from_dict(d)
        assert j.id == "A"
        assert j.duration == 3
        assert j.dependsOn == ["B", "C"]

    def test_default_depends_on(self):
        d = {"id": "A", "duration": 1}
        j = JobSpec.from_dict(d)
        assert j.dependsOn == []

    def test_missing_id(self):
        with pytest.raises(KeyError, match="id"):
            JobSpec.from_dict({"duration": 1})

    def test_missing_duration(self):
        with pytest.raises(KeyError, match="duration"):
            JobSpec.from_dict({"id": "A"})

    def test_negative_duration(self):
        with pytest.raises(ValueError, match="duration"):
            JobSpec.from_dict({"id": "A", "duration": -5})

    def test_non_string_id(self):
        with pytest.raises(ValueError, match="id"):
            JobSpec.from_dict({"id": 123, "duration": 1})

    def test_non_list_deps(self):
        with pytest.raises(TypeError, match="dependsOn"):
            JobSpec.from_dict({"id": "A", "duration": 1, "dependsOn": "B"})

    def test_non_string_dep_entry(self):
        with pytest.raises(TypeError, match="string"):
            JobSpec.from_dict({"id": "A", "duration": 1, "dependsOn": [1]})

    def test_duplicate_deps_deduplicated(self):
        """Specifying the same dependency twice should collapse to one."""
        j = JobSpec.from_dict({"id": "A", "duration": 1, "dependsOn": ["B", "B", "C", "B"]})
        assert j.dependsOn == ["B", "C"]

    def test_empty_string_deps_filtered(self):
        """Empty-string dependencies should be silently dropped."""
        j = JobSpec.from_dict({"id": "A", "duration": 1, "dependsOn": ["", "B", ""]})
        assert j.dependsOn == ["B"]


# ===================================================================
# load_jobs
# ===================================================================

class TestLoadJobs:
    def test_load_basic(self, tmp_path):
        import json
        jf = tmp_path / "jobs.json"
        jf.write_text(json.dumps(
            [{"id": "A", "duration": 3, "dependsOn": []},
             {"id": "B", "duration": 2, "dependsOn": ["A"]}]
        ))
        jobs = load_jobs(str(jf))
        assert len(jobs) == 2
        assert jobs[0].id == "A"

    def test_load_missing_file(self):
        with pytest.raises(SystemExit, match="not found"):
            load_jobs("__nonexistent__.json")

    def test_load_invalid_json(self, tmp_path):
        jf = tmp_path / "bad.json"
        jf.write_text("{not json")
        with pytest.raises(SystemExit, match="invalid JSON"):
            load_jobs(str(jf))

    def test_load_non_list(self, tmp_path):
        import json
        jf = tmp_path / "obj.json"
        jf.write_text(json.dumps({"id": "A"}))
        with pytest.raises(SystemExit, match="array"):
            load_jobs(str(jf))

    def test_load_empty(self, tmp_path):
        import json
        jf = tmp_path / "empty.json"
        jf.write_text(json.dumps([]))
        with pytest.raises(SystemExit, match="empty"):
            load_jobs(str(jf))


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    def test_zero_duration_jobs(self):
        """Zero-duration jobs are valid — they complete instantly."""
        j = _jobs(("A", 0, []), ("B", 0, ["A"]))
        v = validate(j)
        assert v.valid is True
        # Verify scheduling still works
        stages = plan_stages(j, worker_limit=4)
        assert len(stages) >= 1

    def test_disconnected_components(self):
        """Two independent subgraphs."""
        j = _jobs(
            ("A", 1, []), ("B", 2, ["A"]),  # component 1
            ("X", 3, []), ("Y", 1, ["X"]),   # component 2
        )
        v = validate(j)
        assert v.valid is True
        order = topological_sort(j)
        assert order.index("A") < order.index("B")
        assert order.index("X") < order.index("Y")

    def test_large_duration_values(self):
        j = _jobs(("A", 999_999, []),)
        v = validate(j)
        assert v.valid is True
        cp = critical_path(j)
        assert cp.total_time == 999_999

    def test_multiple_roots(self):
        """Multiple jobs with no dependencies."""
        j = _jobs(("A", 1, []), ("B", 2, []), ("C", 3, []), ("D", 4, []))
        v = validate(j)
        assert v.valid is True
        stages = plan_stages(j, worker_limit=3)
        assert len(stages) == 2  # 4 jobs, limit 3 → 3 in stage 1, 1 in stage 2

    def test_same_duration_jobs_parallel(self):
        """When all jobs have the same duration, stage grouping is straightforward."""
        j = _jobs(("A", 2, []), ("B", 2, []), ("C", 2, []))
        stages = plan_stages(j, worker_limit=2)
        assert len(stages) == 2  # 3 jobs, limit 2
        assert stages[0].duration == 2
        assert stages[1].duration == 2

    def test_strict_chain(self):
        """Single chain where every job depends on the previous one."""
        j = _jobs(
            ("1", 1, []),
            ("2", 1, ["1"]),
            ("3", 1, ["2"]),
            ("4", 1, ["3"]),
            ("5", 1, ["4"]),
        )
        stages = plan_stages(j, worker_limit=4)
        # Each stage only has 1 job because of the chain dependency
        assert all(len(s.jobs) == 1 for s in stages)
        assert len(stages) == 5

    def test_multiple_deps_single_parent_chain(self):
        """B depends on A; C also depends on A (not B). Both B and C are parallel after A."""
        j = _jobs(
            ("A", 2, []),
            ("B", 3, ["A"]),
            ("C", 4, ["A"]),
        )
        stages = plan_stages(j, worker_limit=4)
        assert stages[0].jobs == ["A"]
        assert set(stages[1].jobs) == {"B", "C"}

    def test_fan_in(self):
        """Multiple independent paths feeding into one job."""
        j = _jobs(
            ("A", 1, []),
            ("B", 1, []),
            ("C", 1, []),
            ("D", 5, ["A", "B", "C"]),
        )
        stages = plan_stages(j, worker_limit=4)
        assert set(stages[0].jobs) == {"A", "B", "C"}
        assert stages[1].jobs == ["D"]

    def test_fan_out(self):
        """One job feeding into many."""
        j = _jobs(
            ("A", 2, []),
            ("B", 1, ["A"]),
            ("C", 1, ["A"]),
            ("D", 1, ["A"]),
            ("E", 1, ["A"]),
        )
        stages = plan_stages(j, worker_limit=4)
        assert stages[0].jobs == ["A"]
        assert set(stages[1].jobs) == {"B", "C", "D", "E"}

    def test_worker_limit_one_chain_becomes_serial(self):
        """Even independent jobs become serial when worker_limit=1."""
        j = _jobs(("A", 3, []), ("B", 2, []), ("C", 1, []))
        stages = plan_stages(j, worker_limit=1)
        assert len(stages) == 3
        assert all(len(s.jobs) == 1 for s in stages)
        assert stages[0].duration == 3
        assert stages[1].duration == 2
        assert stages[2].duration == 1

    def test_critical_path_on_diamond_weighs_correct_branch(self):
        """Ensure EST-based CP picks the true bottleneck, not just any path."""
        j = _jobs(
            ("root", 1, []),
            ("left_heavy", 10, ["root"]),
            ("right_light", 2, ["root"]),
            ("sink", 1, ["left_heavy", "right_light"]),
        )
        cp = critical_path(j)
        assert cp.path == ["root", "left_heavy", "sink"]
        assert cp.total_time == 12

    def test_critical_path_multiple_sinks(self):
        """When multiple sinks exist, CP is the longest path to any sink."""
        j = _jobs(
            ("R", 2, []),
            ("A", 5, ["R"]),
            ("B", 1, ["R"]),
            ("C", 3, ["R"]),
        )
        cp = critical_path(j)
        # Longest: R→A = 2+5 = 7
        assert cp.total_time == 7
        assert cp.path == ["R", "A"]


# ===================================================================
# Bonus: Graphviz DOT output
# ===================================================================

class TestDotOutput:
    def test_basic_dot_structure(self):
        j = _jobs(("A", 3, []), ("B", 2, ["A"]))
        dot = to_dot(j)
        assert dot.startswith("digraph DAG {")
        assert dot.rstrip().endswith("}")
        assert '"A" [label="A (3s)"' in dot
        assert '"A" -> "B"' in dot

    def test_critical_path_highlighted(self):
        j = _jobs(
            ("A", 2, []),
            ("B", 5, ["A"]),
            ("C", 3, ["A"]),
            ("D", 1, ["B", "C"]),
        )
        cp = critical_path(j).path  # A, B, D
        dot = to_dot(j, critical_path_nodes=cp)
        # Critical path nodes marked red
        assert 'color=red' in dot
        assert "penwidth=2" in dot

    def test_failure_skipped_greyed(self):
        j = _jobs(("A", 1, []), ("B", 1, ["A"]), ("C", 1, ["B"]))
        skipped = downstream_of(j, "B")  # ["C"]
        dot = to_dot(j, failed_node="B", skipped_nodes=skipped)
        assert 'fillcolor="#ffcccc"' in dot  # failed node highlight
        assert 'fillcolor="#eeeeee"' in dot  # skipped node grayed
        assert 'style=dashed' in dot  # skipped edges dashed