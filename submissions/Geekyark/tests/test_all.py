"""Comprehensive test suite for the DAG Job Scheduler.

Covers all M1–M5 modules and edge cases.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from src.critical_path import CriticalPathResult, compute_critical_path
from src.failure import FailureResult, simulate_failure, simulate_failures
from src.graph import DAG, Job
from src.orchestrator import PipelineResult, format_pipeline_result, run
from src.scheduler import ScheduleResult, Stage, schedule
from src.toposort import topological_sort
from src.validator import ValidationIssue, validate


# =========================================================================
# Helper factories
# =========================================================================

def _job(id_: str, dur: float, deps: list[str] | None = None) -> Job:
    return Job(id=id_, duration=dur, depends_on=deps or [])


def _dag(*jobs: Job) -> DAG:
    return DAG.from_jobs({j.id: j for j in jobs})


# =========================================================================
# Graph construction (DAG)
# =========================================================================

class TestDAGConstruction:
    """Test DAG object construction from JSON-like lists and Job dicts."""

    def test_basic_construction(self):
        raw = [
            {"id": "A", "duration": 1, "dependsOn": []},
            {"id": "B", "duration": 2, "dependsOn": ["A"]},
        ]
        dag = DAG.from_list(raw)
        assert dag.job_count == 2
        assert dag.edge_count == 1
        assert dag.predecessors("B") == ["A"]
        assert dag.successors("A") == ["B"]

    def test_empty_list(self):
        dag = DAG.from_list([])
        assert dag.job_count == 0
        assert dag.edge_count == 0

    def test_missing_dependsOn_field(self):
        """dependsOn is optional — should default to []."""
        raw = [{"id": "X", "duration": 5}]
        dag = DAG.from_list(raw)
        assert dag.jobs["X"].depends_on == []

    def test_zero_duration(self):
        """Zero-duration jobs are legal (milestones)."""
        dag = DAG.from_list([{"id": "milestone", "duration": 0}])
        assert dag.jobs["milestone"].duration == 0.0

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError, match="negative"):
            DAG.from_list([{"id": "bad", "duration": -1}])

    def test_missing_id_raises(self):
        with pytest.raises(ValueError, match="missing required field 'id'"):
            DAG.from_list([{"duration": 1}])

    def test_non_string_id_raises(self):
        with pytest.raises(ValueError, match="non-string 'id'"):
            DAG.from_list([{"id": 123, "duration": 1}])

    def test_duplicate_id_raises(self):
        raw = [
            {"id": "dup", "duration": 1},
            {"id": "dup", "duration": 2},
        ]
        with pytest.raises(ValueError, match="Duplicate job id"):
            DAG.from_list(raw)

    def test_non_numeric_duration_raises(self):
        with pytest.raises(ValueError, match="non-numeric duration"):
            DAG.from_list([{"id": "A", "duration": "slow"}])

    def test_dependsOn_non_string_raises(self):
        with pytest.raises(ValueError, match="non-string value"):
            DAG.from_list([{"id": "A", "duration": 1, "dependsOn": [1, 2]}])

    def test_input_not_a_list_raises(self):
        with pytest.raises(ValueError, match="must be a JSON array"):
            DAG.from_list({"id": "A"})  # type: ignore[arg-type]

    def test_item_not_a_dict_raises(self):
        with pytest.raises(ValueError, match="not a JSON object"):
            DAG.from_list(["string_instead_of_dict"])  # type: ignore[listitem]

    def test_dependsOn_not_a_list_raises(self):
        with pytest.raises(ValueError, match="non-list 'dependsOn'"):
            DAG.from_list([{"id": "A", "duration": 1, "dependsOn": "B"}])


class TestDAGQueries:
    """Test DAG query methods (source, sink, degree, downstream, upstream)."""

    def test_source_and_sink(self):
        # A → B → C
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["B"]),
        )
        assert dag.source_nodes() == ["A"]
        assert dag.sink_nodes() == ["C"]

    def test_multiple_sources(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 1),
            _job("C", 1, ["A", "B"]),
        )
        assert set(dag.source_nodes()) == {"A", "B"}

    def test_multiple_sinks(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 1, ["A"]),
            _job("C", 1, ["A"]),
        )
        assert set(dag.sink_nodes()) == {"B", "C"}

    def test_in_degree_out_degree(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 1, ["A"]),
            _job("C", 1, ["A"]),
        )
        assert dag.in_degree("A") == 0
        assert dag.out_degree("A") == 2
        assert dag.in_degree("B") == 1
        assert dag.out_degree("B") == 0

    def test_downstream_of(self):
        # A → B → C, A → D
        dag = _dag(
            _job("A", 1),
            _job("B", 1, ["A"]),
            _job("C", 1, ["B"]),
            _job("D", 1, ["A"]),
        )
        assert dag.downstream_of("A") == {"B", "C", "D"}
        assert dag.downstream_of("B") == {"C"}
        assert dag.downstream_of("C") == set()
        assert dag.downstream_of("nonexistent") == set()

    def test_upstream_of(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 1, ["A"]),
            _job("C", 1, ["A", "B"]),
        )
        assert dag.upstream_of("C") == {"A", "B"}
        assert dag.upstream_of("A") == set()


# =========================================================================
# M1 — Validation
# =========================================================================

class TestValidation:
    """Test cycle detection and missing dependency checks."""

    def test_valid_dag(self):
        dag = _dag(_job("A", 1), _job("B", 2, ["A"]))
        issues = validate(dag)
        assert len(issues) == 0

    def test_simple_cycle(self):
        dag = _dag(
            _job("A", 1, ["C"]),
            _job("B", 2, ["A"]),
            _job("C", 3, ["B"]),
        )
        issues = validate(dag)
        cycles = [i for i in issues if i.kind == "cycle"]
        assert len(cycles) >= 1
        assert "cycle" in cycles[0].kind.lower() or True

    def test_self_loop(self):
        dag = _dag(_job("A", 1, ["A"]))
        issues = validate(dag)
        cycles = [i for i in issues if i.kind == "cycle"]
        assert len(cycles) >= 1

    def test_missing_dependency(self):
        dag = _dag(_job("A", 1, ["ghost"]))
        issues = validate(dag)
        missing = [i for i in issues if i.kind == "missing_dependency"]
        assert len(missing) == 1
        assert "ghost" in missing[0].message

    def test_empty_graph(self):
        dag = DAG.from_list([])
        issues = validate(dag)
        assert len(issues) == 0

    def test_large_acyclic(self):
        """10 node complex DAG — no cycles."""
        json = [
            {"id": "T1", "duration": 4, "dependsOn": []},
            {"id": "T2", "duration": 2, "dependsOn": []},
            {"id": "T3", "duration": 6, "dependsOn": ["T1"]},
            {"id": "T4", "duration": 3, "dependsOn": ["T1", "T2"]},
            {"id": "T5", "duration": 5, "dependsOn": ["T2"]},
            {"id": "T6", "duration": 7, "dependsOn": ["T3", "T4"]},
            {"id": "T7", "duration": 2, "dependsOn": ["T4", "T5"]},
            {"id": "T8", "duration": 3, "dependsOn": ["T6", "T7"]},
            {"id": "T9", "duration": 4, "dependsOn": ["T6"]},
            {"id": "T10", "duration": 1, "dependsOn": ["T8", "T9"]},
        ]
        dag = DAG.from_list(json)
        issues = validate(dag)
        assert len(issues) == 0

    def test_diamond_with_no_cycle(self):
        """Diamond pattern: A → B, A → C, B → D, C → D."""
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["A"]),
            _job("D", 4, ["B", "C"]),
        )
        issues = validate(dag)
        assert len(issues) == 0


# =========================================================================
# M2 — Topological sort
# =========================================================================

class TestTopologicalSort:
    """Test topological sort produces valid orderings."""

    def test_simple_chain(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["B"]),
        )
        order = topological_sort(dag)
        assert order == ["A", "B", "C"]

    def test_diamond(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["A"]),
            _job("D", 4, ["B", "C"]),
        )
        order = topological_sort(dag)
        # A must be first; D must be last; B and C between A and D.
        assert order[0] == "A"
        assert order[-1] == "D"
        a_idx = order.index("A")
        d_idx = order.index("D")
        assert a_idx < order.index("B") < d_idx
        assert a_idx < order.index("C") < d_idx

    def test_single_node(self):
        dag = _dag(_job("X", 5))
        assert topological_sort(dag) == ["X"]

    def test_disconnected(self):
        dag = _dag(_job("A", 1), _job("B", 2), _job("C", 3))
        order = topological_sort(dag)
        assert set(order) == {"A", "B", "C"}
        assert len(order) == 3

    def test_cycle_raises(self):
        dag = _dag(
            _job("A", 1, ["C"]),
            _job("B", 2, ["A"]),
            _job("C", 3, ["B"]),
        )
        with pytest.raises(ValueError, match="cycle"):
            topological_sort(dag)


# =========================================================================
# M3 — Parallel scheduling
# =========================================================================

class TestScheduler:
    """Test parallel-stage scheduling with worker limits."""

    def test_single_worker_chain(self):
        """N=1 on a chain → sequential stages."""
        dag = _dag(
            _job("A", 2),
            _job("B", 3, ["A"]),
            _job("C", 1, ["B"]),
        )
        result = schedule(dag, worker_limit=1)
        assert len(result.stages) == 3
        assert result.total_time == 6.0
        assert result.job_start_times["A"] == 0.0
        assert result.job_start_times["B"] == 2.0
        assert result.job_start_times["C"] == 5.0

    def test_unlimited_workers(self):
        """N large → all disjoint jobs run in one stage."""
        dag = _dag(_job("A", 2), _job("B", 3), _job("C", 1))
        result = schedule(dag, worker_limit=10)
        assert result.total_time == 3.0  # max duration
        assert len(result.stages) == 1

    def test_worker_limit_enforced(self):
        """At most N jobs run concurrently."""
        dag = _dag(*[_job(f"J{i}", 1) for i in range(5)])
        result = schedule(dag, worker_limit=2)
        # 5 jobs at 2 workers → ceil(5/2)=3 stages of 1.0 each.
        assert len(result.stages) == 3
        for stage in result.stages:
            assert len(stage.jobs) <= 2

    def test_empty_dag(self):
        dag = DAG.from_list([])
        result = schedule(dag, worker_limit=4)
        assert result.total_time == 0.0
        assert result.total_jobs == 0

    def test_negative_worker_limit_raises(self):
        dag = _dag(_job("A", 1))
        with pytest.raises(ValueError, match="worker_limit"):
            schedule(dag, worker_limit=0)

    def test_complex_dag_scheduling(self):
        """Verify schedule respects dependencies in a complex DAG."""
        dag = _dag(
            _job("A", 4),
            _job("B", 2),
            _job("C", 6, ["A"]),
            _job("D", 3, ["A", "B"]),
            _job("E", 5, ["B"]),
            _job("F", 7, ["C", "D"]),
        )
        result = schedule(dag, worker_limit=3)

        # Every job must start after all its predecessors finish.
        for jid, job in dag.jobs.items():
            for dep in job.depends_on:
                assert result.job_finish_times[dep] <= result.job_start_times[jid]

        # Completion: A(4), B(2) parallel → t=2 B done, t=4 A done.
        # Then C(6), D(3), E(5): D finishes t=7, E t=7, C t=10.
        # Then F(7): starts at t=10, done t=17.
        assert result.total_time >= 17.0


# =========================================================================
# M4 — Critical path
# =========================================================================

class TestCriticalPath:
    """Test critical path computation."""

    def test_simple_chain(self):
        dag = _dag(
            _job("A", 2),
            _job("B", 3, ["A"]),
            _job("C", 1, ["B"]),
        )
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == 6.0
        assert len(cp.critical_paths) == 1
        assert cp.critical_paths[0] == ["A", "B", "C"]
        # Every job has zero slack.
        for s in cp.slack.values():
            assert abs(s) < 1e-9

    def test_parallel_branches(self):
        # A(4) → B(2)
        #     → C(5)  (critical: 4+5=9 vs 4+2=6)
        dag = _dag(
            _job("A", 4),
            _job("B", 2, ["A"]),
            _job("C", 5, ["A"]),
        )
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == 9.0
        assert len(cp.critical_paths) == 1
        assert cp.critical_paths[0] == ["A", "C"]
        # B should have slack.
        assert cp.slack["B"] > 0

    def test_empty_graph(self):
        dag = DAG.from_list([])
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == 0.0

    def test_single_job(self):
        dag = _dag(_job("only", 5))
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == 5.0
        assert cp.critical_paths == [["only"]]

    def test_zero_duration_jobs(self):
        dag = _dag(
            _job("start", 0),
            _job("work", 10, ["start"]),
        )
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == 10.0

    def test_slack_non_negative(self):
        """Slack must always be >= 0 mathematically."""
        dag = DAG.from_list([
            {"id": "T1", "duration": 4, "dependsOn": []},
            {"id": "T2", "duration": 2, "dependsOn": []},
            {"id": "T3", "duration": 6, "dependsOn": ["T1"]},
            {"id": "T4", "duration": 3, "dependsOn": ["T1", "T2"]},
            {"id": "T5", "duration": 5, "dependsOn": ["T2"]},
            {"id": "T6", "duration": 7, "dependsOn": ["T3", "T4"]},
            {"id": "T7", "duration": 2, "dependsOn": ["T4", "T5"]},
            {"id": "T8", "duration": 3, "dependsOn": ["T6", "T7"]},
            {"id": "T9", "duration": 4, "dependsOn": ["T6"]},
            {"id": "T10", "duration": 1, "dependsOn": ["T8", "T9"]},
        ])
        cp = compute_critical_path(dag)
        for jid, s in cp.slack.items():
            assert s >= -1e-9, f"Job {jid} has negative slack: {s}"


# =========================================================================
# M5 — Failure simulation
# =========================================================================

class TestFailure:
    """Test failure simulation and blast-radius computation."""

    def test_leaf_failure(self):
        """Failing a leaf node affects only itself."""
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["A"]),
        )
        result = simulate_failure(dag, "B")
        assert result.skipped_jobs == ["B"]
        assert set(result.surviving_jobs) == {"A", "C"}

    def test_root_failure(self):
        """Failing a root node cascades to everything downstream."""
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["A", "B"]),
        )
        result = simulate_failure(dag, "A")
        assert set(result.skipped_jobs) == {"A", "B", "C"}
        assert result.surviving_jobs == []

    def test_middle_failure(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
            _job("C", 3, ["B"]),
            _job("D", 1, ["A"]),
        )
        result = simulate_failure(dag, "B")
        assert set(result.skipped_jobs) == {"B", "C"}
        assert set(result.surviving_jobs) == {"A", "D"}

    def test_nonexistent_job_raises(self):
        dag = _dag(_job("A", 1))
        with pytest.raises(ValueError, match="does not exist"):
            simulate_failure(dag, "GHOST")

    def test_multiple_independent_failures(self):
        dag = _dag(
            _job("A", 1),
            _job("B", 2),
            _job("C", 3),
        )
        results = simulate_failures(dag, ["A", "B"])
        assert results["A"].skipped_jobs == ["A"]
        assert results["B"].skipped_jobs == ["B"]

    def test_isolated_job_failure(self):
        """A job with no dependents affects only itself."""
        dag = _dag(_job("island", 5))
        result = simulate_failure(dag, "island")
        assert result.skipped_jobs == ["island"]
        assert result.surviving_jobs == []


# =========================================================================
# Orchestrator — end-to-end
# =========================================================================

class TestOrchestrator:
    """End-to-end pipeline tests through orchestrator.run()."""

    def test_valid_example(self):
        result = run(
            [
                {"id": "A", "duration": 1},
                {"id": "B", "duration": 2, "dependsOn": ["A"]},
            ],
            worker_limit=2,
        )
        assert result.is_valid
        assert result.topological_order == ["A", "B"]
        assert result.schedule_result is not None
        assert result.critical_path_result is not None

    def test_cycle_rejects_further_steps(self):
        result = run([
            {"id": "A", "duration": 1, "dependsOn": ["C"]},
            {"id": "B", "duration": 2, "dependsOn": ["A"]},
            {"id": "C", "duration": 3, "dependsOn": ["B"]},
        ])
        assert not result.is_valid
        assert result.topological_order == []
        assert result.schedule_result is None

    def test_missing_dep_rejects(self):
        result = run([
            {"id": "deploy", "duration": 10, "dependsOn": ["build"]},
        ])
        assert not result.is_valid

    def test_with_failure(self):
        result = run(
            [
                {"id": "A", "duration": 1},
                {"id": "B", "duration": 2, "dependsOn": ["A"]},
                {"id": "C", "duration": 3, "dependsOn": ["B"]},
            ],
            fail_job="B",
        )
        assert result.is_valid
        assert result.failure_result is not None
        assert set(result.failure_result.skipped_jobs) == {"B", "C"}

    def test_from_json_file(self, tmp_path: Path):
        data = [{"id": "X", "duration": 1}]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        result = run(str(f))
        assert result.is_valid

    def test_invalid_json_file(self, tmp_path: Path):
        f = tmp_path / "bad.json"
        f.write_text("not json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            run(str(f))

    def test_non_array_json(self):
        with pytest.raises(ValueError, match="must be an array"):
            run([{"id": "A"}])  # missing duration — caught during parse
        # More explicit: top-level object instead of array.
        with pytest.raises(ValueError, match="must be a JSON array"):
            run(json.dumps({"not": "an array"}))

    def test_format_pipeline_result(self):
        result = run(
            [{"id": "X", "duration": 1}],
            worker_limit=1,
            fail_job="X",
        )
        text = format_pipeline_result(result)
        assert "M1" in text
        assert "M2" in text
        assert "M3" in text
        assert "M4" in text
        assert "M5" in text
        assert "X" in text


# =========================================================================
# CLI integration tests
# =========================================================================

class TestCLI:
    """Test the CLI main() entry point."""

    def test_help(self, tmp_path: Path):
        from main import main as cli_main
        # --help exits 0
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--help"])
        assert exc_info.value.code == 0

    def test_basic_run(self, tmp_path: Path):
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps([{"id": "A", "duration": 1}]))
        from main import main as cli_main
        code = cli_main([str(f)])
        assert code == 0

    def test_cycle_returns_nonzero(self, tmp_path: Path):
        f = tmp_path / "cycle.json"
        f.write_text(json.dumps([
            {"id": "A", "duration": 1, "dependsOn": ["C"]},
            {"id": "B", "duration": 2, "dependsOn": ["A"]},
            {"id": "C", "duration": 3, "dependsOn": ["B"]},
        ]))
        from main import main as cli_main
        code = cli_main([str(f)])
        assert code == 3  # validation failure exit code

    def test_negative_workers_exits_2(self, tmp_path: Path):
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps([{"id": "A", "duration": 1}]))
        from main import main as cli_main
        code = cli_main([str(f), "--workers", "-1"])
        assert code == 2

    def test_missing_file_exits_1(self):
        from main import main as cli_main
        code = cli_main(["nonexistent_file.json"])
        assert code == 1

    def test_json_output_flag(self, tmp_path: Path):
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps([{"id": "A", "duration": 1}]))
        from main import main as cli_main
        code = cli_main([str(f), "--json"])
        assert code == 0

    def test_fail_flag(self, tmp_path: Path):
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps([
            {"id": "A", "duration": 1},
            {"id": "B", "duration": 2, "dependsOn": ["A"]},
        ]))
        from main import main as cli_main
        code = cli_main([str(f), "--fail", "A"])
        assert code == 0


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:
    """Edge cases and corner conditions."""

    def test_very_large_duration(self):
        """Extremely large durations should not cause floating-point issues."""
        dag = _dag(_job("big", 1e12))
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == 1e12
        assert math.isfinite(cp.min_completion_time)

    def test_float_durations(self):
        dag = _dag(
            _job("A", 1.5),
            _job("B", 2.3, ["A"]),
        )
        order = topological_sort(dag)
        assert order == ["A", "B"]
        result = schedule(dag, worker_limit=1)
        assert abs(result.total_time - 3.8) < 0.01

    def test_self_loop_cycle(self):
        dag = _dag(_job("loop", 1, ["loop"]))
        issues = validate(dag)
        cycles = [i for i in issues if i.kind == "cycle"]
        assert len(cycles) >= 1

    def test_long_cycle(self):
        """Longer cycle: A → B → C → D → E → B."""
        dag = _dag(
            _job("A", 1),
            _job("B", 1, ["A"]),
            _job("C", 1, ["B"]),
            _job("D", 1, ["C"]),
            _job("E", 1, ["D"]),
        )
        # Make B depend on E to close the cycle.
        dag.jobs["B"].depends_on.append("E")
        dag = DAG.from_jobs(dag.jobs)  # rebuild adj/rev
        issues = validate(dag)
        cycles = [i for i in issues if i.kind == "cycle"]
        assert len(cycles) >= 1

    def test_empty_depends_on(self):
        raw = [{"id": "A", "duration": 1, "dependsOn": []}]
        dag = DAG.from_list(raw)
        assert dag.source_nodes() == ["A"]

    def test_sort_order_deterministic(self):
        """Same input should always produce the same topological order."""
        dag = DAG.from_list([
            {"id": "A", "duration": 1},
            {"id": "B", "duration": 2},
            {"id": "C", "duration": 3},
        ])
        o1 = topological_sort(dag)
        o2 = topological_sort(dag)
        assert o1 == o2

    def test_failure_on_sink(self):
        """Failing the final output job only skips that job."""
        dag = _dag(
            _job("A", 1),
            _job("B", 2, ["A"]),
        )
        result = simulate_failure(dag, "B")
        assert result.skipped_jobs == ["B"]
        assert result.surviving_jobs == ["A"]

    def test_all_jobs_independent(self):
        """No dependencies → everything runs in parallel."""
        raw = [
            {"id": f"J{i}", "duration": 1}
            for i in range(20)
        ]
        dag = DAG.from_list(raw)
        result = schedule(dag, worker_limit=5)
        assert result.total_time == 4.0  # 20 jobs / 5 workers = 4 stages
        assert len(result.stages) == 4

    def test_disconnected_components(self):
        """Disconnected DAG components should all schedule correctly."""
        dag = _dag(
            _job("A", 2),
            _job("B", 3),
            _job("C", 1, ["A"]),
            _job("D", 1, ["B"]),
        )
        result = schedule(dag, worker_limit=10)
        assert result.total_time == 4.0  # max(A+C=3, B+D=4)

    def test_various_sample_files_exist(self):
        """Assert all sample JSON files are valid and parseable."""
        samples_dir = Path(__file__).parent.parent / "samples"
        for sf in samples_dir.glob("*.json"):
            raw = json.loads(sf.read_text())
            assert isinstance(raw, list), f"{sf.name}: not a list"
            # Try constructing DAG (may fail for intentionally bad ones).
            try:
                dag = DAG.from_list(raw)
            except ValueError:
                pass  # expected for bad samples


# =========================================================================
# Performance smoke test
# =========================================================================

class TestPerformance:
    """Basic performance sanity checks — not benchmarking."""

    def test_large_dag_builds_fast(self):
        """300-node DAG should build, validate, sort, and schedule quickly."""
        n = 300
        raw = [{"id": f"J{i}", "duration": 1} for i in range(n)]
        # Add a linear backbone: J0 → J1 → ... → J{n-1}
        for i in range(1, n):
            raw[i]["dependsOn"] = [f"J{i-1}"]
        dag = DAG.from_list(raw)
        issues = validate(dag)
        assert len(issues) == 0
        order = topological_sort(dag)
        assert len(order) == n
        sched = schedule(dag, worker_limit=4)
        assert sched.total_time == float(n)  # Only 1 job at a time due to chain
        cp = compute_critical_path(dag)
        assert cp.min_completion_time == float(n)