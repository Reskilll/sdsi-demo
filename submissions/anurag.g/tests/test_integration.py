"""Integration tests: end-to-end run() pipeline."""

import pytest
from scheduler.scheduler import run


def test_full_run_sample():
    data = {"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]}
    report = run(data, workers=2)
    assert report.validation.is_valid
    assert len(report.topo_order) == 4
    assert report.topo_order[0] == "A"
    assert report.topo_order[-1] == "D"
    assert report.critical is not None
    assert report.critical.critical_path == ["A", "C", "D"]
    assert report.critical.min_completion_time == 8.0
    assert report.failure is None


def test_full_run_with_failure():
    data = {"jobs": [
        {"id": "A", "duration": 3},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 4, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
    ]}
    report = run(data, workers=1, fail="B")
    assert report.validation.is_valid
    assert report.failure is not None
    assert report.failure.failed_job == "B"
    assert set(report.failure.skipped_jobs) == {"D"}


def test_invalid_graph_aborts_early():
    data = {"jobs": [
        {"id": "A", "duration": 1, "dependsOn": ["B"]},
        {"id": "B", "duration": 1, "dependsOn": ["A"]},
    ]}
    report = run(data)
    assert not report.validation.is_valid
    assert report.topo_order == []  # not populated
    assert report.critical is None


def test_run_with_bad_workers():
    data = {"jobs": [{"id": "A", "duration": 1}]}
    report = run(data, workers=0)
    assert not report.validation.is_valid


def test_large_graph_performance():
    """Synthetic chain of 1000 jobs — should complete in well under 1 second."""
    jobs = []
    for i in range(1000):
        deps = [f"job_{i-1}"] if i > 0 else []
        jobs.append({"id": f"job_{i}", "duration": 1, "dependsOn": deps})
    report = run({"jobs": jobs}, workers=5)
    assert report.validation.is_valid
    assert len(report.topo_order) == 1000
    assert report.critical is not None
    assert report.critical.min_completion_time == 1000.0


def test_fan_in_fan_out():
    data = {"jobs": [
        {"id": "A", "duration": 1},
        {"id": "B", "duration": 2, "dependsOn": ["A"]},
        {"id": "C", "duration": 3, "dependsOn": ["A"]},
        {"id": "D", "duration": 1, "dependsOn": ["B", "C"]},
        {"id": "E", "duration": 4, "dependsOn": ["B", "C"]},
    ]}
    report = run(data, workers=10)
    assert report.validation.is_valid
    # A → B(2), C(3) → D(1), E(4)
    # Critical: A→C(3)→E(4) = 8
    assert report.critical.critical_path == ["A", "C", "E"]
    assert report.critical.min_completion_time == 8.0


def test_report_pretty():
    data = {"jobs": [{"id": "A", "duration": 1}]}
    report = run(data)
    text = report.pretty()
    assert "JOB SCHEDULER REPORT" in text
    assert "A" in text


def test_report_to_dict():
    data = {"jobs": [{"id": "A", "duration": 1}]}
    report = run(data, fail="A")
    d = report.to_dict()
    assert d["num_jobs"] == 1
    assert d["valid"] is True
    assert "failure" in d
    assert d["failure"]["failed_job"] == "A"