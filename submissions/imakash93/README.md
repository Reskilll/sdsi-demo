# PS4 — Inventory Reservation System (Flash Sale)

Prevent overselling during a flash sale with time-limited reservations,
per-user purchase limits, and human-in-the-loop escalation for system errors.

## Requirements

- **Python 3.9+** (standard library only — no ``pip install`` needed)
- The runtime has **no external API calls, no LLM keys, no database, and no
  internet access** — everything runs in process.

## One run command

```bash
python submissions/imakash93/agent.py '{"action":"load","file":"submissions/imakash93/inventory.json"}'
python submissions/imakash93/agent.py '{"action":"reserve","user":"alice","sku":"KB-MECH","qty":1}'
python submissions/imakash93/agent.py '{"action":"report"}'
```

Running the submission as ``python agent.py '<json>'`` uses the ``if __name__ ==
"__main__"`` block.  ``python -c "from agent import run; ..."`` is also
supported.

## Actions

Every request is a JSON object with an ``"action"`` field.

| Action    | Required keys                                   | Optional       |
|-----------|-------------------------------------------------|----------------|
| ``load``  | ``"file"`` (path to ``.json``)                  | —              |
| ``reserve`` | ``"user"``, ``"sku"``, ``"qty"``               | ``"ttl"`` (default 120) |
| ``confirm`` | ``"reservation_id"`` *or* ``"user"`` + ``"sku"`` | —           |
| ``cancel``  | ``"reservation_id"`` *or* ``"user"`` + ``"sku"`` | —           |
| ``report``  | ``"sku"`` (omit for all SKUs)                   | —              |

## Quick example (Python API)

```python
import json
from agent import run

run(json.dumps({"action": "load",  "file": "inventory.json"}))
run(json.dumps({"action": "reserve", "user": "alice", "sku": "MOUSE-PRO", "qty": 2}))
# => {"reservation_id": "abc123...", ...}
run(json.dumps({"action": "confirm", "reservation_id": "abc123..."}))
run(json.dumps({"action": "report"}))
```

## Running tests

```bash
python -m unittest submissions/imakash93/test_engine.py -v
python -m unittest submissions/imakash93/test_agent.py -v
```

## Design choices

| Choice | Rationale |
|--------|-----------|
| **``available`` is computed, never stored** | ``stock - reserved - sold`` computed under the lock — can never drift stale. This *is* the oversell-prevention invariant. |
| **Per-user limits enforced at reserve time** | Limits count *confirmed + reserved* so a confirm can never violate the cap; confirm is a pure status transition. |
| **All-or-nothing confirm** | A reservation's full quantity is confirmed/cancelled at once. No partial confirms. |
| **Lazy per-SKU expiry** | Expired reservations are released on the next operation that touches that SKU, not a global sweep — keeps the non-expired path O(1). |
| **Injectable clock** | The engine accepts a ``clock`` callable so tests fast-forward TTL expiry without sleeping. |
| **Error taxonomy** | ``SystemError`` (file I/O, corrupt inventory) → escalates. ``BusinessError`` (out-of-stock, limit) → rejected, no escalation. |
| **No third-party deps** | 100 % stdlib — ``json`` for parsing, ``threading`` for the lock, ``uuid`` for reservation ids, ``dataclasses`` for models. |
| **``unittest`` for tests** | Zero-dependency test runner — tests "look runnable" without ``pip install``. |

## Assumptions

- ``task`` is a JSON string (not a file path).
- ``load`` accepts a relative file path resolved against the current working
  directory.  ``..`` traversal is rejected.
- SKUs are **case-sensitive** and matched exactly.
- ``report`` with an unknown SKU returns a rejection, not zeros (zeros would
  falsely imply the SKU exists).
- A ``"limit_per_user"`` value of ``null`` or absent means no per-user cap.
- TTL of 0 creates a reservation that expires immediately — useful for
  atomic "try-and-confirm" patterns in tests, and semantically correct.

## Known gaps

- No persistent storage — state resets on process restart.
- No real concurrency harness (all single-threaded in tests); but the ``RLock``
  guards are present and the invariants (available computed, per-user committed)
  are documented for a multi-threaded reader.
- Path traversal guard only rejects ``..`` — does not chroot or sandbox file
  access.
- SKU list in ``items`` is unsorted when reporting a single SKU (order matches
  input).
- No distributed / multi-instance coordination.