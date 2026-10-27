"""Scheduling engine: barrier stages (M3), critical path (M4), failure (M5).

This module is a thin façade over :class:`scheduler.graph.Graph`. It builds a
single :class:`Graph` from the validated jobs and delegates every analysis to
it, so the graph structure is materialised exactly once per request and all
algorithms run in O(V + E) (plus deterministic sorting overhead).
"""

from __future__ import annotations

from typing import Sequence

from .graph import Graph
from .model import CriticalPathReason, Job, JobTiming, Schedule, Stage


def build_stages(jobs: Sequence[Job], workers: int) -> tuple[list[Stage], float]:
    """Partition jobs into barrier-based stages under a worker limit.

    See :meth:`Graph.schedule_stages` for the semantics. This function exists
    for API stability; it builds the graph on demand.
    """
    return Graph(jobs).schedule_stages(workers)


def critical_path_analysis(
    jobs: Sequence[Job], order: Sequence[str]
) -> tuple[dict[str, JobTiming], float, list[str]]:
    """Compute critical-path timing over the DAG (unlimited workers).

    ``order`` must be a valid topological order of ``jobs``. Returns
    ``(job_times, critical_path_duration, critical_path)``; see
    :meth:`Graph.critical_path_analysis`.
    """
    return Graph(jobs).critical_path_analysis(order)


def propagate_failure(jobs: Sequence[Job], failed_id: str) -> list[str]:
    """Return all transitive downstream dependents of ``failed_id``.

    See :meth:`Graph.downstream`.
    """
    return Graph(jobs).downstream(failed_id)


def explain_critical_path(
    graph: Graph,
    critical_path: Sequence[str],
    job_times: dict[str, JobTiming],
) -> list[CriticalPathReason]:
    """Produce a short human-readable explanation for each critical-path job.

    For every job on the representative critical path, explain why it is on the
    path: it has no prerequisites (path start), it is the chosen longest
    predecessor of the following job (its finish time feeds forward), or it is
    the final job that determines the overall critical-path duration.

    ``job_times`` supplies the already-computed earliest start/finish so the
    reported numbers match the critical-path analysis exactly.
    """
    durations = graph.durations
    path = list(critical_path)
    reasons: list[CriticalPathReason] = []

    for i, jid in enumerate(path):
        timing = job_times[jid]
        start = timing.earliest_start
        finish = timing.earliest_finish

        if len(path) == 1:
            reason = (
                f"only job on the critical path; its finish time ({finish:g}) "
                "is the overall critical-path duration"
            )
        elif i == 0:
            nxt = path[1]
            reason = (
                f"start of the critical path (no prerequisites); its finish "
                f"time ({finish:g}) feeds the next job {nxt!r}"
            )
        elif i == len(path) - 1:
            reason = (
                "last job on the critical path; its finish time "
                f"({finish:g}) is the overall critical-path duration"
            )
        else:
            nxt = path[i + 1]
            reason = (
                f"longest prerequisite of {nxt!r}; its finish time ({finish:g}) "
                "determines when the next job can start"
            )

        reasons.append(
            CriticalPathReason(
                job_id=jid,
                duration=durations[jid],
                earliest_start=start,
                earliest_finish=finish,
                reason=reason,
            )
        )

    return reasons


def build_schedule(
    jobs: Sequence[Job],
    workers: int,
    graph: Graph | None = None,
) -> Schedule:
    """Assemble the full analysis for a validated job list.

    Builds one :class:`Graph` (or reuses the supplied ``graph``) and runs every
    analysis against it, so the adjacency is constructed exactly once per
    request.
    """
    if graph is None:
        graph = Graph(jobs)
    order = graph.topological_order()
    stages, total_time = graph.schedule_stages(workers)
    job_times, cp_duration, cp_path = graph.critical_path_analysis(order)
    cp_reasons = explain_critical_path(graph, cp_path, job_times)
    return Schedule(
        topo_order=order,
        stages=stages,
        total_time=total_time,
        critical_path=cp_path,
        critical_path_duration=cp_duration,
        job_times=job_times,
        critical_path_reasons=cp_reasons,
    )
