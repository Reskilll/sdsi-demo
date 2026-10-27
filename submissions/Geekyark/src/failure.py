"""Failure simulation (M5).

Given a failed job id, computes the blast radius — every job that
cannot execute because it depends (directly or transitively) on the
failed job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set

from .graph import DAG


@dataclass
class FailureResult:
    """Result of simulating a single job failure."""

    failed_job: str
    # Jobs that are skipped because they depend on the failed job
    # (transitively), plus the failed job itself.
    skipped_jobs: List[str] = field(default_factory=list)
    # Jobs that can still run successfully.
    surviving_jobs: List[str] = field(default_factory=list)


def simulate_failure(dag: DAG, failed_job_id: str) -> FailureResult:
    """Simulate a single job failure and report the blast radius.

    Args:
        dag:          The validated DAG.
        failed_job_id: The job that failed and cannot complete.

    Returns:
        FailureResult listing all skipped and surviving jobs.

    Raises:
        ValueError if *failed_job_id* does not exist in the DAG.
    """
    if failed_job_id not in dag.jobs:
        raise ValueError(
            f"Cannot simulate failure: job '{failed_job_id}' does not exist in the DAG."
        )

    # All jobs downstream of the failure are skipped (transitive closure).
    downstream = dag.downstream_of(failed_job_id)
    skipped = {failed_job_id} | downstream

    # Sort for deterministic output.
    skipped_list = sorted(skipped)
    surviving_list = sorted(set(dag.jobs.keys()) - skipped)

    return FailureResult(
        failed_job=failed_job_id,
        skipped_jobs=skipped_list,
        surviving_jobs=surviving_list,
    )


def simulate_failures(dag: DAG, failed_job_ids: List[str]) -> dict[str, FailureResult]:
    """Simulate multiple failures.

    Each failure is independent — this is *not* cumulative.
    Call simulate_failure() for the union if you want combined impact.
    """
    results = {}
    for jid in failed_job_ids:
        results[jid] = simulate_failure(dag, jid)
    return results