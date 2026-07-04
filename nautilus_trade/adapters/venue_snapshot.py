"""Venue snapshot provider factory for reconciliation."""

from __future__ import annotations

from nautilus_trade.adapters.binance_snapshot import (
    BinanceVenueSnapshotProvider,
    VenueSnapshotProvider,
)


def create_venue_snapshot_provider(venue: str) -> VenueSnapshotProvider:
    """Return a venue snapshot provider for application-layer reconciliation.

    Only BINANCE is supported today; other venues raise ValueError.
    """
    normalized = venue.upper()
    if normalized == "BINANCE":
        return BinanceVenueSnapshotProvider()
    raise ValueError(
        f"No snapshot provider for venue {venue!r}; only BINANCE is supported"
    )
