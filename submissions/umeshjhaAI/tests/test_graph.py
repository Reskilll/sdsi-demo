"""Tests for topological ordering (M2)."""

import unittest

from scheduler.graph import topological_order
from scheduler.model import Job


def _make(*specs):
    """specs: (id, duration, [deps]) tuples."""
    return [Job(id=i, duration=d, depends_on=tuple(deps)) for i, d, deps in specs]


def _is_valid_order(order, jobs):
    """Every prerequisite appears before its dependent."""
    pos = {jid: i for i, jid in enumerate(order)}
    for job in jobs:
        for dep in job.depends_on:
            if pos[dep] >= pos[job.id]:
                return False
    return True


class TestTopologicalOrder(unittest.TestCase):
    def test_empty_graph(self):
        self.assertEqual(topological_order([]), [])

    def test_single_job(self):
        jobs = _make(("a", 1, []))
        self.assertEqual(topological_order(jobs), ["a"])

    def test_chain(self):
        jobs = _make(("a", 1, []), ("b", 1, ["a"]), ("c", 1, ["b"]))
        self.assertEqual(topological_order(jobs), ["a", "b", "c"])

    def test_independent_jobs_sorted(self):
        jobs = _make(("c", 1, []), ("a", 1, []), ("b", 1, []))
        self.assertEqual(topological_order(jobs), ["a", "b", "c"])

    def test_diamond(self):
        jobs = _make(
            ("a", 1, []),
            ("b", 1, ["a"]),
            ("c", 1, ["a"]),
            ("d", 1, ["b", "c"]),
        )
        order = topological_order(jobs)
        self.assertEqual(order, ["a", "b", "c", "d"])
        self.assertTrue(_is_valid_order(order, jobs))

    def test_multiple_dependencies(self):
        jobs = _make(
            ("a", 1, []),
            ("b", 1, []),
            ("c", 1, []),
            ("d", 1, ["a", "b", "c"]),
        )
        order = topological_order(jobs)
        self.assertEqual(order, ["a", "b", "c", "d"])
        self.assertTrue(_is_valid_order(order, jobs))

    def test_disconnected_components(self):
        jobs = _make(
            ("a", 1, []),
            ("b", 1, ["a"]),
            ("x", 1, []),
            ("y", 1, ["x"]),
        )
        order = topological_order(jobs)
        # lexicographic global ordering: a, b, x, y
        self.assertEqual(order, ["a", "b", "x", "y"])
        self.assertTrue(_is_valid_order(order, jobs))

    def test_lexicographic_not_input_order(self):
        # input ids are intentionally not sorted
        jobs = _make(("z", 1, []), ("a", 1, ["z"]), ("m", 1, ["z"]))
        order = topological_order(jobs)
        self.assertEqual(order, ["z", "a", "m"])

    def test_cycle_raises(self):
        jobs = _make(("a", 1, ["b"]), ("b", 1, ["a"]))
        with self.assertRaises(ValueError):
            topological_order(jobs)

    def test_deterministic(self):
        jobs = _make(
            ("b", 1, []),
            ("a", 1, []),
            ("d", 1, ["a", "b"]),
            ("c", 1, ["a"]),
        )
        self.assertEqual(topological_order(jobs), topological_order(jobs))


if __name__ == "__main__":
    unittest.main()
