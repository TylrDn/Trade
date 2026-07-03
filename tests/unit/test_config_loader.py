"""YAML config loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nautilus_trade.config_loader import load_strategy_config, load_venue_config


class TestLoadStrategyConfig:
    def test_loads_bundled_ema_cross(self) -> None:
        cfg = load_strategy_config("ema_cross")
        assert cfg["name"] == "ema_cross"
        assert cfg["strategy_path"].endswith(":EmaCrossStrategy")
        assert cfg["config"]["fast_period"] == 10

    def test_missing_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_strategy_config("no_such_strategy_xyz")

    def test_explicit_path(self, tmp_path: Path) -> None:
        p = tmp_path / "custom.yaml"
        p.write_text(
            "name: custom\n"
            "strategy_path: pkg.mod:Class\n"
            "venue: BINANCE\n"
            "instrument_id: X\n"
            "bar_type: Y\n"
            "start: '2024-01-01'\n"
            "end: '2024-02-01'\n"
            "config: {a: 1}\n"
        )
        cfg = load_strategy_config("ignored", explicit_path=p)
        assert cfg["name"] == "custom"
        assert cfg["config"] == {"a": 1}


class TestLoadVenueConfig:
    def test_loads_binance(self) -> None:
        cfg = load_venue_config("binance")
        assert cfg["name"] == "BINANCE"
        assert cfg["testnet"] is True
