"""Binance instrument mapping tests."""

from __future__ import annotations

from nautilus_trade.adapters.binance_instruments import binance_symbol_to_instrument_id


def test_binance_symbol_to_instrument_id() -> None:
    assert binance_symbol_to_instrument_id("BTCUSDT") == "BTCUSDT-PERP.BINANCE"
