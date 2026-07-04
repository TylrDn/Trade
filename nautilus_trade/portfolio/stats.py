"""Portfolio statistics helpers for gateway pre-checks and metrics."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from nautilus_trader.model.enums import PriceType

log = logging.getLogger(__name__)


def portfolio_notional_usd(cache: Any, portfolio: Any) -> float:
    """Sum open position notional in USD using MID prices."""
    total = Decimal(0)
    skipped = 0
    for position in cache.positions_open():
        if not position.is_open:
            continue
        price = cache.price(position.instrument_id, PriceType.MID)
        if price is None:
            skipped += 1
            log.error(
                "portfolio_notional: no MID price for %s; position excluded from total",
                position.instrument_id,
            )
            continue
        total += Decimal(str(abs(position.quantity))) * Decimal(str(price))
    if skipped:
        log.error(
            "portfolio_notional: excluded %d open position(s) due to missing prices",
            skipped,
        )
    return float(total)


def portfolio_notional_usd_strict(cache: Any, portfolio: Any) -> float | None:
    """Sum open position notional, or None if any open position lacks MID price."""
    total = Decimal(0)
    for position in cache.positions_open():
        if not position.is_open:
            continue
        price = cache.price(position.instrument_id, PriceType.MID)
        if price is None:
            log.error(
                "portfolio_notional_strict: no MID price for %s; notional unknown",
                position.instrument_id,
            )
            return None
        total += Decimal(str(abs(position.quantity))) * Decimal(str(price))
    return float(total)


def portfolio_equity_usd(portfolio: Any) -> float:
    """Return total account equity in USD when available."""
    equity = Decimal(0)
    for account in portfolio.accounts():
        for balance in account.balances().values():
            total = getattr(balance, "total", None)
            if total is not None:
                equity += Decimal(str(total))
    return float(equity)


def portfolio_leverage(cache: Any, portfolio: Any) -> float:
    """Compute portfolio leverage as notional / equity."""
    notional = portfolio_notional_usd(cache, portfolio)
    equity = portfolio_equity_usd(portfolio)
    if equity <= 0:
        if notional > 0:
            log.error(
                "portfolio_leverage: equity <= 0 with open notional %.2f; treating as over limit",
                notional,
            )
            return float("inf")
        return 1.0
    return notional / equity


def total_open_order_count(cache: Any) -> int:
    """Count all open orders across instruments."""
    return len(cache.orders_open())


def refresh_portfolio_notional_metrics(cache: Any, portfolio: Any) -> None:
    """Update strict notional gauges for observability.

    When strict notional is unknown, marks incomplete=1 and leaves the notional
    gauge unchanged to avoid understating exposure.
    """
    from nautilus_trade.ops.metrics import PORTFOLIO_NOTIONAL_INCOMPLETE, PORTFOLIO_NOTIONAL_USD

    notional = portfolio_notional_usd_strict(cache, portfolio)
    if notional is None:
        PORTFOLIO_NOTIONAL_INCOMPLETE.set(1)
        return

    PORTFOLIO_NOTIONAL_INCOMPLETE.set(0)
    PORTFOLIO_NOTIONAL_USD.set(notional)
