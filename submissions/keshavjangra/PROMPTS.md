# PROMPTS.md — AI Collaboration Effectiveness

## Prompt history

### 1. Initial project scaffolding

> "Build a Job Scheduler with Dependency Resolution (DAG). M1 validate the
> graph (cycles & missing deps). M2 topological sort. M3 parallel stages with
> worker limit. M4 critical path. M5 failure simulation. Full tests and docs."

**Model actions**: Planned module decomposition, created `scheduler/` package
with single-responsibility modules (`graph.py`, `topo.py`, `parallel.py`,
`critical.py`, `failure.py`, `cli.py`).  Created 10 test fixture JSON files
covering every edge case (cycles, missing deps, linear chains, independent
sets, zero-duration jobs, diamonds, fans).  Built 70+ test cases across 7 test
files.

### 2. Design decisions made

| Decision | Rationale |
|----------|-----------|
| Three-color iterative DFS for cycle detection | Handles deep graphs without recursion limits; reports exact cycle path |
| Kahn's algorithm for topological sort | Stable, deterministic (sorted iteration), BFS-based |
| DP-based critical path | O(V+E) — longest-path on a DAG via topological order |
| `parallel_schedule` splits stages into worker-limited slices | Preserves stage ordering; each slice ≤ N workers |
| Separate modules per concern | Graph model is imported by topo, parallel, critical, failure — zero duplication |
| `failure_report()` returns a formatted string | Human-readable output directly usable from CLI |
| JSON output mode (`--json-out`) | Machine-readable for pipeline integration |
| `--stdin` flag | Composable with shell pipes, accepts JSON from stdin |

### 3. Iteration notes

- **Cycle path reporting**: First implementation only said "cycle detected."
  Refined to walk parent pointers and report the full `A → B → C → A` path.
- **Worker limit**: Originally returned unlimited stages only. Added
  `parallel_schedule()` to slice stages into worker-bounded groups.
- **Edge cases**: Added tests for empty DAG, zero-duration jobs, self-loops,
  duplicate IDs, negative durations, invalid types in `dependsOn`.
- **Determinism**: Every algorithm that iterates over sets now calls
  `sorted()` so output is reproducible across runs.
- **Critical path ties**: When multiple paths have the same length the
  algorithm returns the first found deterministically.

### 4. Quality checks

- All 70+ tests pass
- No `print()` outside `cli.py`
- All public functions have docstrings
- `ValueError` raised for all input validation failures (never `assert`)
- CLI exits with distinct codes: 0 (success), 1 (error), 2 (usage)
- `pyproject.toml` for standard Python packaging
- Test fixtures cover: normal, cycle, missing dep, empty, linear, fan,
  diamond, independent, zero-duration, no-edges