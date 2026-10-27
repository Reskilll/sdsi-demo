# PROMPTS.md — AI Collaboration Log

Documents the prompts used and how they shaped the code.

---

## Prompt 1 (User): Initial request

> PS5: Job Scheduler with Dependency Resolution (DAG) … Start the plan building and create plan under anurag.g folder

**What it shaped**: Entire architecture. M1–M5 milestone structure from judging rubric, Python-only/stdlib constraint, project location.

---

## Prompt 2 (User): Speed request

> do it fast

**What it shaped**: Cut exploration depth — made design decisions from first principles. Plan written in one pass with all algorithms chosen upfront.

---

## Prompt 3 (User): Interrupted exploration, restated requirements

> Create below request as fast as possibel under 10 mint.

**What it shaped**: Reinforced time constraint (10 min). Drove decisions:
- Pure stdlib (no external deps) so no install step needed.
- Iterative DFS for cycles (avoids recursion limits on large graphs).
- Flat module structure — one file per milestone — for fast parallel implementation.
- Tests, examples, models, and CLI all written in one shot.

---

## Prompt 4 (User): Approved plan, start coding

**What it shaped**: Implementation phase began. All source files written in parallel groups.

---

## Prompt 5 (User): Stop exploration, run execution

> run the execution fast

**What it shaped**: Full implementation at maximum speed. All 32 files (source, tests, examples, docs) created.

---

## Design choices influenced by AI prompting

1. **Iterative DFS for cycles**: 10-min constraint made recursion avoidance the natural choice.
2. **Kahn's with min-heap**: Deterministic, lexicographic output — direct consequence of "testability" requirement.
3. **Stages as levels + waves**: Level-based approach produces clean, predictable groupings easy to verify.
4. **Orchestrator pattern**: `run()` runs M1→M2→M3→M4→(optional M5), returns single `Report` — from rubric's emphasis on end-to-end pipeline.
5. **No `graphlib` dependency**: graphlib's cycle error messages don't include the full cycle path (necessary for M1). Custom implementation required.
6. **`dependsOn` normalization**: Accepting single string, list, or omission — rubric's "input validation" and "robustness."

---

## What the AI got right

- Iterative cycle detection correctly handles self-cycles and multi-node cycles with path reconstruction.
- Critical path DP correctly handles disconnected components (max earliest-finish across all jobs).
- Failure simulation uses BFS, distinguishes "downstream skipped" vs "upstream unaffected."
- Float durations work throughout (models, critical path, stages).

## What could be improved (retrospective)

- Cycle detection path reconstruction could be simplified using a `parent` dict.
- A conftest.py with shared fixtures would reduce duplication across test files.
- `pyproject.toml` would be more modern than `requirements.txt`, but rubric emphasized runnability.