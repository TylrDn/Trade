"""Shared EventStore JSONL parsing for operational scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def event_types(events: list[dict[str, Any]]) -> list[str]:
    return [str(e.get("event_type", "")) for e in events]
