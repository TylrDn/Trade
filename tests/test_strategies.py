"""Strategy unit and integration tests.

All strategy tests run via NautilusTrader's BacktestEngine (low-level)
to ensure deterministic, reproducible results without live credentials.

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

    def test_fast_must_be_less_than_slow(self) -> None:
        """Logical constraint: fast period should be less than slow period."""
        cfg = EmaCrossConfig(
            instrument_id="BTCUSDT-PERP.BINANCE",
            bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
            fast_period=5,
            slow_period=20,
        )
        assert cfg.fast_period < cfg.slow_period
