"""Kraken symbol to Nautilus InstrumentId mapping for reconciliation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def kraken_symbol_to_instrument_id(symbol: str) -> str:
    """Map a Kraken Futures symbol to Nautilus InstrumentId string.

    Example: PF_XBTUSD -> PF_XBTUSD.KRAKEN
    """
    return f"{symbol}.KRAKEN"


def map_kraken_positions(
    raw_positions: dict[str, Any],
    cache: Any | None = None,
) -> dict[str, Decimal]:
    """Map Kraken symbol keys to Nautilus instrument_id strings."""
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
    return kraken_symbol_to_instrument_id(symbol)
