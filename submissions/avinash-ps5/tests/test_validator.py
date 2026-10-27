"""Tests for input validation."""

import pytest

from dag_scheduler.validator import ValidationError, validate_and_parse


# ---------------------------------------------------------------------------
# Happy-path parsing
# ---------------------------------------------------------------------------

def test_simple_valid_input():
    data = {
        "workerLimit": 2,
        "jobs": [
            {"name": "A", "duration": 5, "dependsOn": []},
            {"name": "B", "duration": 3, "dependsOn": ["A"]},
        ],
    }
    result = validate_and_parse(data)
    assert result.worker_limit == 2
    assert len(result.jobs) == 2
    assert result.jobs["B"].depends_on == ["A"]
    assert result.jobs["A"].duration == 5.0


def test_default_worker_limit():
    data = {"jobs": [{"name": "X", "duration": 1, "dependsOn": []}]}
    result = validate_and_parse(data)
    assert result.worker_limit == 4  # default


def test_dependsOn_as_empty_list():
    data = {"jobs": [{"name": "J", "duration": 2, "dependsOn": []}]}
    result = validate_and_parse(data)
    assert result.jobs["J"].depends_on == []


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_missing_jobs_key():
    with pytest.raises(ValidationError, match="Missing required key: 'jobs'"):
        validate_and_parse({"workerLimit": 3})


def test_empty_jobs_list():
    with pytest.raises(ValidationError, match="'jobs' list is empty"):
        validate_and_parse({"jobs": []})


def test_jobs_not_a_list():
    with pytest.raises(ValidationError, match="'jobs' must be a list"):
        validate_and_parse({"jobs": "not-a-list"})


def test_missing_job_name():
    with pytest.raises(ValidationError, match="missing required field 'name'"):
        validate_and_parse({"jobs": [{"duration": 1, "dependsOn": []}]})


def test_empty_job_name():
    with pytest.raises(ValidationError, match="'name' must be a non-empty string"):
        validate_and_parse({"jobs": [{"name": "", "duration": 1, "dependsOn": []}]})


def test_duplicate_job_name():
    with pytest.raises(ValidationError, match="duplicate job name 'A'"):
        validate_and_parse(
            {
                "jobs": [
                    {"name": "A", "duration": 1, "dependsOn": []},
                    {"name": "A", "duration": 2, "dependsOn": []},
                ]
            }
        )


def test_negative_duration():
    with pytest.raises(ValidationError, match="'duration' must be >= 0"):
        validate_and_parse({"jobs": [{"name": "A", "duration": -1, "dependsOn": []}]})


def test_non_numeric_duration():
    with pytest.raises(ValidationError, match="'duration' must be a number"):
        validate_and_parse(
            {"jobs": [{"name": "A", "duration": "fast", "dependsOn": []}]}
        )


def test_missing_dependency():
    with pytest.raises(ValidationError, match="depends on 'ghost' which does not exist"):
        validate_and_parse(
            {
                "jobs": [
                    {"name": "A", "duration": 1, "dependsOn": ["ghost"]},
                ]
            }
        )


def test_self_dependency():
    with pytest.raises(ValidationError, match="cannot depend on itself"):
        validate_and_parse(
            {"jobs": [{"name": "A", "duration": 1, "dependsOn": ["A"]}]}
        )


def test_unsafe_characters_in_name():
    with pytest.raises(ValidationError, match="unsafe characters"):
        validate_and_parse(
            {"jobs": [{"name": "rm -rf /", "duration": 1, "dependsOn": []}]}
        )


def test_worker_limit_zero():
    with pytest.raises(ValidationError, match="'workerLimit' must be a positive"):
        validate_and_parse({"jobs": [{"name": "A", "duration": 1}], "workerLimit": 0})


def test_worker_limit_negative():
    with pytest.raises(ValidationError, match="'workerLimit' must be a positive"):
        validate_and_parse({"jobs": [{"name": "A", "duration": 1}], "workerLimit": -1})


def test_duplicate_depends_on():
    with pytest.raises(ValidationError, match="'dependsOn' contains duplicates"):
        validate_and_parse(
            {
                "jobs": [
                    {"name": "A", "duration": 1, "dependsOn": []},
                    {"name": "B", "duration": 1, "dependsOn": ["A", "A"]},
                ]
            }
        )


def test_dependsOn_with_empty_string_item():
    with pytest.raises(ValidationError, match="must be a non-empty string"):
        validate_and_parse(
            {
                "jobs": [
                    {"name": "A", "duration": 1, "dependsOn": []},
                    {"name": "B", "duration": 1, "dependsOn": [""]},
                ]
            }
        )