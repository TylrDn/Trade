"""Durable event store for audit and replay.

Captures every material trading event (orders, fills, risk trips,
circuit breaks, system halts) to a append-only JSONL file.

This provides:
- Post-incident debugging and root cause analysis
- Strategy performance audit trail
- Replay artifacts for deterministic analysis

For higher-volume systems, replace the JSONL writer with an async
database writer (Postgres, TimescaleDB, ClickHouse).
"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

EVENT_LOG_DIR = Path("./logs/events")


class EventStore:
    """Append-only JSONL event store for audit and replay."""

    def __init__(self, run_id: str = "default") -> None:
        EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._path = EVENT_LOG_DIR / f"events_{run_id}.jsonl"
        self._fh = self._path.open("a", encoding="utf-8")
        log.info("EventStore opened: %s", self._path)

    def record(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a structured event to the store."""
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            **payload,
        }
        try:
            self._fh.write(json.dumps(entry) + "\n")
            self._fh.flush()
        except Exception as exc:
            log.error("EventStore write failed: %s", exc)

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._fh.close()

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, *_) -> None:
        self.close()
