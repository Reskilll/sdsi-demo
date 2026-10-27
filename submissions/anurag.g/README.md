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
python -m scheduler validate examples/cycle.json
python -m scheduler schedule examples/sample.json --workers 2
python -m scheduler fail examples/sample.json --failed B
```

## API (programmatic)

```python
from scheduler import load_graph, run

graph = load_graph("examples/sample.json")
report = run(graph, workers=2, fail="B")

print(report.pretty())
print(report.topo_order)              # ["A", "B", "C", "D"]
print(report.critical.critical_path)  # ["A", "C", "D"]
print(report.failure.skipped_jobs)    # ["D"]
print(report.to_dict())               # JSON-serializable dict
```

## Milestones

### M1 — Graph Validation
- Detects cycles using iterative 3-color DFS with full path reconstruction.
- Reports all missing dependencies.

### M2 — Topological Sort
- Kahn's algorithm with a min-heap for deterministic, lexicographic output.

### M3 — Parallel Stages
- Level-based grouping (longest-path distance from sources).
- Worker batching: within each level, jobs batched into waves of at most N.

### M4 — Critical Path
- Longest-path DP over topological order.
- Reconstructs one critical path via back-pointers.
- Minimum total completion time = max earliest finish.

### M5 — Failure Simulation
- BFS from the failed job through outgoing (dependents) edges.
- Distinguishes skipped (downstream) vs unaffected (upstream/independent).

## Design decisions

- No recursive DFS — all traversals use explicit stacks/queues.
- Standard library only at runtime; pytest is the sole dev dependency.
- Deterministic output via min-heap in Kahn's algorithm.
- Validation-first: M1 runs before M2–M5, aborts early on invalid graphs.

## Edge cases handled

Empty graph, single job, duplicate ids, self-cycles, multi-node cycles, missing deps + cycles together, dependsOn as string/list/omitted, zero/negative/non-numeric duration, N=0/negative, unknown failed job, disconnected components, fan-in/fan-out, large graphs (1000 jobs).

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

## Testing

```bash
python -m pytest tests/ -v
```

~70 tests covering each milestone, edge cases, integration, CLI, and a 1000-job performance test.