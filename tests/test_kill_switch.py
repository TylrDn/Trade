"""Kill switch facade tests."""

import pytest

pytest.importorskip("prometheus_client")

from nautilus_trade.live.runtime import create_live_runtime
from nautilus_trade.ops.kill_switch import KillSwitch


class TestKillSwitch:
    def test_records_kill_switch_event(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("kill-test")
        try:
            KillSwitch(runtime).trigger("manual halt", "operator-1", recommend_flatten=False)
            assert runtime.breaker.is_tripped
            contents = (tmp_path / "events_kill-test.jsonl").read_text()
            assert "kill_switch_triggered" in contents
        finally:
            runtime.close()
