# PROMPTS.md — AI collaboration log

This documents the prompts, refinement iterations, and bug-fix cycles used
during development of the Job Scheduler.

---

## Prompt 1 — Scaffold and M1–M5

> *Given the problem statement (PS5: Job Scheduler with Dependency Resolution),
> write source code under submissions/anurag that implements:*
>
> 1. **M1** — Graph validation: detect cycles (report path) and missing deps.
> 2. **M2** — Topological sort (Kahn's algorithm).
> 3. **M3** — Parallel stage grouping with configurable worker limit.
> 4. **M4** — Critical path (longest path through DAG).
> 5. **M5** — Failure simulation: list all downstream jobs transitively
>    affected.
>
> *Also: tests, sample JSONs, README, CLI, error handling, input validation.*

**Result:** Wrote `scheduler.py` (core + CLI), `test_scheduler.py` (44 tests),
4 sample JSON files, and this README.

### Design decisions made during this prompt

- **`JobGraph` class** as single entry point — all operations validated
  through a shared adjacency representation.
- **Three-colour DFS** for cycle detection (white/grey/black).
- **`ValidationReport`** collects all errors in one pass instead of
  short-circuiting on the first.
- **`parallel_stages()`** uses a `deque` of ready jobs, grouped per stage,
  with a cap when `worker_limit > 0`.
- **Critical path** via DP over topological order (earliest-start-time).

---

## Prompt 2 — Bug fixes found by test suite

> *Run the tests, observe failures, fix them.*

Three bugs uncovered and resolved:

1. **`_build_adjacency` KeyError on missing deps** — The adjacency builder
   crashed when a dependency referenced an undefined job. **Fix:** Skip
   unknown deps during adjacency construction; `validate()` catches them
   later and reports them explicitly.

2. **`parallel_stages` `int(float("inf"))` → OverflowError** — Using
   `float("inf")` as the "unlimited" sentinel broke `int()` conversion.
   **Fix:** Branch on `worker_limit == 0` directly when computing the
   stage slice count instead of relying on infinity.

3. **DFS recursion depth on 1000-node chains** — Python defaults to 1000
   frames; a chain of 1000 jobs triggers `RecursionError` during cycle
   detection. **Fix:** Converted the recursive cycle-detection DFS to
   an iterative stack-based DFS that handles graphs of arbitrary depth.

**Verification:** All 44 tests pass after these three fixes. CLI produces
correct output for valid, cycle, missing-dep, and complex graphs.

---

## Prompt 3 — Documentation

> *Write README.md with quick start, API docs, sample files table, and
> design-decision rationale.*

**Result:** This `README.md` and `PROMPTS.md`.

---

## Lessons learned

- **Fuzz validation at construction vs. validation time.** Coercing graph
  construction to be strict on missing deps makes "report all errors"
  impossible. Deferring to `validate()` gives a better DX.
- **Iterative > recursive for graph algorithms on unbounded input.**
  Even "trivial" DFS cycle detection blows up on a chain of 1000 nodes.
  The iterative rewrite was simple and testable.
- **Sentinel values bite.** `float("inf")` is clean in theory but Python's
  `range()` needs an `int`. A zero-means-unlimited branch is simpler and
  avoids edge cases.