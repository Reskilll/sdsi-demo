"""Test suite for the Job Scheduler DAG.

Run with::

    python -m pytest test_scheduler.py -v
    # or
    python -m unittest test_scheduler.py -v
"""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from scheduler import Job, JobGraph, ValidationError, ValidationReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _graph(d: dict) -> JobGraph:
    """Convenience: build a JobGraph from an inline dict."""
    return JobGraph.from_dict(d)


# ---------------------------------------------------------------------------
# M1 — Graph validation
# ---------------------------------------------------------------------------

class TestValidation(unittest.TestCase):
    """Detect cycles and missing dependencies."""

    def test_valid_trivial_graph(self) -> None:
        g = _graph({"a": {"duration": 1, "dependsOn": []}})
        report = g.validate()
        self.assertTrue(report.is_valid)

    def test_missing_dependency(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": ["ghost"]},
            "b": {"duration": 2, "dependsOn": ["a"]},
        })
        report = g.validate()
        self.assertFalse(report.is_valid)
        missing = [e for e in report.errors if e.kind == "missing_dependency"]
        self.assertEqual(len(missing), 1)
        self.assertIn("ghost", missing[0].detail)

    def test_simple_cycle(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": ["b"]},
            "b": {"duration": 2, "dependsOn": ["a"]},
        })
        report = g.validate()
        self.assertFalse(report.is_valid)
        cycles = [e for e in report.errors if e.kind == "cycle"]
        self.assertGreaterEqual(len(cycles), 1)

    def test_self_loop(self) -> None:
        g = _graph({"a": {"duration": 1, "dependsOn": ["a"]}})
        report = g.validate()
        self.assertFalse(report.is_valid)
        cycles = [e for e in report.errors if e.kind == "cycle"]
        self.assertGreaterEqual(len(cycles), 1)
        self.assertIn("a", cycles[0].path)

    def test_long_cycle(self) -> None:
        g = _graph({
            "1": {"duration": 1, "dependsOn": ["4"]},
            "2": {"duration": 1, "dependsOn": ["1"]},
            "3": {"duration": 1, "dependsOn": ["2"]},
            "4": {"duration": 1, "dependsOn": ["3"]},
        })
        report = g.validate()
        self.assertFalse(report.is_valid)
        cycles = [e for e in report.errors if e.kind == "cycle"]
        self.assertGreaterEqual(len(cycles), 1)
        # Cycle path should contain all four nodes
        self.assertEqual(len(cycles[0].path), 5)  # start repeated at end: A→B→C→D→A

    def test_diamond_is_valid(self) -> None:
        """Diamond dependencies are acyclic even though multiple paths exist."""
        g = _graph({
            "a": {"duration": 1, "dependsOn": []},
            "b": {"duration": 2, "dependsOn": ["a"]},
            "c": {"duration": 3, "dependsOn": ["a"]},
            "d": {"duration": 1, "dependsOn": ["b", "c"]},
        })
        self.assertTrue(g.validate().is_valid)

    def test_multiple_errors_reported(self) -> None:
        """Both missing deps and cycles should be reported in one pass."""
        g = _graph({
            "a": {"duration": 1, "dependsOn": ["b", "missing"]},
            "b": {"duration": 1, "dependsOn": ["a"]},
        })
        report = g.validate()
        kinds = {e.kind for e in report.errors}
        self.assertIn("cycle", kinds)
        self.assertIn("missing_dependency", kinds)


# ---------------------------------------------------------------------------
# M2 — Topological order
# ---------------------------------------------------------------------------

class TestTopologicalOrder(unittest.TestCase):
    """Kahn's algorithm produces a valid linear extension."""

    def test_single_node(self) -> None:
        self.assertEqual(_graph({"x": {"duration": 0}}).topological_order(), ["x"])

    def test_linear_chain(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": []},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "c": {"duration": 1, "dependsOn": ["b"]},
        })
        self.assertEqual(g.topological_order(), ["a", "b", "c"])

    def test_diamond(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": []},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "c": {"duration": 1, "dependsOn": ["a"]},
            "d": {"duration": 1, "dependsOn": ["b", "c"]},
        })
        order = g.topological_order()
        # Structural invariants
        self.assertEqual(len(order), 4)
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("a"), order.index("c"))
        self.assertLess(order.index("b"), order.index("d"))
        self.assertLess(order.index("c"), order.index("d"))

    def test_disconnected_components(self) -> None:
        g = _graph({
            "a": {"duration": 1},
            "b": {"duration": 1},
            "c": {"duration": 1},
        })
        order = g.topological_order()
        self.assertEqual(set(order), {"a", "b", "c"})

    def test_raises_on_invalid_graph(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": ["b"]},
            "b": {"duration": 1, "dependsOn": ["a"]},
        })
        with self.assertRaises(ValueError):
            g.topological_order()


# ---------------------------------------------------------------------------
# M3 — Parallel stages
# ---------------------------------------------------------------------------

class TestParallelStages(unittest.TestCase):
    """Batching ready jobs into stages, respecting worker_limit."""

    def test_sequential_chain(self) -> None:
        g = _graph({
            "a": {"duration": 1},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "c": {"duration": 1, "dependsOn": ["b"]},
        })
        stages = g.parallel_stages()
        self.assertEqual(stages, [["a"], ["b"], ["c"]])

    def test_diamond_stages(self) -> None:
        g = _graph({
            "a": {"duration": 1},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "c": {"duration": 1, "dependsOn": ["a"]},
            "d": {"duration": 1, "dependsOn": ["b", "c"]},
        })
        stages = g.parallel_stages()
        self.assertEqual(stages, [["a"], ["b", "c"], ["d"]])

    def test_fully_parallel(self) -> None:
        g = _graph({
            "a": {"duration": 1}, "b": {"duration": 1}, "c": {"duration": 1},
        })
        stages = g.parallel_stages()
        self.assertEqual(stages, [["a", "b", "c"]])

    def test_worker_limit_splits_stage(self) -> None:
        g = _graph({
            "a": {"duration": 1}, "b": {"duration": 1}, "c": {"duration": 1},
        })
        stages = g.parallel_stages(worker_limit=2)
        # Stage 0: 2 jobs; stage 1: 1 job
        self.assertEqual(len(stages), 2)
        self.assertEqual(stages[0], ["a", "b"])
        self.assertEqual(stages[1], ["c"])

    def test_worker_limit_zero_means_unlimited(self) -> None:
        g = _graph({
            "a": {"duration": 1}, "b": {"duration": 1}, "c": {"duration": 1},
        })
        self.assertEqual(len(g.parallel_stages(worker_limit=0)), 1)

    def test_worker_limit_negative_raises(self) -> None:
        g = _graph({"a": {"duration": 1}})
        with self.assertRaises(ValueError):
            g.parallel_stages(worker_limit=-1)

    def test_complex_stages(self) -> None:
        """Graph from the sample: two parallel paths."""
        g = _graph({
            "fetch": {"duration": 2},
            "parse_a": {"duration": 1, "dependsOn": ["fetch"]},
            "parse_b": {"duration": 1, "dependsOn": ["fetch"]},
            "join": {"duration": 2, "dependsOn": ["parse_a", "parse_b"]},
            "export": {"duration": 1, "dependsOn": ["join"]},
        })
        stages = g.parallel_stages()
        self.assertEqual(
            stages,
            [["fetch"], ["parse_a", "parse_b"], ["join"], ["export"]],
        )


# ---------------------------------------------------------------------------
# M4 — Critical path
# ---------------------------------------------------------------------------

class TestCriticalPath(unittest.TestCase):
    """Longest path through the DAG."""

    def test_single_node(self) -> None:
        path, duration = _graph({"a": {"duration": 5}}).critical_path()
        self.assertEqual(path, ["a"])
        self.assertEqual(duration, 5.0)

    def test_linear_chain(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": []},
            "b": {"duration": 2, "dependsOn": ["a"]},
            "c": {"duration": 3, "dependsOn": ["b"]},
        })
        path, duration = g.critical_path()
        self.assertEqual(path, ["a", "b", "c"])
        self.assertEqual(duration, 6.0)

    def test_diamond_picks_longer_branch(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": []},
            "b": {"duration": 5, "dependsOn": ["a"]},   # longer
            "c": {"duration": 2, "dependsOn": ["a"]},   # shorter
            "d": {"duration": 1, "dependsOn": ["b", "c"]},
        })
        path, duration = g.critical_path()
        self.assertEqual(path, ["a", "b", "d"])
        self.assertEqual(duration, 7.0)

    def test_disjoint_paths(self) -> None:
        """Two independent chains — critical path is the longer one."""
        g = _graph({
            "a": {"duration": 1},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "x": {"duration": 3},
            "y": {"duration": 3, "dependsOn": ["x"]},
        })
        _, duration = g.critical_path()
        self.assertEqual(duration, 6.0)


# ---------------------------------------------------------------------------
# M5 — Failure simulation
# ---------------------------------------------------------------------------

class TestFailureSimulation(unittest.TestCase):
    """Downstream job propagation."""

    def setUp(self) -> None:
        self.graph = _graph({
            "a": {"duration": 1},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "c": {"duration": 1, "dependsOn": ["a"]},
            "d": {"duration": 1, "dependsOn": ["b"]},
            "e": {"duration": 1, "dependsOn": ["c"]},
            "f": {"duration": 1, "dependsOn": ["d", "e"]},
        })

    def test_fail_root_skips_all(self) -> None:
        self.assertEqual(self.graph.downstream_jobs("a"), ["b", "c", "d", "e", "f"])

    def test_fail_leaf_skips_none(self) -> None:
        self.assertEqual(self.graph.downstream_jobs("f"), [])

    def test_fail_mid_branch(self) -> None:
        self.assertEqual(self.graph.downstream_jobs("b"), ["d", "f"])

    def test_fail_missing_job_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.graph.downstream_jobs("zzz")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation(unittest.TestCase):
    """Malformed input should produce clear, immediate errors."""

    def test_non_dict_input(self) -> None:
        with self.assertRaises(TypeError):
            JobGraph.from_dict([1, 2, 3])  # type: ignore[arg-type]

    def test_non_dict_job_spec(self) -> None:
        with self.assertRaises(TypeError):
            _graph({"a": "not-an-object"})  # type: ignore[dict-item]

    def test_missing_duration(self) -> None:
        with self.assertRaises(KeyError):
            _graph({"a": {"dependsOn": []}})  # type: ignore[typeddict-item]

    def test_negative_duration(self) -> None:
        with self.assertRaises(ValueError):
            _graph({"a": {"duration": -1}})

    def test_non_numeric_duration(self) -> None:
        with self.assertRaises(ValueError):
            _graph({"a": {"duration": "slow"}})  # type: ignore[arg-type]

    def test_non_list_depends_on(self) -> None:
        with self.assertRaises(TypeError):
            _graph({"a": {"duration": 1, "dependsOn": "a"}})  # type: ignore[arg-type]

    def test_non_string_dependency(self) -> None:
        with self.assertRaises(TypeError):
            _graph({"a": {"duration": 1, "dependsOn": [42]}})  # type: ignore[list-item]

    def test_empty_graph(self) -> None:
        with self.assertRaises(ValueError):
            _graph({})


# ---------------------------------------------------------------------------
# Full schedule integration
# ---------------------------------------------------------------------------

class TestSchedule(unittest.TestCase):
    def test_valid_schedule(self) -> None:
        g = _graph({
            "fetch": {"duration": 2},
            "parse": {"duration": 1, "dependsOn": ["fetch"]},
            "export": {"duration": 1, "dependsOn": ["parse"]},
        })
        result = g.schedule(worker_limit=2)
        self.assertTrue(result["valid"])
        self.assertEqual(result["job_count"], 3)
        self.assertEqual(result["topological_order"], ["fetch", "parse", "export"])
        self.assertEqual(result["stage_count"], 3)
        self.assertEqual(result["min_completion_time_seconds"], 4.0)

    def test_invalid_schedule(self) -> None:
        g = _graph({
            "a": {"duration": 1, "dependsOn": ["b"]},
            "b": {"duration": 1, "dependsOn": ["a"]},
        })
        result = g.schedule()
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["kind"] == "cycle" for e in result["errors"]))


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

class TestFileIO(unittest.TestCase):
    def test_roundtrip(self) -> None:
        data = {
            "a": {"duration": 1, "dependsOn": []},
            "b": {"duration": 2, "dependsOn": ["a"]},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            tmp = f.name
        try:
            g = JobGraph.from_file(tmp)
            self.assertEqual(g.topological_order(), ["a", "b"])
        finally:
            Path(tmp).unlink()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):
    def test_zero_duration_jobs(self) -> None:
        g = _graph({
            "a": {"duration": 0},
            "b": {"duration": 0, "dependsOn": ["a"]},
        })
        self.assertTrue(g.validate().is_valid)
        path, duration = g.critical_path()
        self.assertEqual(duration, 0.0)

    def test_same_duration_branches(self) -> None:
        """When both branches have equal weight, the critical path picks one."""
        g = _graph({
            "a": {"duration": 1},
            "b": {"duration": 2, "dependsOn": ["a"]},
            "c": {"duration": 2, "dependsOn": ["a"]},
            "d": {"duration": 1, "dependsOn": ["b", "c"]},
        })
        p, t = g.critical_path()
        self.assertEqual(t, 4.0)
        # Either [a,b,d] or [a,c,d] is valid
        self.assertIn(p, (["a", "b", "d"], ["a", "c", "d"]))

    def test_large_graph_no_regression(self) -> None:
        """Stress test: a chain of 1 000 jobs should compute instantly."""
        n = 1000
        jobs: dict = {}
        for i in range(n):
            jobs[str(i)] = {"duration": 0.001, "dependsOn": [] if i == 0 else [str(i - 1)]}
        g = JobGraph.from_dict(jobs)
        order = g.topological_order()
        self.assertEqual(len(order), n)
        _, t = g.critical_path()
        self.assertAlmostEqual(t, n * 0.001)

    def test_disconnected_with_one_dependent(self) -> None:
        g = _graph({
            "a": {"duration": 1},
            "b": {"duration": 1, "dependsOn": ["a"]},
            "x": {"duration": 5},   # independent chain, longer
        })
        p, t = g.critical_path()
        self.assertEqual(t, 5.0)

    def test_depends_on_empty_default(self) -> None:
        g = JobGraph.from_dict({"a": {"duration": 1}})
        self.assertEqual(g.jobs["a"].depends_on, [])

    def test_float_duration(self) -> None:
        g = _graph({"a": {"duration": 1.5}})
        self.assertAlmostEqual(g.critical_path()[1], 1.5)


if __name__ == "__main__":
    unittest.main()