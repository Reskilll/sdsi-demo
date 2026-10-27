# Agent-Oriented Architecture

This document describes the project's design patterns, architectural decisions,
and concurrency model for the benefit of AI agents and human contributors
maintaining or extending the code.

## Architecture overview

The project follows a **layered pipeline** architecture:

```
 ┌──────────┐    ┌──────────────┐    ┌─────────────────┐    ┌───────────┐
 │ Raw JSON │───▶│ validation.py │───▶│   graph.Graph    │───▶│ CLI / API │
 │  input   │    │  parse_jobs() │    │ (built once,     │    │  server   │
 └──────────┘    │  M1           │    │  shared by all   │    │  text /   │
                 └──────────────┘    │  algorithms)     │    │  JSON /   │
                                     │                  │    │  SPA      │
                                     │ .topological_    │    └───────────┘
                                     │   order()  M2    │
                                     │ .schedule_stages │
                                     │   (workers) M3   │
                                     │ .critical_path_  │
                                     │   analysis() M4  │
                                     │ .downstream() M5 │
                                     └──────────────────┘
```

### Key design decisions

1. **Graph built once, reused by all algorithms.** The `Graph` class in
   `scheduler/graph.py` is a value object (`__slots__`, immutable after
   construction) that materialises forward and reverse adjacency in O(V + E).
   All five algorithmic stages (topological sort, cycle detection, barrier
   scheduling, critical path, failure propagation) read from the same
   `Graph` instance — the adjacency is never rebuilt.

2. **Validation is total (never raises).** `parse_jobs()` in
   `scheduler/validation.py` returns `(jobs, workers, errors)` for every input.
   It aggregates independent problems and only reports a cycle when the graph
   is otherwise structurally sound, avoiding confusing error cascades.

3. **Kahn's algorithm with lexicographic tie-breaking.** Every algorithm that
   processes ready jobs uses a min-heap keyed by job id. This makes all output
   deterministic regardless of input order — see the README for the trade-off
   vs. optimality.

4. **Barrier-based scheduling, not asynchronous.** Stages are discrete:
   every job in a stage finishes at the stage boundary before the next stage
   begins. This is a deliberate simplification mandated by the problem brief;
   see the README for limitations.

5. **Standard library only.** The only dependency is Python 3.11+. This is
   enforced — before adding a third-party import, confirm the problem brief
   requires it or a core requirement cannot be met otherwise.

## Adding a new algorithm

1. Add the method to `Graph` in `scheduler/graph.py`. Use the already-built
   `self._dependencies`, `self._dependents`, and `self._durations` — do not
   rebuild adjacency.
2. Add a thin façade in `scheduler/engine.py` calling the `Graph` method if
   the algorithm needs to be called standalone.
3. Export it from `scheduler/__init__.py`.
4. Add tests in `tests/`.

## Adding a new output format

1. Add the formatting logic in `scheduler/cli.py` (for CLI) or extend the
   result dict in `server.py` (for the HTTP API).
2. Keep diagnostics on stderr, data on stdout. The `--format json` output
   must always be valid JSON with no logging noise.

## Test strategy

- `tests/test_validation.py` — structural and semantic input validation (M1).
- `tests/test_graph.py` — topological ordering correctness (M2).
- `tests/test_scheduling.py` — worker-limited stage invariants (M3).
- `tests/test_critical_path.py` — critical-path math and path selection (M4).
- `tests/test_failure.py` — downstream propagation (M5).
- `tests/test_cli.py` — end-to-end via subprocess.
- `tests/test_properties.py` — randomized invariant tests over generated DAGs.

Tests assert known expected values for small graphs; they never mirror
implementation details. Randomized tests assert three invariants (worker
limit per stage, dependency readiness, critical-path ≤ total time).

## SPA test harness

`server.py` is a standard-library HTTP server serving `static/index.html`
and exposing `POST /api/schedule`. The frontend is a vanilla JS SPA that
sends JSON to the API and renders:

- A KPI row of stat tiles (total time, critical path duration, workers, stage
  count, skipped jobs).
- A topological-order line.
- Horizontal stage-duration bars (sequential palette, per the dataviz skill's
  reference colors). Each bar shows the enclosed job ids and duration, with a
  per-bar hover tooltip.
- Critical-path annotation list with per-job "why" explanations.
- A sortable per-job timing table with critical-path row highlighting.

The SPA uses the [dataviz skill](https://code.claude.com/docs/en/dataviz)'s
reference palette and mark specs: thin bars (28px, 4px rounded ends), 2px
surface gaps, KPI stat tiles, and text/content tokens rather than series-color
text. Dark mode is selectable via OS preference or a toggle, persisted in
`localStorage`.

## Directory map

```
umeshjhaAI/
├── main.py                 # CLI: python main.py --input sample.json
├── server.py               # HTTP server + REST API (standard library)
├── static/index.html       # SPA test harness frontend
├── sample.json             # example input
├── pyproject.toml          # packaging: pip install -e ., bin: jobsched
├── scheduler/
│   ├── __init__.py         # public API surface
│   ├── errors.py           # ValidationError with aggregated .errors list
│   ├── model.py            # Job, Stage, Schedule, JobTiming,
│   │                       #   CriticalPathReason dataclasses
│   ├── validation.py       # parse_jobs() — total parsing + M1 validation
│   ├── graph.py            # Graph value object + all algorithms (M2–M5)
│   ├── engine.py           # façade over Graph, plus explain_critical_path
│   └── cli.py              # argparse CLI + text/JSON formatting
├── tests/
│   ├── test_validation.py
│   ├── test_graph.py
│   ├── test_scheduling.py
│   ├── test_critical_path.py
│   ├── test_failure.py
│   ├── test_cli.py
│   └── test_properties.py  # randomized DAG invariants
├── AGENTS.md               # this file
├── README.md
├── PROMPTS.md
└── .gitignore
```