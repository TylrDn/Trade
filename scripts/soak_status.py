#!/usr/bin/env python3
"""Report cumulative clean-day soak streak from EventStore JSONL."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from nautilus_trade.ops.eventstore_utils import load_events

FAILURE_EVENTS = frozenset(
    {
        "reconciliation_failed",
        "reconciliation_open_orders_mismatch",
        "reconciliation_missing_credentials",
    }
)


def compute_streak(events_path: Path) -> tuple[int, str | None]:
    events = load_events(events_path)
    days_with_failure: set[str] = set()
    for event in events:
        event_type = str(event.get("event_type", ""))
        if event_type in FAILURE_EVENTS:
            ts = str(event.get("ts", ""))
            day = ts[:10] if ts else "unknown"
            days_with_failure.add(day)

    days_seen: set[str] = set()
    for event in events:
        ts = str(event.get("ts", ""))
        if ts:
            days_seen.add(ts[:10])

    if not days_seen:
        return 0, None

    sorted_days = sorted(days_seen)
    streak = 0
    last_failure: str | None = max(days_with_failure) if days_with_failure else None

    for day in reversed(sorted_days):
        if day in days_with_failure:
            break
        streak += 1

    return streak, last_failure


def main() -> None:
    parser = argparse.ArgumentParser(description="Soak streak from EventStore")
    parser.add_argument(
        "--events",
        required=True,
        help="Path to events_<run_id>.jsonl",
    )
    args = parser.parse_args()

    streak, last_failure = compute_streak(Path(args.events))
    print(f"clean_day_streak={streak}")
    print(f"last_failure_day={last_failure or 'none'}")
    print(f"checked_at={datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()
