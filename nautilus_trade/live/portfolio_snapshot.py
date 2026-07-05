"""Extract internal portfolio snapshots for reconciliation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def extract_internal_balances(portfolio: Any) -> dict[str, Decimal]:
    """Build currency -> balance map from the local portfolio."""
    balances: dict[str, Decimal] = {}
    for account in portfolio.accounts():
        for currency, balance in account.balances().items():
            key = str(currency).upper()
            total = getattr(balance, "total", balance)
            balances[key] = Decimal(str(total))
    return balances


def extract_internal_positions(cache: Any) -> dict[str, Decimal]:
    """Build instrument_id -> signed quantity map from open positions."""
    positions: dict[str, Decimal] = {}
    for position in cache.positions_open():
        if not position.is_open:
            continue
        positions[str(position.instrument_id)] = Decimal(str(position.quantity))
    return positions


def extract_internal_open_order_client_ids(cache: Any) -> frozenset[str]:
    """Return client order IDs for all open orders in cache."""
    ids: set[str] = set()
    for order in cache.orders_open():
        client_id = getattr(order, "client_order_id", None)
        if client_id is not None:
            ids.add(str(client_id))
    return frozenset(ids)
