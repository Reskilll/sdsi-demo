"""
Background TTL sweeper — runs in a daemon thread.

Design decisions:
- Uses time.monotonic() everywhere for TTL comparisons — immune to clock drift.
- Sweeps in a loop with configurable interval; on shutdown it receives a
  threading.Event signal and exits cleanly.
- Each sweep acquires per-SKU locks briefly and releases them, so the main
  reservation path is never starved waiting for expiry.
- Sweeper is started AFTER all products are loaded.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import StateStore

# ────────────────────────────────────────────────────────────────────


class Sweeper:
    """Background daemon that periodically scans for expired reservations."""

    def __init__(
        self,
        store: StateStore,
        interval_seconds: float = 1.0,
    ) -> None:
        self._store = store
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Launch the sweeper thread as a daemon."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="ttl-sweeper",
            daemon=True,
        )
        self._thread.start()
        print(f"[sweeper] Started (interval={self._interval}s)")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the sweeper to stop and wait for it."""
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                print("[sweeper] Warning: did not stop within timeout")
            else:
                print("[sweeper] Stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── loop ──────────────────────────────────────────────────────

    def _run(self) -> None:
        """Main loop — sweep, then sleep for the remainder of the interval."""
        while not self._stop_event.is_set():
            cycle_start = time.monotonic()
            try:
                released = self._store.expire_stale()
                idem_removed = self._store.cleanup_stale_idempotency()
                if released > 0 or idem_removed > 0:
                    parts = []
                    if released > 0:
                        parts.append(f"{released} reservations")
                    if idem_removed > 0:
                        parts.append(f"{idem_removed} idempotency records")
                    print(f"[sweeper] Released {' & '.join(parts)}")
            except Exception:
                # Never let a sweeper crash bring down the process.
                # Re-raise is intentional during test to catch bugs.
                import traceback

                traceback.print_exc()

            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0.0, self._interval - elapsed)
            # Use small-slice sleep so stop_event is responsive
            while sleep_time > 0 and not self._stop_event.is_set():
                nap = min(0.1, sleep_time)
                self._stop_event.wait(nap)
                sleep_time -= nap