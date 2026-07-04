"""Live wiring integration-style tests."""

from __future__ import annotations

import pytest

pytest.importorskip("prometheus_client")
pytest.importorskip("nautilus_trader")

from nautilus_trade.live.factories import create_ema_cross_strategy
from nautilus_trade.live.runtime import bound_live_runtime, create_live_runtime
from nautilus_trade.strategies.ema_cross import EmaCrossConfig


@pytest.mark.integration
class TestLiveWiring:
    def test_factory_injects_shared_gateway(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("wire-run")
        try:
            with bound_live_runtime(runtime):
                strategy = create_ema_cross_strategy(
                    EmaCrossConfig(
                        instrument_id="BTCUSDT-PERP.BINANCE",
                        bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                    ),
                )
            assert strategy.gateway is runtime.gateway
            assert strategy.gateway.breaker is runtime.breaker
        finally:
            runtime.close()
