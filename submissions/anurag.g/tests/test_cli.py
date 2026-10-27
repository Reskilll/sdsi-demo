"""Test CLI entrypoint."""

import json
import pytest
from scheduler.__main__ import main
from scheduler.models import GraphLoadError


def test_validate_valid():
    rc = main(["validate", '{"jobs":[{"id":"A","duration":1}]}'])
    assert rc == 0


def test_validate_invalid():
    rc = main(["validate", '{"jobs":[{"id":"A","duration":1,"dependsOn":["A"]}]}'])
    assert rc == 1


def test_schedule():
    rc = main(["schedule", '{"jobs":[{"id":"A","duration":1}]}'])
    assert rc == 0


def test_schedule_with_fail():
    rc = main(["schedule", '{"jobs":[{"id":"A","duration":1}]}', "--failed", "A"])
    assert rc == 0


def test_fail_subcommand():
    rc = main(["fail", '{"jobs":[{"id":"A","duration":1}]}', "--failed", "A"])
    assert rc == 0


def test_fail_subcommand_missing_flag():
    rc = main(["fail", '{"jobs":[{"id":"A","duration":1}]}'])
    assert rc == 2  # argparse error


def test_fail_unknown_job():
    rc = main(["fail", '{"jobs":[{"id":"A","duration":1}]}', "--failed", "Z"])
    assert rc == 2


def test_file_not_found():
    rc = main(["validate", "/nonexistent/file.json"])
    assert rc == 2


def test_no_command():
    rc = main([])
    assert rc == 1


def test_bad_json():
    rc = main(["validate", "not json at all"])
    assert rc == 2


def test_workers_flag():
    rc = main(["schedule", '{"jobs":[{"id":"A","duration":1}]}', "--workers", "5"])
    assert rc == 0


def test_negative_workers():
    rc = main(["schedule", '{"jobs":[{"id":"A","duration":1}]}', "--workers", "-1"])
    assert rc == 2