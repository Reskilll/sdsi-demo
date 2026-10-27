"""Tests for worker-limited barrier stage scheduling (M3)."""

import unittest

from scheduler.engine import build_stages
from scheduler.model import Job


def _make(*specs):
    return [Job(id=i, duration=d, depends_on=tuple(deps)) for i, d, deps in specs]


def _all_ids(stages):
    return [jid for stage in stages for jid in stage.job_ids]


class TestStageScheduling(unittest.TestCase):
    def test_empty_graph(self):
        stages, total = build_stages([], 2)
        self.assertEqual(stages, [])
        self.assertEqual(total, 0.0)

    def test_single_job(self):
        stages, total = build_stages(_make(("a", 3, [])), 2)
        self.assertEqual([list(s.job_ids) for s in stages], [["a"]])
        self.assertEqual(stages[0].duration, 3)
        self.assertEqual(total, 3)

    def test_spec_example_three_independent_two_workers(self):
        # durations 2, 5, 3 with 2 workers -> stage1 {2,5}=5, stage2 {3}=3 -> 8
        stages, total = build_stages(
            _make(("a", 2, []), ("b", 5, []), ("c", 3, [])), 2
        )
        self.assertEqual([list(s.job_ids) for s in stages], [["a", "b"], ["c"]])
        self.assertEqual([s.duration for s in stages], [5, 3])
        self.assertEqual(total, 8)

    def test_worker_limit_respected_every_stage(self):
        jobs = _make(*[(f"j{i}", 1, []) for i in range(10)])
        stages, _ = build_stages(jobs, 3)
        for stage in stages:
            self.assertLessEqual(len(stage.job_ids), 3)

    def test_workers_greater_than_job_count(self):
        jobs = _make(("a", 1, []), ("b", 2, []), ("c", 3, []))
        stages, total = build_stages(jobs, 10)
        self.assertEqual(len(stages), 1)
        self.assertEqual(list(stages[0].job_ids), ["a", "b", "c"])
        self.assertEqual(stages[0].duration, 3)
        self.assertEqual(total, 3)

    def test_workers_equal_one_serializes(self):
        jobs = _make(("a", 2, []), ("b", 3, []), ("c", 1, []))
        stages, total = build_stages(jobs, 1)
        self.assertEqual([list(s.job_ids) for s in stages], [["a"], ["b"], ["c"]])
        self.assertEqual(total, 6)

    def test_dependency_readiness(self):
        # chain: a -> b -> c
        jobs = _make(("a", 1, []), ("b", 1, ["a"]), ("c", 1, ["b"]))
        stages, total = build_stages(jobs, 3)
        # all three must be in separate stages despite 3 workers
        self.assertEqual(len(stages), 3)
        self.assertEqual(_all_ids(stages), ["a", "b", "c"])

    def test_dependent_never_in_same_stage_as_prereq(self):
        jobs = _make(("a", 5, []), ("b", 1, ["a"]))
        stages, _ = build_stages(jobs, 5)
        self.assertEqual(len(stages), 2)
        self.assertEqual(list(stages[0].job_ids), ["a"])
        self.assertEqual(list(stages[1].job_ids), ["b"])

    def test_stage_duration_is_max(self):
        jobs = _make(("a", 2, []), ("b", 9, []), ("c", 4, []))
        stages, _ = build_stages(jobs, 2)
        self.assertEqual(stages[0].duration, 9)

    def test_greedy_choice_affects_completion(self):
        # Two chains: a(5)->b(5) and c(1)->d(1). With 2 workers:
        # stage1 {a,c}=5, stage2 {b,d}=5 -> 10 (greedy packs a+c first)
        jobs = _make(
            ("a", 5, []),
            ("b", 5, ["a"]),
            ("c", 1, []),
            ("d", 1, ["c"]),
        )
        stages, total = build_stages(jobs, 2)
        self.assertEqual([list(s.job_ids) for s in stages], [["a", "c"], ["b", "d"]])
        self.assertEqual(total, 10)

    def test_fractional_durations(self):
        jobs = _make(("a", 0.5, []), ("b", 1.5, []))
        stages, total = build_stages(jobs, 2)
        self.assertEqual(stages[0].duration, 1.5)
        self.assertEqual(total, 1.5)

    def test_deterministic(self):
        jobs = _make(("b", 1, []), ("a", 1, []), ("c", 1, ["a", "b"]))
        s1, t1 = build_stages(jobs, 2)
        s2, t2 = build_stages(jobs, 2)
        self.assertEqual(s1, s2)
        self.assertEqual(t1, t2)


if __name__ == "__main__":
    unittest.main()
