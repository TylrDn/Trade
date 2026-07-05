"""Shared order submit timing for fill latency observability."""

from __future__ import annotations

import threading


class OrderTimingTracker:
    """Thread-safe client_order_id → submit timestamp store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._submit_ts_ns: dict[str, int] = {}

    def record(self, client_order_id: str, submit_ts_ns: int) -> None:
        with self._lock:
            self._submit_ts_ns[client_order_id] = submit_ts_ns

    def pop_latency_seconds(self, client_order_id: str, fill_ts_ns: int) -> float | None:
        with self._lock:
            submit_ts_ns = self._submit_ts_ns.pop(client_order_id, None)
        if submit_ts_ns is None:
            return None
        return (fill_ts_ns - submit_ts_ns) / 1e9

    def clear(self) -> None:
        with self._lock:
            self._submit_ts_ns.clear()
