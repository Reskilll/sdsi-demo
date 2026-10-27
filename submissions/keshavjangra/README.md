# Job Scheduler with Dependency Resolution (DAG)

A mini build / ETL orchestrator that reads a JSON job graph, validates it,
and provides execution analysis.

## What it does

| Milestone | Feature                                                |
|-----------|--------------------------------------------------------|
| **M1**    | Validate the graph: cycle detection (with path) and missing dependency checks |
| **M2**    | Produce a valid execution order via topological sort   |
| **M3**    | Group jobs into parallel stages; configurable worker limit |
| **M4**    | Compute the critical path and minimum total completion time |
| **M5**    | Simulate failures: given a failed job, list every downstream job that is skipped |

## Quick start

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run the CLI on a sample
python -m scheduler.cli tests/fixtures/sample1.json

# With a worker limit
python -m scheduler.cli --workers 3 tests/fixtures/sample2.json

# Simulate a failure
python -m scheduler.cli --fail B tests/fixtures/sample1.json

# JSON output (machine-readable)
python -m scheduler.cli --json-out tests/fixtures/sample1.json

# Pipe JSON from stdin
echo '[{"id":"A","duration":5,"dependsOn":[]}]' | python -m scheduler.cli --stdin
```

## Input format

A JSON array of job objects. Each job has:
- `id` (string, required) — unique identifier
- `duration` (number ≥ 0, required) — how long the job takes
- `dependsOn` (array of strings, optional) — job ids that must finish first

```json
[
  { "id": "A", "duration": 3, "dependsOn": [] },
  { "id": "B", "duration": 5, "dependsOn": ["A"] },
  { "id": "C", "duration": 2, "dependsOn": ["A"] },
  { "id": "D", "duration": 4, "dependsOn": ["B", "C"] },
  { "id": "E", "duration": 1, "dependsOn": ["D"] }
]
```

## Running tests

```bash
pytest                    # run all tests
pytest -v                 # verbose
pytest --cov=scheduler    # with coverage
```

## Project structure

```
keshavjangra/
├── scheduler/
│   ├── __init__.py       # Package version
│   ├── graph.py          # DAG model, parsing, M1 validation
│   ├── topo.py           # M2 topological sort (Kahn + DFS)
│   ├── parallel.py       # M3 parallel stages & worker-limited scheduling
│   ├── critical.py       # M4 critical path & min completion time
│   ├── failure.py        # M5 failure simulation
│   └── cli.py            # Command-line interface
├── tests/
│   ├── fixtures/         # JSON test graphs (valid + invalid)
│   ├── test_graph.py     # M1 tests
│   ├── test_topo.py      # M2 tests
│   ├── test_parallel.py  # M3 tests
│   ├── test_critical.py  # M4 tests
│   ├── test_failure.py   # M5 tests
│   └── test_integration.py  # End-to-end with fixture files
├── pyproject.toml
├── README.md             # This file
└── PROMPTS.md            # AI collaboration log
```

## Edge cases handled

- **Cycles**: Detected with the exact cycle path reported (three-color DFS)
- **Self-loops**: Handled as a cycle of length 1
- **Missing dependencies**: All checked in one pass with detailed error messages
- **Empty DAG**: Works gracefully (empty lists, zero makespan)
- **Zero-duration jobs**: All algorithms handle them correctly
- **Duplicate job ids**: Caught at parse time
- **Invalid types**: `dependsOn` must be a list of strings; `duration` must be non-negative
- **Negative durations**: Rejected
- **Worker limit = 0 or negative**: Rejected
- **Worker limit > ready jobs**: Sub-slices respect the limit
- **Deep graphs**: Iterative DFS avoids Python recursion limits
- **Wide graphs**: Kahn's algorithm scales linearly with node + edge count
- **Deterministic output**: All algorithms sort before iterating for reproducible results
- **Stdin input**: Supports piping JSON for composability
- **JSON output mode**: Machine-readable output for use in pipelines