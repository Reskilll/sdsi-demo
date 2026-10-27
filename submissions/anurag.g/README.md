# PS5 Job Scheduler with Dependency Resolution (DAG)

A mini build/ETL orchestrator — pure Python, standard library only.

## Quick start

```bash
# Install test dependency (optional, only for running tests)
pip install -r requirements.txt

# Run the sample
python -m scheduler schedule examples/sample.json --workers 3

# Run tests
python -m pytest tests/ -q
```

## Input schema

```json
{
  "jobs": [
    { "id": "A", "duration": 3, "dependsOn": [] },
    { "id": "B", "duration": 2, "dependsOn": ["A"] },
    { "id": "C", "duration": 4, "dependsOn": ["A"] },
    { "id": "D", "duration": 1, "dependsOn": ["B", "C"] }
  ]
}
```

- `id`: non-empty string, must be unique.
- `duration`: positive number (int or float).
- `dependsOn`: optional; may be omitted, a single string, or a list of strings.

## CLI

```
python -m scheduler <command> <input> [options]
```

### Commands

| Command      | Description                                    |
|-------------|------------------------------------------------|
| `validate`   | Validate the graph (M1) — report cycles and missing deps |
| `schedule`   | Full pipeline (M1–M4) — order, stages, critical path  |
| `fail`       | Simulate a job failure (M1 + M5)               |

### Options

| Flag            | Description                     | Default |
|-----------------|---------------------------------|---------|
| `--workers N`   | Worker limit for parallel stages | `1`     |
| `--failed ID`   | Job ID to simulate failure for  | —       |

### Examples

```bash
# Validate and detect a cycle
python -m scheduler validate examples/cycle.json

# Schedule with 2 workers
python -m scheduler schedule examples/sample.json --workers 2

# Simulate failure of job B
python -m scheduler fail examples/sample.json --failed B

# Full run with failure simulation
python -m scheduler schedule examples/sample.json --workers 3 --failed B
```

## API (programmatic)

```python
from scheduler import load_graph, run

# Load from file, string, or dict
graph = load_graph("examples/sample.json")

# Run full pipeline
report = run(graph, workers=2, fail="B")

# Access results
print(report.pretty())                  # human-readable
print(report.topo_order)                # ["A", "B", "C", "D"]
print(report.critical.critical_path)    # ["A", "C", "D"]
print(report.critical.min_completion_time)  # 8.0
print(report.failure.skipped_jobs)     # ["D"]
print(report.to_dict())                 # JSON-serializable dict
```

## Milestones

### M1 — Graph Validation
- Detects cycles using iterative 3-color DFS with full path reconstruction.
- Reports all missing dependencies (non-existent ids referenced in `dependsOn`).
- Aggregates errors — doesn't fail on the first issue.

### M2 — Topological Sort
- Kahn's algorithm with a min-heap for deterministic, lexicographic output.
- O(V + E) time complexity.

### M3 — Parallel Stages
- Computes each job's *level* = longest-path distance from sources.
- Jobs at the same level are independent.
- Within each level, jobs are batched into waves of at most N workers.
- Worker limit N must be ≥ 1; default is 1 (sequential).

### M4 — Critical Path
- Longest-path DP over the topological order.
- `earliest_finish[j] = duration[j] + max(earliest_finish[p] for p in deps[j])`.
- Reconstructs one critical path via back-pointers.
- Minimum total completion time = max earliest finish (unlimited-worker bound).

### M5 — Failure Simulation
- BFS from the failed job through outgoing (dependents) edges.
- Returns the failed job, all skipped downstream jobs, and unaffected jobs.
- Distinguishes between *skipped* (transitively downstream of failure) and *unaffected* (upstream/independent).

## Design decisions

- **No recursive DFS**: all graph traversals use explicit stacks/queues to avoid `RecursionError` on large graphs.
- **Standard library only**: `pytest` is the sole optional dev dependency.
- **Deterministic output**: topological sort uses a min-heap so results are stable and reproducible.
- **Validation-first**: the orchestrator runs M1 before M2–M5 and aborts early on invalid graphs.
- **Report object**: all results wrapped in a `Report` dataclass with both `pretty()` (human) and `to_dict()` (machine) output.

## Edge cases handled

- Empty graph (0 jobs)
- Single job with no dependencies
- Duplicate job ids (error)
- Zero/negative/non-numeric duration (error)
- `dependsOn` as string, list, or omitted
- Self-cycle (A depends on A)
- Multi-node cycles
- Missing dependencies + cycles together
- Worker limit N = 0 or negative (error)
- Unknown job id for failure simulation (error)
- Disconnected components
- Fan-in / fan-out topologies
- Large graphs (tested on 1000-job chains)

## Architecture

```
scheduler/
  models.py          # Job, JobGraph dataclasses + load_graph()
  validation.py      # M1: cycle detection + missing deps
  topo.py            # M2: Kahn's topological sort
  stages.py          # M3: parallel stages + worker batching
  critical_path.py   # M4: critical path + min completion time
  failure.py         # M5: failure simulation
  scheduler.py       # Orchestrator: run() + Report
  __main__.py        # CLI entrypoint
```

Each milestone module is self-contained and can be used independently from the orchestrator.

## Testing

```bash
python -m pytest tests/ -v
```

~70 tests covering: each milestone individually, edge cases, integration (full pipeline), CLI, models/parsing, and a 1000-job chain performance test.

## License

MIT