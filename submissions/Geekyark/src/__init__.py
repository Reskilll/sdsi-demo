"""DAG Job Scheduler — PS5 submission by Geekyark.

Core pipeline:
  M1  validate (cycles, missing deps)
  M2  topological sort
  M3  parallel-stage schedule with worker limit N
  M4  critical path analysis
  M5  failure simulation (blast radius)
"""

from .graph import DAG, Job
from .validator import ValidationIssue, validate
from .toposort import topological_sort
from .scheduler import ScheduleResult, Stage, schedule
from .critical_path import CriticalPathResult, compute_critical_path
from .failure import FailureResult, simulate_failure
from .orchestrator import PipelineResult, format_pipeline_result, run

__all__ = [
    "DAG",
    "Job",
    "ValidationIssue",
    "validate",
    "topological_sort",
    "ScheduleResult",
    "Stage",
    "schedule",
    "CriticalPathResult",
    "compute_critical_path",
    "FailureResult",
    "simulate_failure",
    "PipelineResult",
    "format_pipeline_result",
    "run",
]