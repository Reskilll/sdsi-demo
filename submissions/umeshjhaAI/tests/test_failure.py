"""Tests for downstream failure propagation (M5)."""

import unittest

from scheduler.engine import propagate_failure
from scheduler.model import Job


def _make(*specs):
    return [Job(id=i, duration=d, depends_on=tuple(deps)) for i, d, deps in specs]


class TestFailurePropagation(unittest.TestCase):
    def test_empty_graph_unknown_job_raises(self):
        # an empty graph has no known job ids, so any failed id is unknown
        with self.assertRaises(ValueError):
            propagate_failure([], "x")

    def test_job_with_no_dependents(self):
        jobs = _make(("a", 1, []), ("b", 1, ["a"]))
        self.assertEqual(propagate_failure(jobs, "b"), [])

    def test_multi_branch_downstream(self):
        # A -> B -> D, A -> C -> E. Failure of B skips D only.
        jobs = _make(
            ("a", 1, []),
            ("b", 1, ["a"]),
            ("c", 1, ["a"]),
            ("d", 1, ["b"]),
            ("e", 1, ["c"]),
        )
        self.assertEqual(propagate_failure(jobs, "b"), ["d"])

    def test_failure_of_root_skips_all_downstream(self):
        jobs = _make(
            ("a", 1, []),
            ("b", 1, ["a"]),
            ("c", 1, ["a"]),
            ("d", 1, ["b"]),
            ("e", 1, ["c"]),
        )
        self.assertEqual(propagate_failure(jobs, "a"), ["b", "c", "d", "e"])

    def test_transitive_indirect_dependents(self):
        jobs = _make(("a", 1, []), ("b", 1, ["a"]), ("c", 1, ["b"]), ("d", 1, ["c"]))
        self.assertEqual(propagate_failure(jobs, "a"), ["b", "c", "d"])

    def test_prerequisite_not_skipped(self):
        jobs = _make(("a", 1, []), ("b", 1, ["a"]))
        self.assertEqual(propagate_failure(jobs, "b"), [])  # 'a' not skipped

    def test_one_prerequisite_fails(self):
        # d depends on b and c; if b fails, d is skipped (c not skipped)
        jobs = _make(
            ("a", 1, []),
            ("b", 1, ["a"]),
            ("c", 1, ["a"]),
            ("d", 1, ["b", "c"]),
        )
        self.assertEqual(propagate_failure(jobs, "b"), ["d"])

    def test_unknown_failed_job_raises(self):
        jobs = _make(("a", 1, []))
        with self.assertRaises(ValueError):
            propagate_failure(jobs, "ghost")

    def test_deterministic_order(self):
        jobs = _make(
            ("a", 1, []),
            ("b", 1, ["a"]),
            ("c", 1, ["a"]),
            ("d", 1, ["b"]),
        )
        self.assertEqual(propagate_failure(jobs, "a"), ["b", "c", "d"])


if __name__ == "__main__":
    unittest.main()
