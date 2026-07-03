"""Strategy unit tests.

Strategy execution tests run via NautilusTrader's BacktestEngine for
deterministic reproducibility. Here we only exercise config validation
and lightweight logic that does not require the engine.
"""

from __future__ import annotations

import pytest

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

    def test_max_position_notional_defaults_from_risk_cfg(self) -> None:
        cfg = EmaCrossConfig(
            instrument_id="BTCUSDT-PERP.BINANCE",
            bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
        )
        assert cfg.max_position_notional_usd > 0

    @pytest.mark.parametrize(
        ("fast", "slow"),
        [(5, 20), (10, 30), (12, 26)],
    )
    def test_fast_less_than_slow(self, fast: int, slow: int) -> None:
        """EMA-cross semantics require fast_period < slow_period."""
        cfg = EmaCrossConfig(
            instrument_id="BTCUSDT-PERP.BINANCE",
            bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
            fast_period=fast,
            slow_period=slow,
        )
        assert cfg.fast_period < cfg.slow_period
