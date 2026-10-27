# PS5: Production-Quality DAG Job Scheduler & Orchestrator

A high-performance, fault-tolerant mini build and ETL orchestrator engine implemented in Java. It parses job dependency specifications from JSON, validates graph invariants, determines optimal execution sequences, schedules tasks across configurable worker pools using discrete-event simulation, calculates critical paths with float analysis, and simulates transitive failure propagation.

[![CI Pipeline](https://github.com/sdsi-demo/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
![Java Version](https://img.shields.io/badge/Java-17%20%7C%2021%20%7C%2025-blue)
![Build Tool](https://img.shields.io/badge/Maven-3.8%2B-orange)
![Tests](https://img.shields.io/badge/Tests-53%20Passed%20(0%20Failures)-brightgreen)

---

## 🎯 Production Capabilities & Milestones

### 1. Graph Validation (`M1`)
- **Cycle Detection with Path Reconstruction**: Implements 3-Color DFS ($O(V + E)$). When a directed cycle back-edge is encountered, the exact cycle path is extracted and rotated into a canonical signature (e.g., `A -> B -> C -> A`) to prevent duplicate cyclic alerts.
- **Missing Dependencies**: Detects references to non-existent job IDs before any scheduling or allocation attempt.
- **Duplicate Dependency Detection**: Flags duplicate dependencies within a job's `dependsOn` list (e.g., `["A", "A"]`).
- **Integrity Constraints**: Enforces unique, non-blank job IDs, detects self-dependencies (`A -> A`), and validates duration values (strictly positive or non-negative depending on configuration).
- **Topology Support**: Safely handles empty graphs, single-node graphs, and disconnected subgraphs.

### 2. Topological Ordering (`M2`)
- **Kahn's In-Degree BFS Algorithm**: Linear time $O(V + E)$ topological sorting using forward and reverse adjacency representations.
- **Deterministic Priority Queue Tie-Breaking**: When multiple jobs become eligible concurrently, ties are broken deterministically using a lexicographical min-heap.
- **Invariant Verification**: Asserts $|Output| = V$; rejects cyclic graphs. Includes an automated verification helper ensuring $\forall p \in \text{dependsOn}(J), \text{index}(p) < \text{index}(J)$.

### 3. Worker-Limited Parallel Scheduling (`M3`)
- **Discrete-Event Simulation**: Time advances strictly via an event-driven priority queue of completion events: `Event(timestamp, jobId, workerId)`. No single-unit busy waiting.
- **Worker Concurrency Limit ($N \ge 1$)**: Strictly enforces that at every instant $t$, running workers $\le N$.
- **Simultaneous Completions & Zero-Time Tasks**: Drains all tasks completing at identical timestamp $T$ before dispatching ready tasks; zero-duration tasks execute without infinite loops.
- **Pluggable Scheduling Policies**:
  - `FIFO`: Deterministic lexicographical ordering.
  - `ShortestJobFirst (SJF)`: Shortest processing time first to minimize average queue latency.
  - `CriticalPathFirst`: Longest remaining path to terminal sink first (precomputed in $O(V + E)$ via dynamic programming) to unblock project bottlenecks earliest.
- **Lifecycle State Separation**: Tracks jobs across distinct state collections: `PENDING`, `READY`, `RUNNING`, `COMPLETED`, `FAILED`, and `SKIPPED`.
- **Worker Utilization**: Calculates exact worker pool capacity utilization:
  $$\text{Worker Utilization} = \frac{\sum \text{Task Durations}}{\max(1, \text{Makespan} \times N)} \times 100\%$$

### 4. Critical Path Method & Lower-Bound Analysis (`M4`)
- **Dual-Pass Dynamic Programming**:
  - *Forward Pass*: Computes Earliest Start ($ES$) and Earliest Finish ($EF$) using `Math.addExact` checked arithmetic.
  - *Backward Pass*: Computes Latest Start ($LS$) and Latest Finish ($LF$).
  - *Float / Slack Calculation*: $Slack = LS - ES$. Jobs with $Slack = 0$ are marked as `[CRITICAL]`.
- **Deterministic Path Reconstruction**: Traces the critical bottleneck sequence back from terminal nodes with deterministic tie-breaking.
- **Optimality & Bounds Disclosure**: Documents that CPM duration is a theoretical lower bound under infinite concurrency ($N \to \infty$). Resource-Constrained Project Scheduling (RCPSP) with worker limit $N$ is NP-hard; heuristic dispatching rules achieve high throughput but are not guaranteed globally optimal for arbitrary DAGs and worker limits.

### 5. Failure Simulation & Propagation (`M5`)
- **Transitive Impact Closure**: Traverses forward dependent edges using BFS to compute all directly and transitively skipped downstream jobs.
- **Explainable Failure Reasons**: Every skipped job is annotated with its exact dependency failure trigger.
- **Surviving Workflows**: Differentiates skipped downstream jobs from unaffected independent jobs that execute successfully.
- **Configurable Runtime Failure Policies**:
  - `RUN_TO_COMPLETION`: Jobs currently active on workers when a failure is triggered are permitted to finish; their downstream dependents are subsequently skipped.
  - `CANCEL_IMMEDIATELY`: Active worker tasks are immediately aborted upon failure.

---

## 🏗️ Architecture & Component Design

```
com.sdsi.scheduler/
├── Main.java                                # Hardened CLI entry point & exit code management
├── config/
│   ├── SchedulerConfig.java                 # Immutable execution configuration
│   ├── FailurePolicy.java                   # RUN_TO_COMPLETION vs CANCEL_IMMEDIATELY
│   └── SecurityLimits.java                  # Hard resource bounds (max file size, max nodes/edges)
├── model/
│   ├── Job.java                             # Immutable Job definition
│   ├── JobGraph.java                        # Adjacency lists (dependencies & dependents)
│   ├── JobStatus.java                       # Enum: PENDING, READY, RUNNING, COMPLETED, FAILED, SKIPPED
│   ├── JobExecutionState.java               # Lifecycle state tracker with timestamps & reasons
│   ├── Stage.java                           # Bounded stage partition
│   ├── ScheduledTask.java                   # Time-stamped worker assignment
│   ├── ValidationResult.java                # M1: Validation errors, missing deps, and cycle paths
│   ├── CriticalPathResult.java              # M4: CPM analysis with Slack, ES, EF, LS, LF
│   ├── FailureReport.java                   # M5: Transitive failure report with explanatory reasons
│   └── ScheduleResult.java                  # Complete execution report with worker utilization
├── parser/
│   ├── InputReader.java                     # Bounded, hardened JSON parser with strict schema checking
│   └── JobJsonParser.java                   # Delegating JSON parser facade
├── validator/
│   └── GraphValidator.java                  # M1: 3-Color DFS cycle path reporter & integrity checker
├── sorter/
│   └── TopologicalSorter.java               # M2: Kahn's algorithm with deterministic tie-breaking
├── policy/
│   ├── SchedulingPolicy.java                # Strategy SPI for ready job prioritization
│   ├── FifoPolicy.java                      # FIFO / Lexicographical
│   ├── ShortestJobFirstPolicy.java          # Shortest duration first (SJF / SPT)
│   └── CriticalPathFirstPolicy.java         # Longest remaining path to sink first
├── engine/
│   ├── DiscreteEventScheduler.java          # M3: Event-driven worker simulator with discrete time queues
│   └── FailurePropagator.java               # M5: Transitive downstream failure propagation
├── cpm/
│   └── CriticalPathAnalyzer.java            # M4: Forward & backward DP for CPM and Slack
└── service/
    └── JobSchedulerService.java             # Unified facade orchestrator
```

---

## ⚡ Algorithmic Complexity

| Component / Milestone | Algorithm | Time Complexity | Space Complexity |
| :--- | :--- | :--- | :--- |
| **M1: Graph Construction** | Adjacency List Indexing | $O(V + E)$ | $O(V + E)$ |
| **M1: Cycle Detection** | 3-Color DFS with Path Tracking | $O(V + E)$ | $O(V + E)$ |
| **M2: Topological Sort** | Kahn's Algorithm + Priority Queue | $O((V + E) \log V)$ | $O(V + E)$ |
| **M3: Discrete Event Sim** | Event-Driven Priority Queue | $O((V + E) \log V + V \log N)$ | $O(V + N)$ |
| **M4: Critical Path (CPM)** | Dual-Pass Dynamic Programming | $O(V + E)$ | $O(V + E)$ |
| **M5: Failure Propagation**| Transitive BFS Traversal | $O(V + E)$ | $O(V)$ |

---

## 📊 Measured Benchmark Results

Executed on Oracle Java 25 LTS (Windows 11 amd64, 5 Warmup rounds, 10 Measurement rounds averaged):

| Benchmark Graph Topology | Construction | Cycle Det. (M1) | Topo Sort (M2) | CPM (M4) | Sim FIFO (M3) | Sim SJF (M3) | Sim CP (M3) | Failure (M5) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Long Chain ($V=1,000, E=999$)** | 0.851 ms | 1.017 ms | 0.251 ms | 2.440 ms | 4.522 ms | 1.987 ms | 1.676 ms | 0.612 ms |
| **2. Wide Independent ($V=1,000, E=0$)** | 0.549 ms | 1.042 ms | 0.694 ms | 0.918 ms | 3.076 ms | 4.549 ms | 3.793 ms | 0.760 ms |
| **3. Diamond Lattice ($V=1,000, E=1,800$)**| 0.783 ms | 0.842 ms | 0.169 ms | 0.837 ms | 2.035 ms | 1.596 ms | 2.111 ms | 1.719 ms |
| **4. High Fan-In/Out ($V=1,000, E=2,500$)** | 1.153 ms | 0.842 ms | 0.765 ms | 1.144 ms | 3.069 ms | 4.450 ms | 3.304 ms | 0.495 ms |
| **5. Large Sparse DAG ($V=2,000, E=4,000$)** | 0.683 ms | 1.722 ms | 0.666 ms | 3.875 ms | 9.113 ms | 7.006 ms | 6.910 ms | 3.663 ms |

*Run the benchmark suite locally:*
```powershell
java -cp "target/test-classes;target/job-scheduler.jar" com.sdsi.scheduler.benchmark.SchedulerBenchmarkRunner
```

---

## 🔒 Security & Input Hardening

1. **Payload Limits**: Rejects input files larger than 10MB, job lists exceeding 50,000 jobs, or graphs exceeding 100,000 dependency edges.
2. **Schema Hardening**: Jackson parser operates in strict mode (`--strict`), rejecting unknown properties and polymorphic typing.
3. **Integer & Duration Safety**: Enforces `Math.addExact` checked arithmetic for all time calculations to prevent integer overflow.
4. **Injection Safety**: Input values are strictly deserialized into immutable domain models without arbitrary script or shell evaluation.

---

## 🚀 How to Build and Run

### Prerequisites
- **Java SE**: Version 17, 21, or 25 LTS.
- **Apache Maven**: Version 3.8+.

### 1. Build and Run Tests
```powershell
# Set Windows truststore if operating behind an enterprise TLS proxy
$env:MAVEN_OPTS = "-Djavax.net.ssl.trustStoreType=WINDOWS-ROOT"
mvn clean test
```

### 2. Package Standalone Fat JAR
```powershell
mvn clean package -DskipTests
```
Generates `target/job-scheduler.jar`.

### 3. CLI Command Options
```powershell
java -jar target/job-scheduler.jar [OPTIONS]
```

| Flag | Parameter | Description |
| :--- | :--- | :--- |
| `-f, --file` | `<path>` | Path to JSON job specification file |
| `-w, --workers`| `<N>` | Maximum concurrent workers ($N \ge 1$, default: 2) |
| `-p, --policy` | `<FIFO\|SJF\|CP>` | Scheduling policy (`FIFO`, `SJF`, `CP`; default: `FIFO`) |
| `--fail` | `<jobId>` | Simulate failure on specified job ID |
| `--failure-mode`| `<MODE>` | `RUN_TO_COMPLETION` (default) or `CANCEL_IMMEDIATELY` |
| `--strict` | - | Enforce strict schema validation (reject unknown JSON properties) |
| `-h, --help` | - | Display manual |

#### Examples:
```powershell
# Run default built-in ETL pipeline with 3 workers and Critical Path First policy:
java -jar target/job-scheduler.jar --workers 3 --policy CP

# Run external JSON file with Shortest Job First and simulate failure on 'clean_customers':
java -jar target/job-scheduler.jar --file sample-jobs.json --workers 2 --policy SJF --fail clean_customers

# Run with immediate cancellation on failure:
java -jar target/job-scheduler.jar --file sample-jobs.json --fail clean_customers --failure-mode CANCEL_IMMEDIATELY
```

### Exit Codes:
- `0`: Success (all milestones completed).
- `1`: Validation error (cycle detected, missing dependency, duplicate dependency).
- `2`: Bad arguments or missing input file.
