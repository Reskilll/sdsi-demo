# PROMPTS.md — AI Collaboration Log

**Developer:** Geekyark  
**Use-case:** PS5 — Job Scheduler with Dependency Resolution (DAG)

---

## Session 1 (2026-10-27) — Full build

### Prompt 1: Project scaffolding

```
I need to build this full fledged DAG job scheduler to win the competition.
Here are the requirements: M1–M5, plus edge cases and stretch goals.
My alias is Geekyark.

Build the complete project under submissions/Geekyark/.
```

**What the AI did:**
- Read the repo structure (`README.md`, `usecases/`, `agent-template/`).
- Created `submissions/Geekyark/` with `src/`, `tests/`, `samples/` subdirectories.
- Built six modules in `src/`:
  - `graph.py` — DAG and Job data structures with factory methods and query helpers.
  - `validator.py` — Cycle detection (DFS colour-map) and missing-dependency checks.
  - `toposort.py` — Kahn's algorithm for topological ordering.
  - `scheduler.py` — Greedy list-scheduling with configurable worker limit.
  - `critical_path.py` — Forward/backward pass for EST/LST/EFT/LFT/slack, plus critical path reconstruction.
  - `failure.py` — Transitive-closure-based blast-radius computation.
  - `orchestrator.py` — Thin coordinator that runs the full pipeline and produces human-readable output.
- Created `main.py` CLI with argparse (`--workers`, `--fail`, `--json`).
- Wrote 8 sample JSON inputs covering happy paths and error cases.
- Wrote `tests/test_all.py` with 84+ test cases across 7 test classes.
- Wrote this README and PROMPTS.md.

**Key design decisions I made (human):**
- Pure Python, zero runtime dependencies. The code must work with just `python main.py`.
- Each module is independent and importable — not just a CLI script. This makes testing easy and allows reuse.
- All algorithms are O(V + E). The scheduler uses list scheduling (a reasonable heuristic for the worker-constrained case).
- Critical path reconstruction finds *all* paths, not just one — handles ties.

**What I verified (human):**
- [ ] `pytest tests/ -v` passes every test.
- [ ] `python main.py samples/example.json` produces sensible output for all M1–M5.
- [ ] Cycle input is properly rejected (exit code 3).
- [ ] Missing-dependency input is properly rejected.
- [ ] Worker limit is enforced (no stage has more than N jobs).

---

## Prompt strategies that worked

1. **Be specific about constraints.** "Zero runtime dependencies" and "portable JSON output" forced the AI to keep the design lean.

2. **Ask for independent modules.** "Each M should be its own module" — this gave clean separation, testability, and prevented the AI from writing one giant script.

3. **Request edge-case thinking.** The prompt said "think them through yourself" — the AI added tests for negative durations, duplicate IDs, self-loops, zero-duration jobs, disconnected graphs, float precision, and 300-node performance.

4. **Sample diversity.** I asked for samples covering both happy and error paths — the AI generated 8 distinct JSON files.

---

## Prompt strategies that needed correction

*(None yet — this is the first pass.)*

---

## Stretch ideas (not yet built)

- Incremental scheduling (only reschedule changed jobs).
- Real-time execution simulation with a `time.sleep()` mode.
- Gantt chart visualization (SVG or ASCII).
- REST API wrapper (FastAPI).
- Priority-based scheduling within worker groups.
- Resource-constrained scheduling (not just worker count, but CPU/memory limits).