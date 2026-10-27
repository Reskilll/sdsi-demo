"""Tests for input validation (M1)."""

import math
import unittest

from scheduler.validation import parse_jobs


def _ids(jobs):
    return [job.id for job in jobs]


class TestValidationBasics(unittest.TestCase):
    def test_valid_graph(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": 1, "dependsOn": []},
                {"id": "b", "duration": 2, "dependsOn": ["a"]},
            ],
            "workers": 2,
        }
        jobs, workers, errors = parse_jobs(raw)
        self.assertEqual(errors, [])
        self.assertEqual(workers, 2)
        self.assertEqual(_ids(jobs), ["a", "b"])
        self.assertEqual(jobs[0].duration, 1.0)
        self.assertEqual(jobs[1].depends_on, ("a",))

    def test_empty_jobs(self):
        jobs, workers, errors = parse_jobs({"jobs": []})
        self.assertEqual(errors, [])
        self.assertEqual(jobs, [])
        self.assertEqual(workers, 1)

    def test_default_workers_is_one(self):
        jobs, workers, errors = parse_jobs(
            {"jobs": [{"id": "a", "duration": 1}]}
        )
        self.assertEqual(errors, [])
        self.assertEqual(workers, 1)

    def test_workers_override(self):
        raw = {"jobs": [{"id": "a", "duration": 1}], "workers": 3}
        _, workers, errors = parse_jobs(raw, workers_override=5)
        self.assertEqual(errors, [])
        self.assertEqual(workers, 5)

    def test_fractional_duration(self):
        raw = {"jobs": [{"id": "a", "duration": 0.5}]}
        jobs, _, errors = parse_jobs(raw)
        self.assertEqual(errors, [])
        self.assertEqual(jobs[0].duration, 0.5)


class TestTopLevelStructure(unittest.TestCase):
    def test_non_object_input(self):
        _, _, errors = parse_jobs([1, 2, 3])
        self.assertEqual(
            errors, ["input must be a JSON object with a 'jobs' key"]
        )

    def test_missing_jobs_key(self):
        _, _, errors = parse_jobs({"workers": 2})
        self.assertEqual(errors, ["input is missing the required 'jobs' key"])

    def test_jobs_not_list(self):
        _, _, errors = parse_jobs({"jobs": {"id": "a"}})
        self.assertEqual(errors, ["'jobs' must be a list"])

    def test_job_not_object(self):
        raw = {"jobs": ["not-an-object"]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be an object", errors[0])


class TestIdValidation(unittest.TestCase):
    def test_missing_id(self):
        raw = {"jobs": [{"duration": 1}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing required 'id'", errors[0])

    def test_non_string_id(self):
        raw = {"jobs": [{"id": 5, "duration": 1}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a string", errors[0])

    def test_empty_id(self):
        raw = {"jobs": [{"id": "", "duration": 1}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("non-empty", errors[0])

    def test_duplicate_id(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": 1},
                {"id": "a", "duration": 2},
            ]
        }
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate job id", errors[0])

    def test_numeric_like_and_punctuated_ids(self):
        raw = {
            "jobs": [
                {"id": "10", "duration": 1},
                {"id": "job.name-1", "duration": 1},
                {"id": "2", "duration": 1, "dependsOn": ["10"]},
            ]
        }
        jobs, _, errors = parse_jobs(raw)
        self.assertEqual(errors, [])
        self.assertEqual(_ids(jobs), ["10", "job.name-1", "2"])


class TestDurationValidation(unittest.TestCase):
    def test_missing_duration(self):
        raw = {"jobs": [{"id": "a"}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing required 'duration'", errors[0])

    def test_non_numeric_duration(self):
        raw = {"jobs": [{"id": "a", "duration": "fast"}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a number", errors[0])

    def test_bool_duration(self):
        raw = {"jobs": [{"id": "a", "duration": True}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("not a boolean", errors[0])

    def test_zero_duration(self):
        raw = {"jobs": [{"id": "a", "duration": 0}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be positive", errors[0])

    def test_negative_duration(self):
        raw = {"jobs": [{"id": "a", "duration": -3}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be positive", errors[0])

    def test_nan_duration(self):
        raw = {"jobs": [{"id": "a", "duration": float("nan")}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("finite", errors[0])

    def test_infinity_duration(self):
        raw = {"jobs": [{"id": "a", "duration": float("inf")}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("finite", errors[0])


class TestDependsOnValidation(unittest.TestCase):
    def test_depends_on_not_list(self):
        raw = {"jobs": [{"id": "a", "duration": 1, "dependsOn": "b"}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a list", errors[0])

    def test_non_string_dependency(self):
        raw = {"jobs": [{"id": "a", "duration": 1, "dependsOn": [1]}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be strings", errors[0])

    def test_missing_dependency_reference(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": 1, "dependsOn": ["ghost"]},
            ]
        }
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("depends on missing job 'ghost'", errors[0])
        self.assertIn("'a'", errors[0])

    def test_self_dependency(self):
        raw = {"jobs": [{"id": "a", "duration": 1, "dependsOn": ["a"]}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot depend on itself", errors[0])


class TestWorkerValidation(unittest.TestCase):
    def test_zero_workers(self):
        raw = {"jobs": [{"id": "a", "duration": 1}], "workers": 0}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn(">= 1", errors[0])

    def test_negative_workers(self):
        raw = {"jobs": [{"id": "a", "duration": 1}], "workers": -2}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)

    def test_float_workers(self):
        raw = {"jobs": [{"id": "a", "duration": 1}], "workers": 2.5}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("integer", errors[0])

    def test_bool_workers(self):
        raw = {"jobs": [{"id": "a", "duration": 1}], "workers": True}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("integer", errors[0])


class TestCycleDetection(unittest.TestCase):
    def test_two_job_cycle(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": 1, "dependsOn": ["b"]},
                {"id": "b", "duration": 1, "dependsOn": ["a"]},
            ]
        }
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("cycle", errors[0])
        self.assertIn("a -> b -> a", errors[0])

    def test_longer_cycle(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": 1, "dependsOn": ["c"]},
                {"id": "b", "duration": 1, "dependsOn": ["a"]},
                {"id": "c", "duration": 1, "dependsOn": ["b"]},
            ]
        }
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("a -> b -> c -> a", errors[0])

    def test_cycle_in_one_component_only(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": 1, "dependsOn": ["b"]},
                {"id": "b", "duration": 1, "dependsOn": ["a"]},
                {"id": "x", "duration": 1},
                {"id": "y", "duration": 1, "dependsOn": ["x"]},
            ]
        }
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("cycle", errors[0])

    def test_self_dependency_reported_as_error_not_cycle(self):
        raw = {"jobs": [{"id": "a", "duration": 1, "dependsOn": ["a"]}]}
        _, _, errors = parse_jobs(raw)
        self.assertEqual(len(errors), 1)
        self.assertIn("itself", errors[0])


class TestErrorAggregation(unittest.TestCase):
    def test_multiple_independent_errors(self):
        raw = {
            "jobs": [
                {"id": "a", "duration": -1},
                {"id": "b", "duration": "x", "dependsOn": ["a"]},
                {"id": "", "duration": 1},
                {"id": "a", "duration": 1},
            ],
            "workers": True,
        }
        _, _, errors = parse_jobs(raw)
        self.assertGreaterEqual(len(errors), 4)
        joined = "; ".join(errors)
        self.assertIn("positive", joined)
        self.assertIn("non-empty", joined)
        self.assertIn("duplicate", joined)
        self.assertIn("workers", joined)


if __name__ == "__main__":
    unittest.main()
