"""Live feed health monitoring.

Tracks last-seen timestamps for active data subscriptions and fires
alerts when feeds go stale, preventing the system from trading on
stale market data.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from nautilus_trade.config import risk_cfg
from nautilus_trade.ops.alerts import send_alert
from nautilus_trade.ops.circuit_breaker import CircuitBreaker

log = logging.getLogger(__name__)


class FeedHealthMonitor:
    """Tracks last-seen timestamps per instrument and trips circuit on staleness."""

    def __init__(self, breaker: CircuitBreaker | None = None) -> None:
        self.breaker = breaker or CircuitBreaker()
        self._last_seen: dict[str, float] = defaultdict(float)

    def record_quote(self, instrument_id: str) -> None:
        """Call this on every tick/quote received for an instrument."""
        self._last_seen[instrument_id] = time.monotonic()

    def check_all(self) -> list[str]:
        """Return list of stale instrument IDs. Call on a regular schedule."""
        now = time.monotonic()
        stale = [
            iid
            for iid, last in self._last_seen.items()
            if (now - last) > risk_cfg.stale_feed_seconds
        ]
        if stale:
            msg = f"Stale feeds detected: {stale}"
            log.warning(msg)
            send_alert(f"⚠️ {msg}", level="warning")
            self.breaker.trip(f"Stale feed: {stale}")
        return stale

    def is_healthy(self, instrument_id: str) -> bool:
        """Return True if the feed has been seen recently."""
        last = self._last_seen.get(instrument_id, 0.0)
        return (time.monotonic() - last) <= risk_cfg.stale_feed_seconds
