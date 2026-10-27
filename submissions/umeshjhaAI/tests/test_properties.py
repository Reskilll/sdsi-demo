"""Randomized property-based tests over generated DAGs.

These are the only tests that do not hard-code expected outputs; instead they
assert three scheduling invariants that must hold for *any* valid acyclic input:

1. every stage contains at most ``workers`` jobs (worker limit),
2. every scheduled job's prerequisites finished in an earlier stage (readiness),
3. the critical-path duration is a lower bound on the worker-limited total.

The generator only produces DAGs, so no cycle is ever fed to the engine.
"""

import random
import unittest

from scheduler.engine import build_schedule


def _generate_dag(num_jobs: int, density: float, rng: random.Random):
    """Generate ``num_jobs`` jobs forming an acyclic graph.

    Edges only point from lower-indexed to higher-indexed jobs, guaranteeing no
    cycles. ``density`` is the probability that any valid edge is added.
    """
    jobs = []
    for i in range(num_jobs):
        deps = [
            f"j{j}" for j in range(i) if rng.random() < density
        ]
        jobs.append(
            {
                "id": f"j{i}",
                "duration": rng.choice([1, 2, 3, 5, 8]),
                "dependsOn": deps,
            }
        )
    return jobs


class TestRandomizedDAGProperties(unittest.TestCase):
    def _assert_invariants(self, raw_jobs, workers):
        from scheduler.validation import parse_jobs

        jobs, _, errors = parse_jobs({"jobs": raw_jobs, "workers": workers})
        self.assertEqual(errors, [], f"unexpected validation errors: {errors}")

        schedule = build_schedule(jobs, workers)

        # invariant 1: worker limit respected in every stage
        for stage in schedule.stages:
            self.assertLessEqual(
                len(stage.job_ids),
                workers,
                f"stage {stage.job_ids} exceeds worker limit {workers}",
            )

        # invariant 2: every job starts only after its prerequisites completed
        stage_index = {}
        for idx, stage in enumerate(schedule.stages):
            for jid in stage.job_ids:
                stage_index[jid] = idx
        by_id = {job.id: job for job in jobs}
        for job in jobs:
            for dep in job.depends_on:
                self.assertLess(
                    stage_index[dep],
                    stage_index[job.id],
                    f"{job.id} scheduled before its prerequisite {dep}",
                )

        # invariant 3: critical path is a lower bound on the worker-limited total
        self.assertLessEqual(
            schedule.critical_path_duration,
            schedule.total_time,
            "critical-path duration must never exceed the worker-limited total",
        )

        # deterministic: identical input yields identical schedule
        schedule2 = build_schedule(jobs, workers)
        self.assertEqual(schedule.stages, schedule2.stages)
        self.assertEqual(schedule.critical_path, schedule2.critical_path)

    def test_random_dags(self):
        rng = random.Random(20261027)
        for _ in range(200):
            n = rng.randint(0, 30)
            density = rng.choice([0.0, 0.1, 0.3, 0.6])
            workers = rng.randint(1, 8)
            raw_jobs = _generate_dag(n, density, rng)
            self._assert_invariants(raw_jobs, workers)

    def test_many_independent_jobs(self):
        # a stress case where readiness is trivial but worker limit binds
        raw_jobs = [
            {"id": f"j{i}", "duration": 1, "dependsOn": []}
            for i in range(50)
        ]
        self._assert_invariants(raw_jobs, 3)

    def test_deep_chain(self):
        # a deep chain stresses stage-by-stage readiness without recursion
        n = 100
        raw_jobs = [
            {
                "id": f"j{i}",
                "duration": 1,
                "dependsOn": ([f"j{i - 1}"] if i else []),
            }
            for i in range(n)
        ]
        self._assert_invariants(raw_jobs, 2)


if __name__ == "__main__":
    unittest.main()
