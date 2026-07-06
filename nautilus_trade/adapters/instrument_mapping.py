"""Venue-dispatch instrument mapping for reconciliation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from nautilus_trade.adapters.binance_instruments import map_binance_positions
from nautilus_trade.adapters.kraken_instruments import map_kraken_positions


def mapping_warnings_for_positions(
    mapped_positions: dict[str, Any],
    cache: Any | None,
) -> list[str]:
    """Return warnings when mapped instrument IDs are not loaded in cache."""
    if cache is None or not mapped_positions:
        return []

    instruments_fn = getattr(cache, "instruments", None)
    if not callable(instruments_fn):
        return []

    known = {str(getattr(instrument, "id", "")) for instrument in instruments_fn()}
    warnings: list[str] = []
    for instrument_id in mapped_positions:
        if instrument_id not in known:
            warnings.append(f"{instrument_id} not loaded in cache")
    return warnings


def map_venue_positions(
    venue: str,
    raw_positions: dict[str, Any],
    cache: Any | None = None,
) -> dict[str, Decimal]:
    """Map venue-native position keys to Nautilus instrument_id strings."""
    normalized = venue.upper()
    if normalized == "BINANCE":
        return map_binance_positions(raw_positions, cache)
    if normalized == "KRAKEN":
        return map_kraken_positions(raw_positions, cache)
    raise ValueError(f"No position mapper for venue {venue!r}")
