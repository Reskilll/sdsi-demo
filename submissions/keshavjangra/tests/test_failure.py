"""Tests for M5 – Failure simulation."""

import pytest

from scheduler.graph import DAG
from scheduler.failure import downstream_impact, failure_report


_FIXTURE = [
    {"id": "A", "duration": 3, "dependsOn": []},
    {"id": "B", "duration": 5, "dependsOn": ["A"]},
    {"id": "C", "duration": 2, "dependsOn": ["A"]},
    {"id": "D", "duration": 4, "dependsOn": ["B", "C"]},
    {"id": "E", "duration": 1, "dependsOn": ["D"]},
]


def _dag():
    return DAG.from_dicts(_FIXTURE)


def test_failure_root_skips_all():
    dag = _dag()
    skipped = downstream_impact(dag, "A")
    assert skipped == {"A", "B", "C", "D", "E"}


def test_failure_leaf_skips_only_itself():
    dag = _dag()
    skipped = downstream_impact(dag, "E")
    assert skipped == {"E"}


def test_failure_mid_chain():
    dag = _dag()
    skipped = downstream_impact(dag, "B")
    assert skipped == {"B", "D", "E"}


def test_failure_nonexistent_job():
    dag = _dag()
    with pytest.raises(ValueError, match="not found"):
        downstream_impact(dag, "GHOST")


def test_failure_report_format():
    dag = _dag()
    report = failure_report(dag, "B")
    assert "B" in report
    assert "D" in report
    assert "E" in report
    assert "Downstream jobs skipped" in report


def test_failure_leaf_report():
    dag = _dag()
    report = failure_report(dag, "E")
    assert "No downstream jobs affected" in report


def test_failure_independent_jobs():
    """If all jobs are independent, failing one doesn't affect others."""
    dag = DAG.from_dicts([
        {"id": "X", "duration": 1, "dependsOn": []},
        {"id": "Y", "duration": 1, "dependsOn": []},
        {"id": "Z", "duration": 1, "dependsOn": []},
    ])
    skipped = downstream_impact(dag, "Y")
    assert skipped == {"Y"}


def test_failure_report_nonexistent_job():
    dag = _dag()
    with pytest.raises(ValueError, match="not found"):
        failure_report(dag, "GHOST")