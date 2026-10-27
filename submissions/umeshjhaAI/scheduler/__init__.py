"""Mini job scheduler / ETL orchestrator.

Public API surface. The scheduler validates a JSON job description, computes a
deterministic topological order, a worker-limited barrier-based stage schedule,
critical-path analysis, and downstream failure propagation.
"""

from .engine import build_schedule, propagate_failure
from .errors import SchedulerError, ValidationError
from .model import CriticalPathReason, Job, Stage, Schedule, JobTiming
from .validation import parse_jobs

__all__ = [
    "Job",
    "Stage",
    "Schedule",
    "JobTiming",
    "CriticalPathReason",
    "SchedulerError",
    "ValidationError",
    "parse_jobs",
    "build_schedule",
    "propagate_failure",
]
