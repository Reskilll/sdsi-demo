# AI Collaboration & Engineering Log (PROMPTS.md)

**Problem Statement:** PS5: Job Scheduler with Dependency Resolution (DAG)  
**Track:** Developer Track — SDSI Agentic AI Hackathon  
**Author:** `divya.j`  
**Collaborative AI:** Antigravity (Advanced Agentic Coding Assistant)

---

## 1. Collaboration Strategy & Architectural Evolution

The development progressed through two major engineering cycles:

1. **Cycle 1: Baseline Prototype (Scaffold to Functional)**
   - Initial review of hackathon instructions in `README.md` and `agent-template/agent.py`.
   - Creation of the core graph data structures, basic 3-color DFS cycle detector, Kahn's algorithm, basic CPM, and reachability-based failure simulation.
   - Initial test suite of 29 tests validating basic functionality.

2. **Cycle 2: Production Hardening (The Master Prompt Overhaul)**
   - Thorough inspection and audit identifying 8 architectural, algorithmic, security, and concurrency gaps.
   - Decomposition into hardened modular packages: `config`, `model`, `parser`, `validator`, `sorter`, `policy`, `engine`, `cpm`, and `service`.
   - Implementation of pluggable `SchedulingPolicy` SPI (`FifoPolicy`, `ShortestJobFirstPolicy`, `CriticalPathFirstPolicy`).
   - Implementation of event-driven `DiscreteEventScheduler` handling simultaneous completions, zero-time events, and active job cancellation modes.
   - Invariant testing against randomly generated DAGs and CLI harness integration tests.
   - Addition of a reproducible benchmark harness measuring performance on 5 distinct graph topologies up to 2,000 nodes.
   - Total test count expanded to **53 automated tests** (100% passing).

---

## 2. Prompts & Technical Dialogues

### Prompt 1: Initial Problem Setup
- **User Prompt:**
  > "I have to solve a problem using java code, write most optimised code and error handling using all edge cases, my problem statement: PS5: Job Scheduler with Dependency Resolution (DAG)..."
- **AI Action:**
  - Audited local Java 25 LTS and Apache Maven 3.10.0 environment.
  - Resolved Maven TLS certificate path exception in enterprise proxy environment by introducing `-Djavax.net.ssl.trustStoreType=WINDOWS-ROOT`.
  - Built initial implementation and verified 29 tests.

### Prompt 2: The Master Prompt (Senior Architect & QA Review)
- **User Prompt:**
  > "Act as a Senior Java Backend Engineer, Algorithms Specialist, Software Architect, and QA Engineer.
  > Thoroughly audit, improve, optimize, test, and document the existing project...
  > Enforce: M1 (unique IDs, duplicate dependencies, cycle path), M2 (Kahn's deterministic tie-breaking), M3 (discrete-event simulation, pluggable policies: FIFO, SJF, CP, separate collections, worker utilization), M4 (CPM, float, lower-bound disclosure), M5 (failure simulation, configurable cancellation), security limits, random DAG invariant testing, JMH/benchmark harness, CI workflow."

- **AI Technical Response & Fixes:**
  1. *Audit & Gap Identification:* Cataloged defects (SEC-01, ALG-01, COR-01, COR-02, COR-03, ALG-02, PRF-01, OPS-01).
  2. *Duplicate Dependency Detection (M1):* Extended `JobGraph` and `GraphValidator` to track raw dependency lists and explicitly detect duplicate references (e.g. `["A", "A"]`).
  3. *Pluggable Policies (M3):* Created `SchedulingPolicy` interface and implemented `FifoPolicy`, `ShortestJobFirstPolicy`, and `CriticalPathFirstPolicy` (precomputing remaining downstream paths in $O(V + E)$ via dynamic programming).
  4. *Simultaneous Completion Handling (M3):* Redesigned completion event loop in `DiscreteEventScheduler` to drain all events at identical timestamp $T$ before evaluating worker availability and eligible tasks.
  5. *Arithmetic Overflow Protection (M4):* Replaced all naive `+` operations on timestamps and durations with `Math.addExact`.
  6. *Deterministic Tie-Breaking on Critical Paths (M4):* Added lexicographical tie-breaking for equal-duration predecessor paths and terminal nodes.
  7. *Security Bounds (Sec):* Created `SecurityLimits` and `InputReader` enforcing 10MB maximum file size, 50,000 max jobs, 100,000 max dependencies, and strict schema validation mode.
  8. *Property-Based Invariant Verification:* Added `SchedulingInvariantsTest` generating randomized DAGs with up to 60 nodes and asserting concurrency limits, dependency ordering, and makespan bounds.
  9. *CI Workflow:* Added `.github/workflows/ci.yml` matrix testing across Java 17 and 21 on Ubuntu and Windows.

---

## 3. Verified Invariants & Test Results

Executed with Maven Surefire on Java 25 LTS:
```
Tests run: 53, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

Key test coverage highlights:
- **`SchedulingInvariantsTest`**:
  - `finishTime(dep) <= startTime(job)` for all dependencies.
  - `runningTasks(t) <= N` across all interval boundary checkpoints.
  - `totalMakespan >= criticalPathDuration` (makespan bound).
  - Determinism across repeated executions with identical configuration.
- **`DiscreteEventSchedulerTest`**:
  - Simultaneous completions at identical timestamp.
  - Zero-duration task execution without infinite loops.
  - `RUN_TO_COMPLETION` vs `CANCEL_IMMEDIATELY` failure modes.
- **`CliIntegrationTest`**:
  - Exit codes: `0` (success), `1` (validation / cyclic error), `2` (argument / file error).
- **`SchedulerBenchmarkRunner`**:
  - Benchmarked across 5 topologies (Long Chain, Wide Layers, Diamond Lattice, High Fan-In/Out, Large Sparse DAG).
  - Validated sub-10ms throughput on 2,000-node DAGs.

---

## 4. Architectural Trade-offs & Limitations

1. **RCPSP Heuristic Optimality**:
   - The Critical Path duration represents an unconstrained lower bound.
   - Resource-Constrained Project Scheduling (RCPSP) with worker limit $N$ is proven NP-hard. Heuristic dispatching rules (FIFO, SJF, Critical Path First) provide polynomial-time $O((V+E)\log V)$ solutions that maximize throughput, but cannot guarantee the mathematically minimal makespan for arbitrary DAGs and worker limits.
2. **Recursion vs Iteration in Cycle Detection**:
   - 3-Color DFS is used with recursion depth bounded by the graph height. For deeply nested DAGs ($> 10,000$ sequential nodes), JVM `-Xss` stack size should be increased or an iterative stack used.
