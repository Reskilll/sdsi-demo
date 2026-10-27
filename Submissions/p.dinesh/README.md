# Job Scheduler with Dependency Resolution (DAG)

A mini build / ETL orchestrator — given a JSON job list, it validates,
schedules, and analyses the DAG for parallel execution.

---

## Quick start

```bash
# Install (editable)
pip install -e ".[dev]"

# Run the report
dag-scheduler samples/basic.json

# With a worker limit
dag-scheduler samples/complex.json --workers 3

# Simulate a failure
dag-scheduler samples/complex.json --fail train_a

# JSON output
dag-scheduler samples/basic.json --json

# Extract a single mode
dag-scheduler samples/basic.json --only stages

# Graphviz DOT output (pipe into `dot -Tpng` to render)
dag-scheduler samples/complex.json --dot
```

No install?  Run directly:
```bash
python -m src.cli samples/basic.json
```

---

## Input format (JSON)

```json
[
  { "id": "A", "duration": 3, "dependsOn": [] },
  { "id": "B", "duration": 2, "dependsOn": ["A"] },
  { "id": "C", "duration": 1, "dependsOn": ["A"] },
  { "id": "D", "duration": 4, "dependsOn": ["B", "C"] }
]
```

- **`id`** *(required, non-empty string)* — unique job identifier.
- **`duration`** *(required, non-negative integer)* — time the job takes.
- **`dependsOn`** *(optional, array of strings)* — jobs that must finish first.

---

## Capabilities (M1–M5)

| # | Feature                | Description                                                                 |
|---|------------------------|-----------------------------------------------------------------------------|
| M1| **Validate**           | Detects cycles (reports the full cycle path), missing dependencies, and duplicate IDs. |
| M2| **Topological sort**   | Produces a valid linear execution order (Kahn's algorithm).                  |
| M3| **Parallel stages**    | Groups jobs into stages with configurable worker limit `N`.                  |
| M4| **Critical path**      | Computes the longest dependency chain and minimum total completion time.     |
| M5| **Failure simulation** | Given a failed job, lists every transitively downstream job that is skipped. |

---

## Sample output

```
============================================================
  JOB SCHEDULER — Dependency-Aware DAG Execution Plan
============================================================
  Jobs:           4
  Worker limit:   4

  ✅ Graph is a valid DAG — no cycles, all dependencies satisfied.

────────────────────────────────────────────────────────────
  TOPOLOGICAL ORDER
  A → B → C → D

────────────────────────────────────────────────────────────
  PARALLEL EXECUTION STAGES
  Stage  1  t=  0→  3  ( 3s)  A
  Stage  2  t=  3→  5  ( 2s)  B, C
  Stage  3  t=  5→  9  ( 4s)  D
             Total timeline: 9s

────────────────────────────────────────────────────────────
  CRITICAL PATH
  Path:            A → B → D
  Minimum time:    9s
```

---

## Project structure

```
p.dinesh/
  ├── src/
  │   ├── __init__.py
  │   ├── models.py      # JobSpec, ExecutionPlan, JSON loading
  │   ├── engine.py      # Core algorithms (M1–M5)
  │   └── cli.py         # Command-line interface
  ├── tests/
  │   ├── __init__.py
  │   └── test_engine.py # Full test suite (45+ tests)
  ├── samples/
  │   ├── basic.json
  │   ├── cycle.json
  │   ├── missing_dep.json
  │   └── complex.json
  ├── PROMPTS.md         # AI collaboration log
  ├── README.md          # ← this file
  └── pyproject.toml
```

---

## Running the tests

```bash
pip install -e ".[dev]"
pytest -v
```

Tests cover all M1–M5 modules plus edge cases:
zero-duration jobs, disconnected components, fan-in/fan-out,
strict chains, multiple roots/sinks, worker-limit serialisation,
duplicate/empty dependency entries, and model-validation for malformed input.

---

## Bonus features

- **Graphviz DOT export** (`--dot`) — render the DAG as a diagram with the
  critical path highlighted in red and failure-skipped nodes grayed out:
  ```bash
  dag-scheduler samples/complex.json --dot | dot -Tpng -o dag.png
  ```
- **JSON machine output** (`--json`) — full plan as structured JSON for
  piping into other tools.
- **Single-mode extraction** (`--only`) — run just one analysis (`validate`,
  `topo`, `stages`, `critical`, `fail`) for quick checks.

---

## Algorithm notes

- **Cycle detection** — 3-colour DFS (white/gray/black).  When a back-edge
  is found we walk the parent pointers to reconstruct the full cycle path.
- **Topological sort** — Kahn's algorithm (BFS with in-degree tracking).
  O(V + E).
- **Parallel staging** — Level-scheduling with a bounded worker pool.
  At each tick we dequeue up to `N` ready jobs; any excess stay in the
  ready queue for the next stage.
- **Critical path** — Longest-path-in-DAG computed in a single topological
  pass with Earliest Start Time propagation.  O(V + E).
- **Failure simulation** — Simple BFS from the failed node through the
  adjacency list to collect all transitive dependents.