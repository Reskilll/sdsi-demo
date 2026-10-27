"""Background TTL sweeper utilizing a min-heap for O(log N) expiration scheduling."""

import heapq
import threading
import time
from typing import Callable, List, Tuple, Optional


class TTLSweeper:
    """
    Min-heap priority queue TTL expiration scheduler with an optional
    background sweeper daemon thread.
    """

    def __init__(
        self,
        expire_callback: Callable[[str, str], None],
        sweep_interval: float = 0.5,
        time_func: Optional[Callable[[], float]] = None,
    ):
        self._callback = expire_callback
        self._interval = sweep_interval
        self._time_func = time_func or time.time
        self._heap: List[Tuple[float, str, str]] = []  # (expires_at, reservation_id, sku)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def schedule(self, reservation_id: str, sku: str, expires_at: float) -> None:
        """Schedules a reservation for expiration."""
        with self._lock:
            heapq.heappush(self._heap, (expires_at, reservation_id, sku))

    def sweep_expired(self, current_time: Optional[float] = None) -> List[Tuple[str, str]]:
        """
        Pops and triggers expiration for all reservations whose expires_at <= now.
        Returns list of (reservation_id, sku) expired.
        """
        now = self._time_func() if current_time is None else current_time
        expired_items: List[Tuple[str, str]] = []

        with self._lock:
            while self._heap and self._heap[0][0] <= now:
                _, res_id, sku = heapq.heappop(self._heap)
                expired_items.append((res_id, sku))

        for res_id, sku in expired_items:
            try:
                self._callback(res_id, sku)
            except Exception:
                # Log or swallow in sweeper callback so thread doesn't crash
                pass

        return expired_items

    def start(self) -> None:
        """Starts background sweeper daemon thread."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="TTLSweeperThread",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Stops background sweeper daemon thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        """Returns True if background daemon thread is active."""
        return bool(self._thread and self._thread.is_alive())

    def _run_loop(self) -> None:
        """Periodic background sweep loop."""
        while not self._stop_event.is_set():
            self.sweep_expired()
            self._stop_event.wait(timeout=self._interval)
