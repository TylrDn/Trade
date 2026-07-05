"""Soak status tests."""

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from soak_status import compute_streak


class TestSoakStatus:
    def test_clean_streak_from_fixture(self, tmp_path: Path) -> None:
        events = tmp_path / "events.jsonl"
        events.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "ts": "2026-01-01T12:00:00+00:00",
                            "event_type": "reconciliation_ok",
                        }
                    ),
                    json.dumps(
                        {
                            "ts": "2026-01-02T12:00:00+00:00",
                            "event_type": "reconciliation_ok",
                        }
                    ),
                ]
            )
        )
        streak, last_failure = compute_streak(events)
        assert streak == 2
        assert last_failure is None
