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
    downstream_of_many,
    list_schedule,
    slack_analysis,
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

    def test_multiple_failures_union(self):
        """Failing two independent sources skips the union of their downstreams."""
        j = _jobs(
            ("A", 1, []),
            ("B", 1, ["A"]),
            ("C", 1, []),
            ("D", 1, ["C"]),
            ("E", 1, []),
        )
        skipped = downstream_of_many(j, ["A", "C"])
        assert set(skipped) == {"B", "D"}
        assert "E" not in skipped

    def test_multiple_failures_overlap(self):
        """Overlapping downstream regions are not double-counted.

        B is itself a *failed* job, so it is not "skipped" — only C is.
        """
        j = _jobs(
            ("A", 1, []),
            ("B", 1, ["A"]),
            ("C", 1, ["B"]),
        )
        skipped = downstream_of_many(j, ["A", "B"])
        assert set(skipped) == {"C"}

    def test_multiple_failures_ignore_unknown(self):
        """Unknown failed IDs are silently ignored."""
        j = _jobs(("A", 1, []), ("B", 1, ["A"]))
        assert downstream_of_many(j, ["Z", "A"]) == ["B"]


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


# ===================================================================
# Bonus: Concrete list scheduling
# ===================================================================

class TestListSchedule:
    def test_single_job(self):
        sched = list_schedule(_jobs(("A", 5, []),), worker_limit=2)
        assert sched.makespan == 5
        assert len(sched.jobs) == 1
        assert sched.jobs[0].id == "A"
        assert (sched.jobs[0].start, sched.jobs[0].finish) == (0, 5)

    def test_serial_chain(self):
        """A→B: B cannot start until A finishes, even on 2 workers."""
        sched = list_schedule(_jobs(("A", 5, []), ("B", 3, ["A"])), worker_limit=2)
        assert sched.makespan == 8
        b = next(s for s in sched.jobs if s.id == "B")
        assert b.start == 5

    def test_two_independent_on_one_worker(self):
        """Independent jobs must serialise onto a single worker."""
        sched = list_schedule(_jobs(("A", 2, []), ("B", 3, [])), worker_limit=1)
        assert sched.makespan == 5
        assert sched.worker_count == 1

    def test_two_independent_on_two_workers(self):
        """Independent jobs run in parallel on separate workers."""
        sched = list_schedule(_jobs(("A", 2, []), ("B", 3, [])), worker_limit=2)
        assert sched.makespan == 3
        assert {s.worker for s in sched.jobs} == {0, 1}

    def test_dependency_forced_wait_while_worker_free(self):
        """B depends on A; a second independent C can backfill worker 1.

        A(5)→B(2), plus C(1) independent.  With 2 workers, C runs on worker 1
        while A runs on worker 0, then B runs right after A — makespan 7.
        """
        j = _jobs(("A", 5, []), ("B", 2, ["A"]), ("C", 1, []))
        sched = list_schedule(j, worker_limit=2)
        assert sched.makespan == 7

    def test_rejects_zero_workers(self):
        with pytest.raises(ValueError, match="worker_limit"):
            list_schedule(_jobs(("A", 1, []),), worker_limit=0)

    def test_empty(self):
        sched = list_schedule([], worker_limit=2)
        assert sched.makespan == 0
        assert sched.jobs == []


# ===================================================================
# Bonus: Slack / float analysis
# ===================================================================

class TestSlackAnalysis:
    def test_critical_chain_all_zero_slack(self):
        j = _jobs(("A", 2, []), ("B", 3, ["A"]), ("C", 4, ["B"]))
        slack = {s.id: s for s in slack_analysis(j)}
        assert slack["A"].is_critical
        assert slack["B"].is_critical
        assert slack["C"].is_critical
        assert slack["C"].earliest_start == 5

    def test_non_critical_branch_has_slack(self):
        """A→(B heavy 5, C light 3)→D: C has float, B does not."""
        j = _jobs(
            ("A", 2, []),
            ("B", 5, ["A"]),
            ("C", 3, ["A"]),
            ("D", 1, ["B", "C"]),
        )
        slack = {s.id: s for s in slack_analysis(j)}
        assert slack["B"].is_critical
        assert slack["C"].total_slack == 2  # 5 - 3
        assert not slack["C"].is_critical
        assert slack["A"].is_critical
        assert slack["D"].is_critical

    def test_multiple_critical_paths_flag_all(self):
        """Two equal-length branches are both critical (tie handled)."""
        j = _jobs(
            ("A", 1, []),
            ("B", 5, ["A"]),
            ("C", 5, ["A"]),
        )
        slack = {s.id: s for s in slack_analysis(j)}
        assert slack["B"].is_critical and slack["C"].is_critical

    def test_empty(self):
        assert slack_analysis([]) == []


# ===================================================================
# Empty-input / defensive guards
# ===================================================================

class TestEmptyInputs:
    def test_build_plan_empty(self):
        plan = build_plan([], worker_limit=4)
        assert plan.valid is True
        assert plan.topological_order == []
        assert plan.stages == []
        assert plan.critical_path == []
        assert plan.critical_path_time == 0

    def test_critical_path_empty(self):
        cp = critical_path([])
        assert cp.path == []
        assert cp.total_time == 0

    def test_plan_stages_empty(self):
        assert plan_stages([], worker_limit=4) == []

    def test_plan_stages_rejects_zero_workers(self):
        with pytest.raises(ValueError, match="worker_limit"):
            plan_stages(_jobs(("A", 1, []),), worker_limit=0)

    def test_build_plan_rejects_zero_workers(self):
        with pytest.raises(ValueError, match="worker_limit"):
            build_plan(_jobs(("A", 1, []),), worker_limit=0)


# ===================================================================
# CLI smoke tests (the --only regression)
# ===================================================================

class TestCLI:
    def test_only_flag_registered(self, tmp_path):
        """Regression: --only was referenced but never registered → AttributeError.

        A bare `--only stages` on a valid graph must exit 0 (not crash).
        """
        import json
        from src.cli import main
        jf = tmp_path / "j.json"
        jf.write_text(json.dumps([{"id": "A", "duration": 1}]))
        assert main([str(jf), "--only", "stages"]) == 0

    def test_only_validate_valid(self, tmp_path):
        import json
        from src.cli import main
        jf = tmp_path / "j.json"
        jf.write_text(json.dumps([{"id": "A", "duration": 1}]))
        assert main([str(jf), "--only", "validate"]) == 0

    def test_only_validate_invalid(self, tmp_path):
        import json
        from src.cli import main
        jf = tmp_path / "j.json"
        jf.write_text(json.dumps([{"id": "A", "duration": 1, "dependsOn": ["Z"]}]))
        assert main([str(jf), "--only", "validate"]) == 1

    def test_only_slack(self, tmp_path):
        import json
        from src.cli import main
        jf = tmp_path / "j.json"
        jf.write_text(json.dumps([
            {"id": "A", "duration": 2},
            {"id": "B", "duration": 5, "dependsOn": ["A"]},
            {"id": "C", "duration": 3, "dependsOn": ["A"]},
        ]))
        assert main([str(jf), "--only", "slack"]) == 0

    def test_multiple_fails_flag(self, tmp_path):
        import json
        from src.cli import main
        jf = tmp_path / "j.json"
        jf.write_text(json.dumps([
            {"id": "A", "duration": 1},
            {"id": "B", "duration": 1, "dependsOn": ["A"]},
            {"id": "C", "duration": 1},
            {"id": "D", "duration": 1, "dependsOn": ["C"]},
        ]))
        # --only fail with --fails A,C should skip B and D
        assert main([str(jf), "--only", "fail", "--fails", "A,C"]) == 0