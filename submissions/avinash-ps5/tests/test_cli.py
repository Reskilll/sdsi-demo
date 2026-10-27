"""End-to-end tests exercising the CLI entry point against sample files."""

from pathlib import Path

import pytest

from dag_scheduler.main import main
from dag_scheduler.validator import ValidationError

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_cli_etl_pipeline(capsys):
    report = main([str(SAMPLES / "etl_pipeline.json")])
    assert report["job_count"] == 6
    assert report["cycle"]["has_cycle"] is False
    assert report["critical_path"]["total_time"] == 13.0
    assert report["schedule"]["makespan"] == 13.0


def test_cli_ci_cd_with_failure(capsys):
    report = main(
        [
            str(SAMPLES / "ci_cd_pipeline.json"),
            "--workers",
            "3",
            "--fail",
            "integration_test",
        ]
    )
    failure = report["failure_simulation"]
    assert failure["failed_job"] == "integration_test"
    assert "e2e_test" in failure["directly_skipped"]
    assert set(failure["all_skipped"]) >= {"e2e_test", "deploy_staging", "smoke_test", "deploy_prod"}


def test_cli_cycle_is_reported_not_crashed(capsys):
    report = main([str(SAMPLES / "cycle_simple.json")])
    assert report["cycle"]["has_cycle"] is True
    assert len(report["cycle"]["cycle_path"]) >= 3


def test_cli_missing_dep_errors(capsys):
    with pytest.raises(ValidationError, match="does not exist"):
        main([str(SAMPLES / "missing_dep.json")])


def test_cli_unknown_fail_job_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main([str(SAMPLES / "etl_pipeline.json"), "--fail", "no_such_job"])


def test_cli_invalid_workers_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main([str(SAMPLES / "etl_pipeline.json"), "--workers", "0"])


def test_cli_output_file(tmp_path):
    out = tmp_path / "report.json"
    report = main([str(SAMPLES / "single_job.json"), "--output", str(out)])
    assert out.exists()
    import json

    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["job_count"] == 1
    assert report["critical_path"]["path"] == ["only_job"]