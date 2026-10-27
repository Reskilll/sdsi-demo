# 🤖 AI Collaboration Record & Design Rationale (PROMPTS.md)

This document records the prompt progression, architectural deliberations, trade-offs, and verification steps taken during pair programming on the **Flash Sale Overselling Prevention** system.

---

## 1. Initial Brief & Requirements Deconstruction

### User Request
> "Prevent overselling during a flash sale.
> What your code is judged on:
> M1 Load products and stock from some sample input file like inventory.json (or similar).
> M2 Reserve stock for a user, held for a TTL (default 120 s).
> M3 Confirm permanently deducts the stock. Cancel or TTL expiry releases it.
> M4 Enforce a per-user purchase limit per SKU.
> M5 Report available, reserved and sold counts per SKU.
> Also judged on: Functional correctness · Code quality and design · Testing · Documentation and runnability (README) · AI collaboration effectiveness (PROMPTS.md) · Security and robustness · Git hygiene · Performance awareness · Error handling and input validation.
> Your code is also checked against edge cases that aren’t listed here: think them through yourself.
> Anything you build on top as a stretch or bonus also carries weight in your selection."

### Key Engineering Challenges Identified
1. **Race Conditions & Overselling**: In a flash sale, 100+ requests hit the same SKU at the same millisecond. Simple read-modify-write patterns result in stock overselling.
2. **Lock Granularity & Contention**: A single global lock blocks all requests across all products, degrading throughput. A per-SKU locking architecture is required.
3. **Reservation TTL Expiry Reliability**: Background timers alone can suffer from thread starvation or timer jitter. We need **both active background sweeping and passive on-demand verification**.
4. **Per-User Quotas**: Tracking both active reservations and completed purchases per user per SKU. If an active reservation is cancelled or expires, the quota must be immediately restored.
5. **Invariant Integrity**: $\text{initial\_stock} = \text{available} + \text{reserved} + \text{sold}$ must be mathematically preserved across all states.

---

## 2. Iterative Design Dialogue & Decision Log

### Phase 1: Architectural Foundation
- **Prompt Analysis**: Explored whether to use an in-memory embedded SQLite database or pure in-memory data structures with Python's `threading` synchronization.
- **Decision**: In-memory data structures protected by per-SKU `threading.RLock()` and a Min-Heap priority queue for TTL management. This provides sub-millisecond latency (thousands of operations per second) without external daemon dependencies.
- **Artifact Generated**: Submitted an architectural design plan artifact (`design_plan.md`) covering domain models, locking strategies, and testing plans, which was reviewed and approved by the user.

### Phase 2: Lock Granularity & Performance Optimization
- **Deliberation**: How should we handle lock acquisition when a user reserves an item?
  - *Option A*: Single global lock for the entire engine.
    - *Drawback*: Contention on one hot SKU (e.g., iPhone) slows down reservations for unrelated SKUs (e.g., Headphones).
  - *Option B*: Fine-grained per-SKU `RLock` with a lightweight global lock for index modification.
    - *Decision*: Adopted Option B. Per-SKU locks isolate hot items and maximize multi-threaded concurrency.

### Phase 3: TTL Sweeper Architecture
- **Deliberation**: How to reliably expire reservations after 120s?
  - *Naive approach*: Sleep thread per reservation or $O(N)$ full table scan every tick.
    - *Drawback*: Spawning a thread per reservation is wasteful and unstable under high load. Scanning all reservations every second is $O(N)$ and wastes CPU.
  - *Engineered approach*:
    - **Min-Heap ($O(\log N)$)**: Reservations are scheduled in a priority queue keyed by `expires_at`. The background sweeper only inspects the heap root (`heap[0] <= now`).
    - **Dual / Lazy Evaluation**: Even if the background thread has not ticked yet, any query or confirmation attempt evaluates `now >= reservation.expires_at` lazily and triggers expiration instantly.

### Phase 4: Quota Accounting (M4)
- **Deliberation**: When does an order count toward a user's limit?
  - *Decision*: A user's total committed stock equals $\text{active\_reserved} + \text{confirmed\_purchased}$.
  - When a user reserves, quota is temporarily locked.
  - If the reservation is confirmed, it shifts into `confirmed_purchased`.
  - If cancelled or expired, it is immediately released, allowing the user to reserve again.

### Phase 5: Edge Cases Brainstormed & Implemented
1. **User Impersonation / Cross-User Interference**: Can User A confirm or cancel User B's reservation? Added explicit `user_id` ownership checks; unauthorized attempts raise `ReservationNotFoundError`.
2. **Double Operations**: Prevent double-confirming or double-cancelling a reservation using strict state machine transitions (`PENDING -> CONFIRMED`, `PENDING -> CANCELLED`, `PENDING -> EXPIRED`).
3. **Invalid Inputs**: Validated non-empty string user IDs and SKUs, strictly positive integer quantities, and valid positive TTL values.
4. **Deterministic Testing**: Introduced pluggable `time_func` allowing unit tests to simulate TTL expiry instantly without wall-clock sleeps.

### Phase 6: Stretch Features
1. **FIFO Waitlist with Auto-Promotion**: Implemented `WaitlistManager` where out-of-stock items can be queued, and freed stock automatically promotes the first eligible waitlisted user.
2. **Audit Ledger**: Implemented `AuditLedger` logging every state change for compliance and post-mortem analysis.
3. **Live Simulation CLI**: Created `run_demo.py` and `flash_sale/cli.py` to run multi-threaded flash sale simulations.

---

## 3. Verification & Test Matrix

| Test Suite | File | Tests / Assertions | Purpose |
| :--- | :--- | :---: | :--- |
| **Engine Tests** | `tests/test_engine.py` | 20 passed | Verifies requirements M1, M2, M3, M4, M5. |
| **Concurrency Stress** | `tests/test_concurrency.py` | 3 passed | 100 simultaneous threads, mixed operations, multi-SKU isolation, zero overselling proof. |
| **Edge Cases & Robustness** | `tests/test_edge_cases.py` | 13 passed (21 subtests) | Input sanitization, authorization checks, invalid states, sweeper lifecycle. |
| **Waitlist Feature** | `tests/test_waitlist.py` | 2 passed | FIFO queue ordering and auto-promotion upon cancellation. |
| **Total** | **All suites** | **38 passed (59 cases)** | **100% pass rate in 0.21s**. |

---

## 4. Key Learnings & Future Extensions

- **Distributed Environments**: For a distributed multi-node architecture (e.g. multiple Kubernetes pods), the in-memory per-SKU `RLock` can be substituted with Redis distributed locks (`Redlock`) or Lua scripts (`EVAL`) executing atomic `DECR` and TTL key setting.
- **Event-Driven Messaging**: Expired reservations can publish Kafka/RabbitMQ events to trigger user notifications and dynamic cart abandonment workflows.
