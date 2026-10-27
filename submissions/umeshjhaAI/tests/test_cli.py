"""End-to-end CLI tests via subprocess."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.py"


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(MAIN), *args],
        capture_output=True,
        text=True,
        cwd=cwd or str(ROOT),
    )


def _write_json(payload):
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(payload, tmp)
    tmp.close()
    return tmp.name


SAMPLE = {
    "jobs": [
        {"id": "extract", "duration": 3, "dependsOn": []},
        {"id": "validate", "duration": 2, "dependsOn": ["extract"]},
        {"id": "transform", "duration": 4, "dependsOn": ["extract"]},
        {"id": "load", "duration": 2, "dependsOn": ["validate", "transform"]},
    ],
    "workers": 2,
}


class TestCLI(unittest.TestCase):
    def test_sample_text_output(self):
        path = _write_json(SAMPLE)
        try:
            result = _run("--input", path)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Topological order", result.stdout)
            # after extract, "transform" < "validate" lexicographically
            self.assertIn("extract -> transform -> validate -> load", result.stdout)
            self.assertIn("Total completion time", result.stdout)
        finally:
            os.unlink(path)

    def test_sample_json_output_valid_and_contains_all_analyses(self):
        path = _write_json(SAMPLE)
        try:
            result = _run("--input", path, "--format", "json")
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)  # no noise on stdout
            self.assertEqual(data["workers"], 2)
            self.assertEqual(
                data["topological_order"],
                ["extract", "transform", "validate", "load"],
            )
            # with 2 workers: stage1 {extract}=3, stage2 {validate,transform}=4,
            # stage3 {load}=2 -> total 9
            self.assertEqual(data["total_completion_time"], 9)
            self.assertEqual(data["critical_path"], ["extract", "transform", "load"])
            self.assertEqual(data["critical_path_duration"], 9)
            self.assertIn("stages", data)
            self.assertIsNone(data["skipped_jobs"])
        finally:
            os.unlink(path)

    def test_workers_override(self):
        path = _write_json(SAMPLE)
        try:
            result = _run("--input", path, "--workers", "10", "--format", "json")
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data["workers"], 10)
        finally:
            os.unlink(path)

    def test_failed_job(self):
        path = _write_json(SAMPLE)
        try:
            result = _run("--input", path, "--failed-job", "transform", "--format", "json")
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertEqual(data["skipped_jobs"], ["load"])
        finally:
            os.unlink(path)

    def test_unknown_failed_job_exits_nonzero(self):
        path = _write_json(SAMPLE)
        try:
            result = _run("--input", path, "--failed-job", "ghost")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown failed job", result.stderr)
            self.assertEqual(result.stdout, "")
        finally:
            os.unlink(path)

    def test_cycle_exits_nonzero(self):
        payload = {
            "jobs": [
                {"id": "a", "duration": 1, "dependsOn": ["b"]},
                {"id": "b", "duration": 1, "dependsOn": ["a"]},
            ]
        }
        path = _write_json(payload)
        try:
            result = _run("--input", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cycle", result.stderr)
        finally:
            os.unlink(path)

    def test_malformed_json_exits_nonzero(self):
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write("{ not valid json")
        tmp.close()
        try:
            result = _run("--input", tmp.name)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("malformed JSON", result.stderr)
        finally:
            os.unlink(tmp.name)

    def test_invalid_workers_cli_exits_nonzero(self):
        path = _write_json(SAMPLE)
        try:
            result = _run("--input", path, "--workers", "0")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("workers", result.stderr)
        finally:
            os.unlink(path)

    def test_deterministic_across_runs(self):
        path = _write_json(SAMPLE)
        try:
            r1 = _run("--input", path, "--format", "json")
            r2 = _run("--input", path, "--format", "json")
            self.assertEqual(r1.stdout, r2.stdout)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
