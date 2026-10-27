"""PS5 Job Scheduler with Dependency Resolution (DAG).

A mini build/ETL orchestrator that reads a JSON job graph, validates it,
topologically sorts it, groups jobs into parallel stages under a worker limit,
computes the critical path, and simulates failures.
"""

from scheduler.scheduler import run
from scheduler.models import JobGraph, load_graph

__all__ = ["JobGraph", "load_graph", "run"]