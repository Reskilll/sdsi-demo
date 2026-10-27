# AI-Assisted Development Process

This document records how this mini job scheduler was designed and built with
AI assistance. It is an honest account: nothing here claims a command was run
or a test passed that did not actually happen.

## Problem decomposition

The brief breaks into five core modules (M1–M5) plus integration and
documentation:

1. **Input validation (M1)** — parse JSON safely, then validate every field and
   aggregate independent errors.
2. **Topological sort (M2)** — produce one deterministic valid execution order.
3. **Stage scheduling (M3)** — group jobs into worker-limited barrier stages.
4. **Critical path (M4)** — DP over the DAG for earliest start/finish and the
   longest weighted path.
5. **Failure propagation (M5)** — compute the transitive downstream closure of a
   failed job.

The chosen decomposition keeps each concern in its own module (`validation.py`,
`graph.py`, `engine.py`, `cli.py`) with a small `model.py` for shared data
classes and `errors.py` for a single validation-error type.

## Algorithms selected and why

- **Kahn's algorithm** for topological sorting: naturally detects cycles (nodes
  left over after draining indegree-zero nodes) and produces an order while
  iterating. A **min-heap** keyed by job id gives deterministic lexicographic
  tie-breaking with O(V log V) overhead.
- **Cycle reconstruction**: after Kahn leaves residual nodes, a forward walk
  over the residual subgraph is guaranteed to revisit a node, yielding a real
  `A -> B -> ... -> A` path rather than an unordered node set.
- **Greedy barrier scheduling**: at each stage pop up to `workers` ready jobs
  from the min-heap (lexicographic), release newly-ready dependents, repeat.
  This matches the required "as many ready jobs as possible, up to the limit,
  deterministically" semantics.
- **Critical path via dynamic programming**: process jobs in topological order;
  `start[j] = max(finish[pred])` and `finish[j] = start[j] + duration[j]`.
  O(V + E). A representative path is reconstructed backwards, tie-broken by
  smallest id, so it is deterministic.
- **Failure propagation via BFS** over the reverse (dependent) adjacency,
  giving the transitive downstream closure in O(V + E).

## Edge cases considered

Covered in the test suite: empty graph; single job; chain; independent jobs;
disconnected components; diamond; multiple prerequisites; duplicate ids;
missing dependency references; self-dependency; two-job cycle; longer cycle; a
cycle in one component with valid jobs elsewhere; worker count of 1; worker
count greater than the job count; invalid workers (zero, negative, float,
boolean); missing/malformed duration; zero/negative durations; `NaN` and
`Infinity` durations; invalid and wrong-structure JSON; multi-branch failure;
failure of a job with no dependents; unknown failed job; equal-duration
critical paths; ids that look like numbers, contain punctuation, or are not
lexicographically ordered; determinism across repeated runs; one-of-many
prerequisites failing; fractional durations; and a greedy-choice case where the
pick affects completion time.

A few subtle points resolved during implementation:

- **Booleans are `int` subclasses** in Python, so `workers`/`duration`
  validation must reject `bool` explicitly before accepting `int`.
- **Non-finite floats**: `float('nan')` and `float('inf')` parse fine from a
  Python object but must be rejected via `math.isfinite`.
- **Cycle vs. self-dependency**: a self-dependency (`A -> A`) is reported as a
  "cannot depend on itself" structural error, not folded into the generic cycle
  message.
- **Error aggregation**: structural errors are collected first; cycle detection
  runs only when the graph is otherwise structurally sound, avoiding confusing
  cycle messages on top of malformed jobs.

## Tests run and their outcomes

The suite is `unittest`-based (`tests/`), run with:

```
python -m unittest discover -s tests -v
```

Final result: **86 tests, all passing** (ran via `py -3` on Windows).

Three of the initial test expectations were corrected during development
(implementation behavior was correct; the test expectations were wrong):

- The topological order for the sample is `extract -> transform -> validate ->
  load` because after `extract`, both `transform` and `validate` are ready and
  `"transform" < "validate"` lexicographically. The test had asserted
  `validate` before `transform`.
- `propagate_failure([], "x")` correctly raises an "unknown failed job" error,
  since an empty graph has no known ids; the test had expected an empty list.

A fourth correction was made while adding the critical-path explanation: the
start-of-path reason string initially said "feeds the next job" without naming
that job, which a test asserted against; the string was updated to name the
downstream job explicitly.

## Enhancements (added after the core requirements passed)

Three lower-risk enhancements were added on request, each with test coverage:

1. **Critical-path explanations** — a `CriticalPathReason` model and
   `explain_critical_path()` in `engine.py`, surfaced in both text and JSON
   output, explaining why each job is on the representative critical path.
   Covered by `test_critical_path_reasons`.
2. **Randomized property-based DAG tests** — `tests/test_properties.py`
   generates acyclic graphs and asserts three invariants (worker limit per
   stage, dependency readiness, and critical-path ≤ worker-limited total) over
   hundreds of random DAGs plus a deep-chain and many-independent-jobs stress
   case.
3. **Packaging** — `pyproject.toml` with a `jobsched` console script entry
   point; verified with `pip install -e .` in a throwaway venv.

## Implementation trade-offs

- **Aggregated validation** reports all independent problems at once, at the
  cost of slightly more bookkeeping in the validator (jobs with unusable ids
  are skipped for subsequent per-job checks).
- **Barrier-based scheduling** is a deliberate simplification mandated by the
  brief; it is not an optimal or fully asynchronous scheduler.
- **Determinism over optimality**: the greedy "smallest id first" rule is
  deterministic but not guaranteed to minimize completion time in every case
  (documented in the README).
- **Standard library only**: no third-party dependencies, which keeps the
  project trivially runnable but means using `unittest` rather than a heavier
  test framework.

## Genuine AI prompts used

The following are the actual prompts supplied to the AI during this task
(reproduced in full, unmodified):

1. The full competition brief (the "Build a Production-Quality Mini Job
   Scheduler with DAG Dependency Resolution" prompt), which specified all five
   core requirements, the input/output interface, hidden-test expectations,
   testing requirements, documentation requirements, and the definition of
   done.

2. The instruction "continue" after the initial repository inspection, to
   proceed from planning into implementation.

3. "suggest what can be done over top of this?" — a request to propose
   follow-up work, which led to the enhancements listed above.

4. "implement 'lower effort / nice-to-have' and push" — the instruction to
   implement the critical-path explanations, property-based tests, and
   packaging, then commit and push.

No other prompts were issued. No illustrative prompts are included beyond the
ones above.
