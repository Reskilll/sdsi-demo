"""Lightweight min-heap TTL scheduler with O(log N) operations and background sweeping."""

import heapq
import threading
import time
from typing import Callable, List, Tuple, Optional


class TTLSweeper:
    """O(log N) min-heap expiration scheduler with minimal memory footprint."""

    __slots__ = ("_callback", "_interval", "_time_func", "_heap", "_lock", "_stop_event", "_thread")

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
        """O(log N) push into priority queue."""
        with self._lock:
            heapq.heappush(self._heap, (expires_at, reservation_id, sku))

    def sweep_expired(self, current_time: Optional[float] = None) -> List[Tuple[str, str]]:
        """Pops and invokes callback for all expired items in O(M log N) where M is expired count."""
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
                pass

        return expired_items

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="TTLSweeperThread", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.sweep_expired()
            self._stop_event.wait(timeout=self._interval)
