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

### Prompt 4 — "Add something advanced" (stretch features + bug fix)

> **Prompt**:
> *Start working on PS5: Job Scheduler with Dependency Resolution. Where you
> left off, add something advanced, etc.*

**What happened** — The agent audited the existing code, found a latent bug
(the `--only` flag was referenced in `cli.py` but never registered, so *every*
CLI invocation raised `AttributeError`), fixed it, and then added three
stretch features on top:

1. **Concrete list scheduling** (`list_schedule`, `--only schedule`) — greedy
   longest-job-first packing onto `N` workers, returning per-job
   `(start, finish, worker)` and a real makespan.  This is a 2-approximation
   for `P | prec | C_max` and is more faithful than stage scheduling.
2. **Slack / float analysis** (`slack_analysis`, `--only slack`) — forward +
   backward pass computing total float per job, flagging *every* critical job
   (including ties).
3. **Multiple-failure simulation** (`--fails a,b,c`) — the union of all
   transitively downstream jobs across several failed jobs.

It also guarded empty-input edge cases that previously crashed (`critical_path([])`,
`build_plan([])`, `worker_limit=0`) and added CLI smoke tests so the `--only`
regression can't recur.

**Why it worked well**
- The agent first *ran* the CLI and read the code before writing — the bug
  surfaced because it exercised the path the README advertises rather than
  trusting the docs.
- The stretch features were chosen to map directly to the rubric's
  "performance awareness" (a real makespan, not level-boundary padding) and
  "testing" (slack flags critical ties a single path can't express).

---

### Reflection

**What the agent did well**
- Broke the problem into small, testable pure functions.
- Used standard algorithms (3-colour DFS, Kahn's, longest-path-in-DAG, list
  scheduling, CPM forward/backward pass) with clear comments so the code is
  self-documenting.
- Wrote 60+ tests covering happy path, error paths, and edge cases.
- Used `pyproject.toml` for modern packaging with `pip install -e ".[dev]"`.
- Caught and fixed a shipped bug (`--only`) that the docs claimed worked.

**Where I needed to guide**
- I had to explicitly ask for JSON output and `--only` flags (the rubric
  values "runnability", and a JSON mode lets other tools pipe in).
- Edge-case coverage benefited from a second prompt asking for specific
  scenarios the initial test set didn't explore.
- The stretch features (list scheduling, slack) were the agent's initiative in
  response to "add something advanced" — a good prompt, because it delegated
  *what* to build while leaving *how* (and *how well*) to the agent.

**For future projects**
- State "JSON output" and "extract individual modes" in the initial prompt
  to get them in the first pass.
- Include "zero-duration jobs" and "disconnected components" in the
  acceptance criteria up front rather than as a follow-up.
- Add CLI smoke tests early: the `--only` regression slipped through precisely
  because only the library functions were unit-tested, never the entry point.