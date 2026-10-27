# PROMPTS.md — AI Collaboration Effectiveness

## Project: Job Scheduler with Dependency Resolution (DAG)

---

### Prompt 1 — Project Kickoff

> **Prompt** (via Claude Code):  
> *Please implement a DAG job scheduler for a university coding challenge (PS5).  
> Requirements: M1–M5 (validate cycles/missing deps, topo sort, parallel stages with worker limit, critical path, failure simulation).  
> My dir is empty — set up the full project including tests, README, sample JSONs, and CLI.*

**What happened** — The agent designed the full project skeleton first:
`src/` (models, engine, CLI), `tests/`, and `samples/`.  It inspected the
environment, found no Python, and accommodated that by writing portable
stdlib-only code.  Each module (M1–M5) was implemented as a pure function
composable by a top-level `build_plan()` orchestrator.

**Why it worked well**
- I gave a clear numbered list of “M1–M5” which the agent could decompose
  into independent functions and tests.
- The agent wrote sample JSON inputs alongside the code so the whole thing
  is self-contained and runnable without an internet connection.

---

### Prompt 2 — Test Coverage & Edge Cases

> **Prompt**:  
> *Add more tests — edge cases like zero-duration jobs, disconnected  
> components, worker_limit=1, fan-in/fan-out, multiple sinks for critical path.*

**What happened** — The agent added 25+ additional parametrised test cases,
each named for the edge case it covers.  It also validated the CP algorithm
picks the correct branch in a weighed diamond (not just any longest path).

**Why it worked well**
- The request was specific about which edge cases to exercise, so the agent
  didn't have to guess which corner-case behaviours matter.

---

### Prompt 3 — JSON output and CLI ergonomics

> **Prompt**:  
> *The rubric mentions "runnability" — give me a CLI that can also output  
> JSON and let me extract individual modes (--only validate, --only stages, …).*

**What happened** — The agent extended `cli.py` with `--json` and
`--only <mode>` flags.  The `ExecutionPlan.to_dict()` / `.to_json()` methods
serialise the full analysis so other tools can consume it.

**Why it worked well**
- Clear ask about output format and mode isolation.  The agent mapped each
  `--only` value to the corresponding module so they are independently
  exercisable.

---

### Reflection

**What the agent did well**
- Broke the problem into small, testable pure functions.
- Used standard algorithms (3-colour DFS, Kahn's, longest-path-in-DAG) with
  clear comments so the code is self-documenting.
- Wrote 45+ tests covering happy path, error paths, and edge cases.
- Used `pyproject.toml` for modern packaging with `pip install -e ".[dev]"`.

**Where I needed to guide**
- I had to explicitly ask for JSON output and `--only` flags (the rubric
  values "runnability", and a JSON mode lets other tools pipe in).
- Edge-case coverage benefited from a second prompt asking for specific
  scenarios the initial test set didn't explore.

**For future projects**
- State "JSON output" and "extract individual modes" in the initial prompt
  to get them in the first pass.
- Include "zero-duration jobs" and "disconnected components" in the
  acceptance criteria up front rather than as a follow-up.