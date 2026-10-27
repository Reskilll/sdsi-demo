# DAG Job Scheduler — PS5

A dependency-aware job orchestrator that validates a job graph, computes a
valid execution order, schedules work across parallel workers, finds the
critical path, and simulates failures.

## Quick start

```bash
# 1. Install (Python ≥ 3.9 — no external dependencies beyond stdlib)
cd submissions/avinash-ps5

# 2. Run a sample
python -m dag_scheduler.main samples/etl_pipeline.json

# 3. With a custom worker limit and failure simulation
python -m dag_scheduler.main samples/ci_cd_pipeline.json --workers 3 --fail integration_test

# 4. Export the full report to JSON
python -m dag_scheduler.main samples/linear_chain.json --output report.json
```

## Sample output

```
📋 Topological order: fetch_data → clean_data → validate → train_model → evaluate → deploy
🕐 Critical path: fetch_data → clean_data → train_model → evaluate → deploy (total: 13.0)

⚙️  Parallel schedule (4 workers, makespan 13.0):
   Stage 0: ['fetch_data']
   Stage 1: ['clean_data', 'validate']
   Stage 2: ['train_model']
   Stage 3: ['evaluate']
   Stage 4: ['deploy']
```

## Input format

```json
{
  "workerLimit": 4,
  "jobs": [
    {"name": "fetch_data",  "duration": 2, "dependsOn": []},
    {"name": "clean_data",  "duration": 3, "dependsOn": ["fetch_data"]},
    {"name": "validate",    "duration": 1, "dependsOn": ["fetch_data"]},
    {"name": "train_model", "duration": 5, "dependsOn": ["clean_data", "validate"]}
  ]
}
```

| Field        | Required | Notes                                    |
|-------------|----------|------------------------------------------|
| `name`      | ✅       | Alphanumeric, hyphen, underscore, dot    |
| `duration`  | ✅       | Non-negative number                      |
| `dependsOn` | ✅       | List of job names (may be empty)         |
| `workerLimit`| No      | Positive integer (default: 4)            |

## Features

| ID | Feature | Description |
|----|---------|------------|
| M1 | **Cycle detection** | DFS tri-colour; reports the exact cycle path |
| M2 | **Topological sort** | Kahn's algorithm with level grouping |
| M3 | **Parallel scheduling** | Greedy list-scheduler with configurable worker cap; outputs per-stage grouping + detailed timeline |
| M4 | **Critical path** | Dynamic-programming longest-path; gives the minimum total completion time |
| M5 | **Failure simulation** | Given a failed job, computes the transitive closure of all downstream skipped jobs |

### Bonus capabilities

- **Input validation**: Sanitises job names against injection; catches duplicates, missing deps, negative durations, empty lists, and self-loops before any scheduling logic runs.
- **Level-order grouping**: BFS-style level assignment for visualizing independent jobs.
- **Worker timeline**: The `--output report.json` exports each job's `(start, end, worker_id)`.
- **CLI ergonomics**: Verbose mode (`--verbose`), output file (`--output`), safe exit codes.

## Run tests

```bash
cd submissions/avinash-ps5
python -m pytest tests/ -v
```

## Directory layout

```
submissions/avinash-ps5/
├── dag_scheduler/
│   ├── __init__.py      # Package init
│   ├── graph.py         # DAG model, cycle detection, topo-sort, critical path, failure
│   ├── scheduler.py     # Parallel scheduling (group_stages + list-scheduler)
│   ├── validator.py     # JSON loading, input validation, sanitisation
│   └── main.py          # CLI entry point
├── tests/
│   ├── conftest.py
│   ├── test_graph.py
│   ├── test_scheduler.py
│   └── test_validator.py
├── samples/
│   ├── etl_pipeline.json
│   ├── ci_cd_pipeline.json
│   ├── linear_chain.json
│   ├── fully_parallel.json
│   ├── deep_chain.json
│   ├── single_job.json
│   ├── cycle_simple.json
│   └── missing_dep.json
├── README.md
└── PROMPTS.md
```

## Edge case handling

- **Empty graphs**: Rejected at validation.
- **Self-dependencies**: Caught during validation.
- **Duplicate job names**: Caught during validation.
- **Missing dependencies**: Cross-referenced after parsing.
- **Zero-duration jobs**: Allowed (instant). Scheduler handles them correctly.
- **Single job**: Works — both critical path and scheduler handle the trivial case.
- **Fully disconnected graph**: All jobs run in parallel, limited only by workers.
- **Deep linear chain**: Scheduler correctly produces a sequential schedule regardless of worker count.
- **Large worker limit**: Capped by number of ready jobs at any time.
- **Injection resistance**: Job names are validated against a safe-identifier regex; JSON is loaded with `json.loads` (no arbitrary code execution).