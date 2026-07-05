"""Regime filter tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.actors.regime_filter import RegimeFilterActor, RegimeFilterConfig


class TestRegimeFilterActor:
    def test_publishes_initial_signal(self) -> None:
        actor = RegimeFilterActor(
            RegimeFilterConfig(bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL")
        )
        actor.atr.initialized = True
        actor.atr.value = 100.0
        actor.publish_data = MagicMock()
        bar = MagicMock(close=20000.0, ts_event=1, ts_init=1)
        actor.on_bar(bar)
        assert actor.publish_data.call_count == 1
        assert actor._initial_signal_published is True
