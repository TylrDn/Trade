"""Strategy configuration tests.

Covers EmaCrossConfig construction. BacktestEngine integration tests require
a populated catalog and full NautilusTrader runtime; run via scripts/run_backtest.py
or CI with pip install -e ".[dev]".

Requires nautilus_trader and prometheus_client for full execution;
skipped cleanly in minimal environments without those dependencies.
"""

from __future__ import annotations

import pytest

pytest.importorskip("nautilus_trader")
pytest.importorskip("prometheus_client")

from nautilus_trade.strategies.ema_cross import EmaCrossConfig


class TestEmaCrossConfig:
    def test_default_config(self) -> None:
        cfg = EmaCrossConfig(
            instrument_id="BTCUSDT-PERP.BINANCE",
            bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
        )
        assert cfg.fast_period == 10
        assert cfg.slow_period == 30
        assert cfg.trade_size == "0.01"

    def test_custom_periods(self) -> None:
        cfg = EmaCrossConfig(
            instrument_id="BTCUSDT-PERP.BINANCE",
            bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
            fast_period=5,
            slow_period=20,
        )
        assert cfg.fast_period == 5
        assert cfg.slow_period == 20

    def test_default_flatten_on_stop_is_false(self) -> None:
        cfg = EmaCrossConfig(
            instrument_id="BTCUSDT-PERP.BINANCE",
            bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
        )
        assert cfg.flatten_on_stop is False
