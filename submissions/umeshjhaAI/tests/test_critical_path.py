"""Tests for critical-path analysis (M4)."""

import unittest

from scheduler.engine import critical_path_analysis
from scheduler.graph import topological_order
from scheduler.model import Job


def _make(*specs):
    return [Job(id=i, duration=d, depends_on=tuple(deps)) for i, d, deps in specs]


def _analyze(jobs):
    order = topological_order(jobs)
    return critical_path_analysis(jobs, order)


class TestCriticalPath(unittest.TestCase):
    def test_empty_graph(self):
        times, dur, path = _analyze([])
        self.assertEqual(times, {})
        self.assertEqual(dur, 0.0)
        self.assertEqual(path, [])

    def test_single_job(self):
        jobs = _make(("a", 4, []))
        times, dur, path = _analyze(jobs)
        self.assertEqual(dur, 4)
        self.assertEqual(path, ["a"])
        self.assertEqual(times["a"].earliest_start, 0)
        self.assertEqual(times["a"].earliest_finish, 4)

    def test_chain(self):
        jobs = _make(("a", 3, []), ("b", 2, ["a"]), ("c", 1, ["b"]))
        times, dur, path = _analyze(jobs)
        self.assertEqual(dur, 6)
        self.assertEqual(path, ["a", "b", "c"])

    def test_diamond(self):
        # a(1) -> b(3), c(5); d(1) depends on b,c. Critical: a -> c -> d = 7
        jobs = _make(
            ("a", 1, []),
            ("b", 3, ["a"]),
            ("c", 5, ["a"]),
            ("d", 1, ["b", "c"]),
        )
        times, dur, path = _analyze(jobs)
        self.assertEqual(dur, 7)
        self.assertEqual(path, ["a", "c", "d"])
        self.assertEqual(times["d"].earliest_start, 6)

    def test_multiple_dependencies_max_finish(self):
        jobs = _make(
            ("a", 2, []),
            ("b", 7, []),
            ("c", 3, ["a", "b"]),
        )
        times, dur, path = _analyze(jobs)
        self.assertEqual(dur, 10)  # b(7) + c(3)
        self.assertEqual(path, ["b", "c"])
        self.assertEqual(times["c"].earliest_start, 7)

    def test_disconnected_components_max_overall(self):
        jobs = _make(
            ("a", 1, []),
            ("b", 2, ["a"]),  # path = 3
            ("x", 10, []),      # path = 10
        )
        times, dur, path = _analyze(jobs)
        self.assertEqual(dur, 10)
        self.assertEqual(path, ["x"])

    def test_equal_duration_critical_paths_deterministic(self):
        # two equal-length paths: a->b (1+2=3) and a->c (1+2=3); tie broken by id
        jobs = _make(
            ("a", 1, []),
            ("b", 2, ["a"]),
            ("c", 2, ["a"]),
        )
        times, dur, path = _analyze(jobs)
        self.assertEqual(dur, 3)
        self.assertEqual(path, ["a", "b"])  # 'b' < 'c'

    def test_independent_jobs_max(self):
        jobs = _make(("a", 2, []), ("b", 9, []), ("c", 5, []))
        _, dur, path = _analyze(jobs)
        self.assertEqual(dur, 9)
        self.assertEqual(path, ["b"])


if __name__ == "__main__":
    unittest.main()
