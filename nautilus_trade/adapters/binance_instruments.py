"""Binance symbol to Nautilus InstrumentId mapping for reconciliation."""

from __future__ import annotations

from typing import Any


def binance_symbol_to_instrument_id(symbol: str) -> str:
    """Map a Binance USDT-M futures symbol to Nautilus InstrumentId string.

    Example: BTCUSDT -> BTCUSDT-PERP.BINANCE
    """
    return f"{symbol}-PERP.BINANCE"


def map_binance_positions(
    raw_positions: dict[str, Any],
    cache: Any | None = None,
) -> dict[str, Any]:
    """Map Binance symbol keys to Nautilus instrument_id strings.

    When *cache* is provided, attempts to match instruments by symbol first.
    """
    from decimal import Decimal

    mapped: dict[str, Decimal] = {}
    for symbol, qty in raw_positions.items():
        amt = Decimal(str(qty))
        if amt == 0:
            continue
        instrument_id = _resolve_instrument_id(str(symbol), cache)
        mapped[instrument_id] = amt
    return mapped


def _resolve_instrument_id(symbol: str, cache: Any | None) -> str:
    if cache is not None:
        instruments_fn = getattr(cache, "instruments", None)
        if callable(instruments_fn):
            for instrument in instruments_fn():
                inst_symbol = str(getattr(instrument, "symbol", ""))
                raw_symbol = str(getattr(instrument, "raw_symbol", inst_symbol))
                if symbol in (inst_symbol, raw_symbol):
                    return str(instrument.id)
    return binance_symbol_to_instrument_id(symbol)
