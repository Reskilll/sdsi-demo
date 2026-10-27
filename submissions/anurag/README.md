# Job Scheduler with Dependency Resolution (DAG)

A mini build/ETL orchestrator. Given a JSON job graph with durations and
dependencies, it validates the graph, produces an execution plan, and simulates
failures.

## Quick start

```bash
# Validate & schedule
python scheduler.py sample.json

# With a worker limit of 2
python scheduler.py sample.json --worker-limit 2

# Simulate a failure
python scheduler.py sample.json --fail parse_a

# Run all tests
python -m unittest test_scheduler -v
```

## Input format

A JSON object mapping job names to `{duration, dependsOn}`:

```json
{
  "fetch":   { "duration": 2, "dependsOn": [] },
  "parse_a": { "duration": 1, "dependsOn": ["fetch"] },
  "parse_b": { "duration": 1, "dependsOn": ["fetch"] },
  "join":    { "duration": 2, "dependsOn": ["parse_a", "parse_b"] },
  "export":  { "duration": 1, "dependsOn": ["join"] }
}
```

- `duration` — non-negative number (seconds, or any unit).
- `dependsOn` — array of job names that must finish first. Defaults to `[]`.

## What it computes

| Milestone | Description |
|-----------|-------------|
| **M1 — Validation** | Detects cycles (reports the full path) and missing dependencies. All errors are reported in one pass. |
| **M2 — Topological order** | A valid linear execution order via Kahn's algorithm. |
| **M3 — Parallel stages** | Groups jobs into stages where all jobs in a stage are ready and can run concurrently. A `worker_limit` caps how many run at once by splitting stages. |
| **M4 — Critical path** | The longest path through the DAG — determines the minimum total completion time. |
| **M5 — Failure simulation** | Given a failed job, returns every transitively dependent downstream job (the ones that must be skipped). |

## API (Python)

```python
from scheduler import JobGraph

graph = JobGraph.from_dict({...})
# or
graph = JobGraph.from_file("graph.json")

# Validate
report = graph.validate()
print(report.is_valid, report.errors)

# Schedule
result = graph.schedule(worker_limit=4)
# {
#   "valid": True,
#   "topological_order": [...],
#   "parallel_stages": [[...], [...]],
#   "critical_path": [...],
#   "min_completion_time_seconds": 6.0,
# }

# Individual methods
order = graph.topological_order()
stages = graph.parallel_stages(worker_limit=4)
path, min_time = graph.critical_path()
skipped = graph.downstream_jobs("failed_job")
```

## Sample files

| File | Purpose |
|------|---------|
| `sample.json` | Simple 5-job ETL pipeline |
| `sample_cycle.json` | Two-node mutual dependency (cycle) |
| `sample_missing.json` | Reference to undefined `ghost` job |
| `sample_complex.json` | 8-job pipeline with fan-out/fan-in |

## Design decisions

- **Iterative DFS** for cycle detection — handles graphs of any depth without
  hitting Python's recursion limit.
- **Kahn's algorithm** for topological sort — stable, linear-time, no recursion.
- **All errors at once** — validation reports missing deps *and* cycles in a
  single pass so the caller can fix everything before re-running.
- **Conservative parallelism** — `parallel_stages()` only runs jobs whose *all*
  dependencies have completed. The worker cap further splits ready work.

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)