# Mini Job Scheduler with DAG Dependency Resolution

A production-quality mini job scheduler / ETL orchestrator. It reads a JSON
description of jobs and their dependency relationships, validates the input
thoroughly, and produces a deterministic analysis: a topological execution
order, a worker-limited barrier-based stage schedule, critical-path analysis,
and downstream failure propagation.

It is a pure analysis engine — it **never executes** shell commands, arbitrary
code, or network operations.

## Features

- **Input validation (M1)** — validates every field and aggregates independent
  errors, reporting clear messages (duplicate ids, missing dependencies,
  self-dependencies, directed cycles with a real path, invalid workers, etc.).
- **Topological ordering (M2)** — Kahn's algorithm with lexicographic
  tie-breaking for deterministic output; supports disconnected components and
  empty graphs.
- **Worker-limited stage scheduling (M3)** — barrier-based stages, each with at
  most `N` jobs whose dependencies finished in earlier stages.
- **Critical-path analysis (M4)** — dynamic programming over the DAG to compute
  earliest start/finish, the longest weighted path, and a representative
  critical path.
- **Failure propagation (M5)** — given a failed job id, reports every transitive
  downstream dependent that must be skipped.
- **CLI** — human-readable text output by default, and machine-readable JSON.

## Prerequisites

- Python 3.11+ (uses only the standard library).
- On Windows, run with `py -3` if `python` is not on `PATH` (the Microsoft
  Store `python` alias does not point at a real interpreter).

## Setup

No dependencies to install. The package has no third-party requirements.

```bash
# optional: create and activate a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate    |   Unix: source .venv/bin/activate
```

## How to run

```bash
python main.py --input sample.json
python main.py --input sample.json --workers 2
python main.py --input sample.json --failed-job transform
python main.py --input sample.json --format json
```

On Windows without `python` on PATH:

```bash
py -3 main.py --input sample.json
```

### CLI options

| Option          | Description                                                        |
|-----------------|--------------------------------------------------------------------|
| `--input PATH`  | (required) path to the JSON input file                             |
| `--workers N`   | worker limit; **overrides** the JSON `workers` field when supplied |
| `--failed-job X`| simulate failure of job `X` and report skipped downstream jobs     |
| `--format`      | `text` (default) or `json`                                         |

### Exit codes

- `0` — success.
- `1` — validation error, cycle, or unknown `--failed-job` id.
- `2` — CLI usage error (argparse).

Diagnostics are written to **stderr**; `--format json` keeps stdout as valid
JSON with no logging noise mixed in.

## Input JSON schema

```json
{
  "jobs": [
    {"id": "extract",   "duration": 3, "dependsOn": []},
    {"id": "validate",  "duration": 2, "dependsOn": ["extract"]},
    {"id": "transform", "duration": 4, "dependsOn": ["extract"]},
    {"id": "load",      "duration": 2, "dependsOn": ["validate", "transform"]}
  ],
  "workers": 2
}
```

- `jobs` (required): a list of job objects.
- Each job:
  - `id` (required): a unique, non-empty string.
  - `duration` (required): a positive, finite number (integer or float; `bool`,
    `NaN`, and `Infinity` are rejected).
  - `dependsOn` (optional): a list of dependency ids (strings). May be omitted
    or empty.
- `workers` (optional): a positive integer (defaults to `1` when omitted from
  both the JSON and the CLI).

## What each result means

### Topological order

A linear ordering where every prerequisite appears before its dependent. Ties
are broken lexicographically by job id, so output is deterministic.

### Parallel stages (worker-limited)

Jobs are grouped into discrete, barrier-based stages. Each stage:

- contains at most `workers` jobs,
- contains only jobs whose dependencies finished in earlier stages, and
- runs for the maximum duration of the jobs in it.

The total completion time is the sum of the stage durations. For example, three
independent jobs of durations 2, 5, and 3 with two workers schedule as:

- Stage 1: durations 2 and 5 → stage duration 5
- Stage 2: duration 3 → stage duration 3
- Total: 8

### Critical path (unlimited workers)

The longest weighted path through the DAG, computed with dynamic programming.
For each job, the earliest start is the maximum earliest finish of its
dependencies; the earliest finish is start + duration. The critical-path
duration is the maximum earliest finish over all jobs (0 for an empty graph).

**Important distinction:** the critical-path duration assumes *unlimited*
parallel workers with zero scheduling overhead. It is a lower bound, **not**
the completion time of the worker-limited barrier schedule. The two are only
equal when the worker limit never causes waiting.

### Failure propagation

For a failed job `F`, the skipped set is every job reachable from `F` through
dependency edges (direct and indirect dependents). It excludes `F` itself, its
prerequisites, and unrelated jobs. The result is reported in lexicographic
order.

## Validation and error behavior

Validation happens **before** any scheduling or critical-path computation; an
invalid graph never produces a partial or misleading schedule. Independent
errors are aggregated into one report. A cycle is reported as a real path, e.g.
`A -> B -> C -> A`. Malformed JSON is reported without a stack trace.

## Testing

```bash
python -m unittest discover -s tests -v
# Windows:  py -3 -m unittest discover -s tests -v
```

The suite covers all core requirements and edge cases: empty graphs, chains,
independent jobs, disconnected components, diamonds, multiple dependencies,
duplicate ids, missing/self dependencies, two- and multi-job cycles, cycles in
one component only, worker limits (1, greater than job count, invalid values
including booleans), malformed/missing/zero/negative/non-finite durations,
invalid JSON, multi-branch failure, jobs with no dependents, unknown failed
jobs, equal-duration critical paths, non-lexicographic ids, fractional
durations, and determinism across runs — plus end-to-end CLI tests.

## Algorithmic complexity

For `V` jobs and `E` dependency edges:

| Analysis             | Complexity                         |
|----------------------|------------------------------------|
| Validation           | O(V + E) (plus cycle detection)    |
| Topological sort     | O(V + E) (heap ops add O(V log V)) |
| Stage scheduling     | O(V + E + V log V)                 |
| Critical path        | O(V + E)                           |
| Failure propagation  | O(V + E)                           |

All graph traversals are linear in the graph size, plus deterministic sorting
overhead (a min-heap keyed by id).

## Project layout

```
umeshjhaAI/
├── main.py                 # CLI entry point
├── sample.json             # example input
├── scheduler/
│   ├── __init__.py         # public API
│   ├── errors.py           # error types
│   ├── model.py            # Job / Stage / Schedule dataclasses
│   ├── validation.py       # parsing + M1 validation
│   ├── graph.py            # adjacency + M2 topological sort
│   ├── engine.py           # M3 stages, M4 critical path, M5 failure
│   └── cli.py              # argparse CLI + text/JSON formatting
└── tests/                  # unittest suite
```

## Known limitations and scheduling assumptions

- The stage model uses **barrier-based** scheduling: every job in a stage is
  assumed to finish at the stage boundary. It does not model a fully
  asynchronous, event-driven scheduler where a worker could pick up a new job
  the moment one finishes.
- The greedy ready-job selection (smallest id first) is deterministic but not
  guaranteed to minimize the total completion time for all inputs; that would
  require an optimal scheduling algorithm beyond the required scope.
- Durations are positive finite floats; fractional durations are supported.
- `workers` defaults to `1` when neither the JSON nor the CLI specifies it.
- Duplicate dependency entries within a single job are treated as one edge.
