# PS5 — DAG Job Scheduler with Dependency Resolution

**Developer:** Geekyark  
**Track:** Productivity  
**Use-case ID:** PS5

A mini build/ETL orchestrator that schedules jobs with dependency resolution.
Given a JSON payload of jobs (each with a `duration` and `dependsOn` list),
the pipeline validates the graph, produces valid execution orders, groups jobs
into parallel stages subject to a worker cap, identifies critical paths, and
simulates failure blast radius.

---

## Quick start

```bash
# 1. Install (only pytest for tests — zero runtime dependencies)
cd submissions/Geekyark
pip install -r requirements.txt

# 2. Run the example
python main.py samples/example.json

# 3. With a worker cap
python main.py samples/example.json --workers 4

# 4. Simulate a failure
python main.py samples/example.json --fail load_orders

# 5. JSON output (for piping / CI)
python main.py samples/example.json --json

# 6. Run the test suite (84+ tests)
pytest tests/ -v
```

### Python version

Requires **Python 3.10+** (uses `X | Y` union syntax).

---

## Input format

A JSON array of job objects:

```json
[
  { "id": "init_db",    "duration": 2,   "dependsOn": [] },
  { "id": "load_users", "duration": 4,   "dependsOn": ["init_db"] },
  { "id": "build_index","duration": 3,   "dependsOn": ["load_users"] }
]
```

| Field        | Type        | Required | Notes                              |
|-------------|-------------|----------|------------------------------------|
| `id`        | `string`    | Yes      | Must be unique.                    |
| `duration`  | `number`    | Yes      | Must be >= 0.                      |
| `dependsOn` | `[string]`  | No       | Defaults to `[]` if omitted.       |

---

## Architecture

```
submissions/Geekyark/
  main.py                  CLI entry point
  src/
    __init__.py             Public API surface
    graph.py                DAG & Job data structures
    validator.py            M1 — cycle detection + missing deps
    toposort.py             M2 — topological sort (Kahn's algorithm)
    scheduler.py            M3 — parallel-stage scheduling (list scheduling)
    critical_path.py         M4 — critical path (forward/backward pass)
    failure.py              M5 — failure simulation (blast radius)
    orchestrator.py         Pipeline runner + human-readable formatter
  tests/
    test_all.py             84+ test cases covering all modules + edge cases
  samples/
    example.json            Basic 5-job DAG
    complex_dag.json        10-job DAG with diamond patterns
    chain.json              Linear chain of 5 jobs
    disconnected.json       3 independent jobs
    single_job.json         Single-node DAG
    with_cycle.json         Intentional cycle (A→B→C→A)
    missing_dep.json        Job depends on undefined job
    duplicate_id.json       Duplicate 'id' values
  PROMPTS.md                AI collaboration log
  requirements.txt          pytest (dev only)
```

### Module dependency graph

```
graph.py  ←──  no internal deps (data layer)
  ├── validator.py       (M1)
  ├── toposort.py        (M2)
  ├── scheduler.py       (M3)
  ├── critical_path.py   (M4, depends on toposort)
  ├── failure.py         (M5)
  └── orchestrator.py   (aggregates all; called by main.py)
```

---

## What the code is judged on

### M1 — Validate the graph
- Cycle detection via iterative DFS with a WHITE/GREY/BLACK colour map.
- Detects **all** cycles (not just the first one) and reports the cycle path.
- Flags every missing dependency with the source job and the undefined target.

### M2 — Topological sort
- Kahn's algorithm (BFS-based, queue of zero-in-degree nodes).
- Deterministic output for the same input.
- Refuses to sort cyclic graphs (validates first).

### M3 — Parallel stages with worker limit N
- Greedy list-scheduling heuristic.
- At each time step, picks up to N ready jobs (all deps satisfied).
- Advances time by the shortest-running job in the current batch.
- Reports per-job start/finish times, stage composition, and total makespan.

### M4 — Critical path
- Forward pass for earliest start/finish times.
- Backward pass for latest start/finish times.
- Slack = LST − EST; zero-slack jobs are on the critical path.
- Reconstructs **all** critical paths (handles ties).

### M5 — Failure simulation
- Computes the transitive closure of successors for the failed job.
- Reports: skipped jobs (failed + downstream), surviving jobs.

### Beyond the rubric
- **Input validation:** Rejects malformed JSON, missing fields, wrong types,
  negative durations, duplicate ids, non-list `dependsOn`.
- **Performance awareness:** All algorithms are O(V + E); tested on 300-node DAGs.
- **Error handling:** Every edge case the evaluator throws gets a clear error
  message — nothing passes silently.
- **Extensible design:** Each module is independent; the `orchestrator.py` is
  just a thin coordinator. Add new analysis modules without touching existing code.

---

## Sample output

```
============================================================
  JOB SCHEDULER — PIPELINE RESULT
============================================================
  Jobs: 5  |  Edges: 4  |  Worker limit: 1
------------------------------------------------------------
  M1 — GRAPH VALIDATION
------------------------------------------------------------
  ✓ No issues found.

------------------------------------------------------------
  M2 — TOPOLOGICAL ORDER
------------------------------------------------------------
  init_db → load_users → load_orders → build_index → send_report

------------------------------------------------------------
  M3 — PARALLEL EXECUTION STAGES
------------------------------------------------------------
  Stage   1  @ t=   0.0  dur=   2.0  jobs: init_db
  Stage   2  @ t=   2.0  dur=   4.0  jobs: load_users
  Stage   3  @ t=   6.0  dur=   1.0  jobs: load_orders
  Stage   4  @ t=   7.0  dur=   3.0  jobs: build_index
  Stage   5  @ t=  10.0  dur=   1.0  jobs: send_report
  Total completion time: 11.0

------------------------------------------------------------
  M4 — CRITICAL PATH
------------------------------------------------------------
  Critical path 1: init_db → load_users → build_index → send_report
  Minimum completion time: 10.0

  Per-job slack (zero = on critical path):
    init_db               slack=   0.0 ★
    load_users            slack=   0.0 ★
    load_orders           slack=   1.0
    build_index           slack=   0.0 ★
    send_report           slack=   0.0 ★
```