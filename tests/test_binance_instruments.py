"""Binance instrument mapping tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from nautilus_trade.adapters.binance_instruments import (
    binance_symbol_to_instrument_id,
    map_binance_positions,
    mapping_warnings_for_positions,
)


def test_binance_symbol_to_instrument_id() -> None:
    assert binance_symbol_to_instrument_id("BTCUSDT") == "BTCUSDT-PERP.BINANCE"


def test_map_binance_positions_uses_cache_instrument_id() -> None:
    instrument = SimpleNamespace(
        id="BTCUSDT-LINEAR.BINANCE",
        symbol="BTCUSDT",
        raw_symbol="BTCUSDT",
    )
    cache = SimpleNamespace(instruments=lambda: [instrument])
    mapped = map_binance_positions({"BTCUSDT": Decimal("0.1")}, cache=cache)
    assert mapped == {"BTCUSDT-LINEAR.BINANCE": Decimal("0.1")}


def test_mapping_warnings_when_instrument_not_in_cache() -> None:
    mapped = {"BTCUSDT-PERP.BINANCE": Decimal("0.1")}
    cache = SimpleNamespace(instruments=lambda: [])
    warnings = mapping_warnings_for_positions(mapped, cache)
    assert warnings == ["BTCUSDT-PERP.BINANCE not loaded in cache"]

