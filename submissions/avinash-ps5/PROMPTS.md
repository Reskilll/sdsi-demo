# PROMPTS.md — AI Collaboration Log

## Session prompts

### Prompt 1 — Scaffold the project

> I need to build PS5: Job Scheduler with Dependency Resolution (DAG) for the
> SDSI hackathon. The repo is at avinash1315/sdsi-demo.git. The spec:
> M1 Validate graph (cycle detection + missing deps), M2 Topological sort,
> M3 Parallel stages with worker limit, M4 Critical path / min completion time,
> M5 Failure simulation (downstream skip). Also judged on edge cases, code
> quality, testing, docs, PROMPTS.md, security, git hygiene, error handling.
> Build it as a Python package under submissions/avinash-ps5/.

**Reasoning**: Gave the full problem statement and all judging criteria so the
AI could plan the complete submission in one shot — domain model, graph algo
modules, scheduler module, validator, CLI, test suite, sample inputs, and docs.

### Prompt 2 — Refine the scheduler logic

> The first version of the scheduler had messy event-loop logic. I asked the
> model to rewrite it as a clean greedy list-scheduler using a priority queue
> of busy workers, which is clearer and correct.

**Reasoning**: The first attempt was overcomplicated with ad-hoc time stepping
and edge-condition flags. The clean heap-based approach (dispatch ready jobs,
advance to the next completion event, release workers) is standard, testable,
and easier to reason about.

### Prompt 3 — Fix level computation and add edge-case coverage

> The topological sort's original level grouping was fragile (tracking "current"
> vs "next" level queues). We replaced it with a simple BFS longest-distance
> computation — each node's level is `max(parent_level) + 1` — which is both
> correct for parallel-stage grouping and independent of enqueue order.

**Reasoning**: The evaluator rubric includes parallel-stage grouping. The
longest-path level assignment is the right semantic for "all jobs at this
level can run once their dependencies (at earlier levels) are done."

## What the AI did well

1. **Domain separation**: Graph algorithms (pure), scheduling (time-aware),
   validation (input sanitisation), CLI (presentation) — each in its own module.
2. **Testing**: 30+ tests covering happy paths, every validation error, edge
   cases (self-loops, zero workers, large limits, deep chains, failures at
   various positions).
3. **Input safety**: JSON loading via `json.loads`, identifier sanitisation,
   explicit error messages.
4. **Samples**: 8 JSON files covering real-world pipelines, trivial cases,
   and error cases.

## What I (the human) had to steer

- The first scheduler was over-engineered — I asked for a cleaner rewrite.
- Pointed out that the `missing_dep.json` sample had the wrong dependency; the
  model fixed it.
- Reminded it to keep the conftest.py for pytest import path resolution.

## Key AI collaboration takeaways

- Giving the full rubric upfront (all M1–M5 + judging criteria) let the model
  plan a complete design rather than iterating feature-by-feature.
- Asking "write me a cleaner version of this function" after seeing messy code
  works better than trying to fix it incrementally.
- Sample input files act as an implicit spec — the model catches errors (like
  the missing_dep sample bug) when it writes tests against them.