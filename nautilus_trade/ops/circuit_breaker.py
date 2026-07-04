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
from typing import TYPE_CHECKING

from nautilus_trade.config import system_cfg
from nautilus_trade.ops.metrics import CIRCUIT_TRIPS

if TYPE_CHECKING:
    from nautilus_trade.ops.event_store import EventStore

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

    def reset(
        self,
        operator: str = "system",
        *,
        event_store: EventStore | None = None,
    ) -> None:
        """Reset the circuit. Must be called explicitly by an operator."""
        if system_cfg.is_live and operator == "system":
            raise ValueError(
                "Circuit breaker reset in production requires an explicit human operator "
                "identifier, not 'system'."
            )

        prior_reason = self._reason
        if self._tripped:
            log.warning(
                "Circuit breaker RESET by %s (was tripped at %s for: %s)",
                operator,
                self._tripped_at,
                prior_reason,
            )
        self._tripped = False
        self._reason = ""
        self._tripped_at = None

        if event_store is not None:
            event_store.record(
                "circuit_breaker_reset",
                {"operator": operator, "prior_reason": prior_reason},
            )

    def status(self) -> dict:
        return {
            "tripped": self._tripped,
            "reason": self._reason,
            "tripped_at": self._tripped_at.isoformat() if self._tripped_at else None,
        }
