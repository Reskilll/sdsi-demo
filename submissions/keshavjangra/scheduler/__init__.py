"""Job Scheduler with Dependency Resolution (DAG).

A mini build / ETL orchestrator that:
  - Validates DAGs (cycle detection, missing dependencies)
  - Produces topological execution orders
  - Groups jobs into parallel stages with a configurable worker limit
  - Computes critical path and minimum completion time
  - Simulates failures (lists skipped downstream jobs)
"""

__version__ = "1.0.0"