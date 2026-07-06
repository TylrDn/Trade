"""Venue snapshot provider factory for reconciliation."""

from __future__ import annotations

from nautilus_trade.adapters.binance_snapshot import BinanceVenueSnapshotProvider
from nautilus_trade.adapters.kraken_snapshot import KrakenVenueSnapshotProvider
from nautilus_trade.adapters.snapshot_types import VenueSnapshotProvider


def create_venue_snapshot_provider(venue: str) -> VenueSnapshotProvider:
    """Return a venue snapshot provider for application-layer reconciliation."""
    normalized = venue.upper()
    if normalized == "BINANCE":
        return BinanceVenueSnapshotProvider()
    if normalized == "KRAKEN":
        return KrakenVenueSnapshotProvider()
    raise ValueError(
        f"No snapshot provider for venue {venue!r}; supported: BINANCE, KRAKEN"
    )
