"""Smoke testnet script tests."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from smoke_testnet import dry_run, validate_events


class TestSmokeTestnetDryRun:
    def test_dry_run_passes(self) -> None:
        fixtures = Path(__file__).parent / "fixtures" / "smoke"
        assert dry_run(fixtures) == 0

    def test_validate_fixture_events(self) -> None:
        events = Path(__file__).parent / "fixtures" / "smoke" / "events_smoke.jsonl"
        assert validate_events(events) == []
