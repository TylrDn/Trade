"""Trading circuit breaker.

A simple, dependency-free circuit breaker that can be tripped by:
- Daily loss limit breach (risk engine)
- Stale feed detection (feed health monitor)
- Manual operator action
- Any unrecoverable system error

When tripped, the ExecutionGateway blocks all order submission.
Reset requires explicit operator action.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from nautilus_trade.ops.metrics import CIRCUIT_TRIPS

log = logging.getLogger(__name__)


class CircuitBreaker:
    """System-wide trading halt gate."""

    def __init__(self) -> None:
        self._tripped = False
        self._reason: str = ""
        self._tripped_at: datetime | None = None

    @property
    def is_tripped(self) -> bool:
        return self._tripped

    def trip(self, reason: str) -> None:
        """Trip the circuit. Idempotent — multiple trips log but don't double-count."""
        if not self._tripped:
            self._tripped = True
            self._reason = reason
            self._tripped_at = datetime.now(timezone.utc)
            log.critical("CIRCUIT BREAKER TRIPPED: %s", reason)
            CIRCUIT_TRIPS.labels(reason=reason[:32]).inc()
        else:
            log.warning("Circuit already tripped (new reason: %s)", reason)

    def reset(self) -> None:
        """Reset the circuit. Must be called explicitly by an operator."""
        if self._tripped:
            log.warning(
                "Circuit breaker RESET (was tripped at %s for: %s)",
                self._tripped_at,
                self._reason,
            )
        self._tripped = False
        self._reason = ""
        self._tripped_at = None

    def status(self) -> dict:
        return {
            "tripped": self._tripped,
            "reason": self._reason,
            "tripped_at": self._tripped_at.isoformat() if self._tripped_at else None,
        }
