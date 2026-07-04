"""Realized PnL extraction from NautilusTrader position state.

OrderFilled events do not carry realized PnL. The engine updates position
realized_pnl on each fill; we track deltas for daily loss accounting.

Scope: USDT-settled instruments (e.g. Binance USDT-M perps). Multi-currency
conversion is not performed here.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

log = logging.getLogger(__name__)


def _money_to_float(value: Any) -> float:
    if value is None:
        return 0.0
    as_double = getattr(value, "as_double", None)
    if callable(as_double):
        return float(as_double())
    return float(value)


def _position_key(position: Any) -> str:
    position_id = getattr(position, "id", None)
    if position_id is not None:
        return str(position_id)
    return str(getattr(position, "instrument_id", "unknown"))


def resolve_position_for_fill(cache: Any, event: Any) -> Any | None:
    """Resolve the position associated with a fill event."""
    position_id = getattr(event, "position_id", None)
    if position_id is not None:
        position = cache.position(position_id)
        if position is not None:
            return position

    instrument_id = getattr(event, "instrument_id", None)
    if instrument_id is not None:
        return cache.position_for_instrument(instrument_id)

    return None


def realized_pnl_delta_usd(
    cache: Any,
    event: Any,
    last_seen: dict[str, Decimal],
) -> tuple[float | None, str]:
    """Return (delta_usd, source) for a fill event.

    source is ``position_delta`` when computed from position.realized_pnl change,
    or ``unavailable`` when position state cannot be read. When unavailable, delta
    is None — not zero — so live/staging callers can fail closed.
    """
    position = resolve_position_for_fill(cache, event)
    if position is None:
        log.warning(
            "realized_pnl_delta: no position for fill instrument=%s",
            getattr(event, "instrument_id", "?"),
        )
        return None, "unavailable"

    realized = getattr(position, "realized_pnl", None)
    if realized is None:
        log.warning(
            "realized_pnl_delta: position %s has no realized_pnl",
            _position_key(position),
        )
        return None, "unavailable"

    current = Decimal(str(_money_to_float(realized)))
    key = _position_key(position)
    previous = last_seen.get(key, Decimal(0))
    delta = current - previous
    last_seen[key] = current
    return float(delta), "position_delta"
