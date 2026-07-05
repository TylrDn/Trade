#!/usr/bin/env python3
"""Testnet smoke validation script."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nautilus_trade.ops.eventstore_utils import event_types, load_events

REQUIRED_EVENTS = {
    "reconciliation_startup_timing",
}


def validate_events(events_path: Path) -> list[str]:
    errors: list[str] = []
    events = load_events(events_path)
    if not events:
        errors.append(f"No events in {events_path}")
        return errors
    types = set(event_types(events))
    missing = REQUIRED_EVENTS - types
    if missing:
        errors.append(f"Missing required events: {sorted(missing)}")
    if "reconciliation_ok" not in types and "reconciliation_failed" not in types:
        errors.append("Expected reconciliation_ok or reconciliation_failed")
    return errors


def dry_run(fixtures_dir: Path) -> int:
    events_file = fixtures_dir / "events_smoke.jsonl"
    errors = validate_events(events_file)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        return 1
    print("PASS: dry-run smoke assertions satisfied")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Testnet smoke validation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate fixture EventStore JSONL (no credentials)",
    )
    parser.add_argument(
        "--fixtures",
        default="tests/fixtures/smoke",
        help="Fixture directory for dry-run",
    )
    parser.add_argument(
        "--events",
        help="EventStore JSONL path for live validation",
    )
    args = parser.parse_args()

    if args.dry_run:
        return dry_run(Path(args.fixtures))

    if args.events:
        errors = validate_events(Path(args.events))
        if errors:
            for err in errors:
                print(f"FAIL: {err}")
            return 1
        print("PASS: live event validation satisfied")
        return 0

    print("Live smoke requires --events or use --dry-run for CI")
    return 2


if __name__ == "__main__":
    sys.exit(main())
