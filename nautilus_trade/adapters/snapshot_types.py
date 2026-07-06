"""Venue-neutral snapshot types for application-layer reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Protocol

SnapshotStatus = Literal["ok", "missing_credentials", "fetch_error"]


@dataclass(frozen=True)
class VenueSnapshot:
    """Venue balances and positions with explicit fetch status."""

    balances: dict[str, Decimal]
    positions: dict[str, Decimal]
    status: SnapshotStatus
    error: str | None = None
    raw_positions: dict[str, Decimal] = field(default_factory=dict)
    balance_details: dict[str, dict[str, str]] = field(default_factory=dict)
    open_order_client_ids: frozenset[str] = field(default_factory=frozenset)


class VenueSnapshotProvider(Protocol):
    """Fetch venue balances and positions for reconciliation."""

    def fetch(self) -> VenueSnapshot:
        """Return venue snapshot with explicit status."""
        ...
