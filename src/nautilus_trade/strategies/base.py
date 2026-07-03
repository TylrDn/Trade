"""Base strategy mixin with standardized lifecycle hooks and logging."""

from __future__ import annotations

import logging
from abc import abstractmethod
from decimal import Decimal

from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

log = logging.getLogger(__name__)


class BaseStrategy(Strategy):
    """Extends NautilusTrader Strategy with shared risk-aware order helpers.

    All strategies in this system should inherit from BaseStrategy to
    ensure consistent logging, risk pre-checks, and metric emission.
    """

    # ── Required overrides ────────────────────────────────────────────────

    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable strategy identifier."""
        ...

    # ── Lifecycle logging ─────────────────────────────────────────────────

    def on_start(self) -> None:
        log.info("[%s] Strategy starting", self.strategy_name())

    def on_stop(self) -> None:
        log.info("[%s] Strategy stopping", self.strategy_name())

    def on_reset(self) -> None:
        log.info("[%s] Strategy resetting", self.strategy_name())

    def on_dispose(self) -> None:
        log.info("[%s] Strategy disposing", self.strategy_name())

    # ── Helpers ───────────────────────────────────────────────────────────

    def log_signal(
        self,
        side: OrderSide,
        instrument_id: InstrumentId,
        quantity: Quantity,
        reason: str = "",
    ) -> None:
        log.info(
            "[%s] SIGNAL %s %s qty=%s reason=%s",
            self.strategy_name(),
            side.name,
            instrument_id,
            quantity,
            reason,
        )

    def position_notional(self, instrument_id: InstrumentId) -> Decimal:
        """Return the current open position notional for an instrument."""
        position = self.cache.position_for_instrument(instrument_id)  # type: ignore
        if position is None:
            return Decimal(0)
        return Decimal(str(abs(position.quantity))) * Decimal(
            str(self.cache.price(instrument_id, price_type=None) or 0)
        )
