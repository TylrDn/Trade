"""Live TradingNode composition smoke tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("prometheus_client")
pytest.importorskip("nautilus_trader")

from nautilus_trade.live.node import build_live_trading_node
from nautilus_trade.live.runtime import (
    create_live_runtime,
    get_live_runtime,
    unbind_live_runtime,
)


@pytest.mark.integration
class TestBuildLiveTradingNode:
    def test_composes_runtime_actors_and_strategy(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        build_calls: list[bool] = []

        class MockTradingNode:
            def __init__(self, config: object) -> None:
                self.config = config

            def add_data_client_factory(self, _venue: str, _factory: object) -> None:
                return None

            def add_exec_client_factory(self, _venue: str, _factory: object) -> None:
                return None

            def build(self) -> None:
                build_calls.append(True)

        monkeypatch.setattr("nautilus_trade.live.node.TradingNode", MockTradingNode)

        runtime = create_live_runtime("node-smoke")
        try:
            node = build_live_trading_node(
                runtime=runtime,
                venue="BINANCE",
                strategy_specs=[
                    {
                        "config": {
                            "instrument_id": "BTCUSDT-PERP.BINANCE",
                            "bar_type": "BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                        },
                    },
                ],
                data_factory=object(),
                exec_factory=object(),
                data_client_config=SimpleNamespace(),
                exec_client_config=SimpleNamespace(),
            )

            assert build_calls == [True]
            assert len(node.config.actors) == 4
            assert len(node.config.strategies) == 1
            assert (
                node.config.strategies[0].strategy_path
                == "nautilus_trade.live.factories:create_ema_cross_strategy"
            )
            assert get_live_runtime() is runtime
        finally:
            unbind_live_runtime()
            runtime.close()
