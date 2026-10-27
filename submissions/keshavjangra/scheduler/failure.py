"""M5 – Failure simulation.

Given a failed job, computes the transitive closure of downstream jobs
that become unreachable, i.e. every job that depends (directly or
indirectly) on the failed job.
"""

from __future__ import annotations

from collections import deque
from typing import List, Set

from .graph import DAG


def downstream_impact(dag: DAG, failed_job_id: str) -> Set[str]:
    """Return the set of all job ids that must be skipped because
    *failed_job_id* cannot run.

    Includes the failed job itself.

    Raises ``ValueError`` if *failed_job_id* is not in the DAG.
    """
    if failed_job_id not in dag.jobs:
        raise ValueError(f"Job '{failed_job_id}' not found in the DAG")

    skipped: Set[str] = {failed_job_id}
    queue: deque[str] = deque([failed_job_id])

    while queue:
        node = queue.popleft()
        for child in dag.downstream_of(node):
            if child not in skipped:
                skipped.add(child)
                queue.append(child)

    return skipped


def failure_report(dag: DAG, failed_job_id: str) -> str:
    """Produce a human-readable report of the failure impact.

    Returns a formatted string listing:
      - The failed job
      - Every downstream job that is skipped, grouped by distance
    """
    if failed_job_id not in dag.jobs:
        raise ValueError(f"Job '{failed_job_id}' not found in the DAG")

    skipped = downstream_impact(dag, failed_job_id)
    skipped_except_failed = sorted(skipped - {failed_job_id})

    lines = [
        f"Failure report for job: {failed_job_id}",
        f"  Duration of failed job: {dag.jobs[failed_job_id].duration}",
        f"  Total jobs skipped (including failed): {len(skipped)}",
    ]
    if skipped_except_failed:
        lines.append("  Downstream jobs skipped:")
        for jid in skipped_except_failed:
            lines.append(f"    - {jid} (duration: {dag.jobs[jid].duration})")
    else:
        lines.append("  No downstream jobs affected.")
    return "\n".join(lines)