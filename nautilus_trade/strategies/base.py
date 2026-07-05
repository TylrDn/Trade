"""Base strategy mixin with standardized lifecycle hooks and logging."""

from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from nautilus_trader.model.enums import OrderSide, PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

from nautilus_trade.config import system_cfg
from nautilus_trade.execution.gateway import ExecutionGateway, OrderIntent
from nautilus_trade.portfolio.stats import (
    portfolio_leverage,
    portfolio_notional_usd_strict,
    total_open_order_count,
)

if TYPE_CHECKING:
    from nautilus_trade.ops.event_store import EventStore
    from nautilus_trade.ops.order_timing import OrderTimingTracker

log = logging.getLogger(__name__)


class BaseStrategy(Strategy):
    """Extends NautilusTrader Strategy with shared risk-aware order helpers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._execution_gateway: ExecutionGateway | None = None
        self._event_store: EventStore | None = None
        self._order_timing_tracker: OrderTimingTracker | None = None
        self._guarded_submit = False
        self._pending_submit_ts_ns: int | None = None

    def bind_execution_gateway(
        self,
        gateway: ExecutionGateway | None,
        *,
        event_store: EventStore | None = None,
        order_timing_tracker: OrderTimingTracker | None = None,
    ) -> None:
        """Wire live OMS enforcement and fill latency tracking."""
        self._execution_gateway = gateway
        self._event_store = event_store
        self._order_timing_tracker = order_timing_tracker

    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable strategy identifier."""
        ...

    def on_start(self) -> None:
        log.info("[%s] Strategy starting", self.strategy_name())

    def on_stop(self) -> None:
        log.info("[%s] Strategy stopping", self.strategy_name())

    def on_reset(self) -> None:
        log.info("[%s] Strategy resetting", self.strategy_name())

    def on_dispose(self) -> None:
        log.info("[%s] Strategy disposing", self.strategy_name())

    def _record_oms_bypass(self, method: str) -> None:
        log.critical(
            "[%s] OMS bypass blocked: direct %s with gateway wired",
            self.strategy_name(),
            method,
        )
        if self._event_store is not None:
            self._event_store.record(
                "oms_bypass_attempt",
                {"strategy": self.strategy_name(), "method": method},
            )

    def submit_order(self, order: Any) -> None:
        if (
            self._execution_gateway is not None
            and not self._guarded_submit
            and not system_cfg.is_research
        ):
            self._record_oms_bypass("submit_order")
            return
        super().submit_order(order)
        if (
            self._guarded_submit
            and self._order_timing_tracker is not None
            and self._pending_submit_ts_ns is not None
        ):
            self._order_timing_tracker.record(
                str(order.client_order_id),
                self._pending_submit_ts_ns,
            )

    def close_position(self, position: Any, **kwargs: Any) -> None:
        if (
            self._execution_gateway is not None
            and not self._guarded_submit
            and not system_cfg.is_research
        ):
            self._record_oms_bypass("close_position")
            return
        super().close_position(position, **kwargs)

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
        position = self.cache.position_for_instrument(instrument_id)
        if position is None:
            return Decimal(0)
        price = self.cache.price(instrument_id, PriceType.MID)
        if price is None:
            log.warning("position_notional: no MID price for %s, returning 0", instrument_id)
            return Decimal(0)
        return Decimal(str(abs(position.quantity))) * Decimal(str(price))

    def trading_halted(self, gateway: ExecutionGateway | None) -> bool:
        """Return True when portfolio-level trading is halted."""
        if gateway is None:
            return False
        return gateway.risk.is_halted or gateway.breaker.is_tripped

    def gateway_order_context(
        self,
        gateway: ExecutionGateway | None,
    ) -> tuple[float | None, float, int]:
        """Return portfolio notional, leverage, and open order count for gateway checks."""
        if gateway is None:
            return 0.0, 1.0, 0
        notional = portfolio_notional_usd_strict(self.cache, self.portfolio)
        if notional is None:
            return None, portfolio_leverage(self.cache, self.portfolio), total_open_order_count(
                self.cache
            )
        return (
            notional,
            portfolio_leverage(self.cache, self.portfolio),
            total_open_order_count(self.cache),
        )

    def submit_order_guarded(
        self,
        gateway: ExecutionGateway | None,
        intent: OrderIntent,
        submit_fn: Callable[[], None],
    ) -> bool:
        """Run advisory gateway pre-flight, then submit if approved."""
        if gateway is None:
            submit_fn()
            return True

        portfolio_notional, leverage, open_order_count = self.gateway_order_context(gateway)
        if not gateway.submit(
            intent,
            current_portfolio_notional_usd=portfolio_notional,
            current_leverage=leverage,
            open_order_count=open_order_count,
        ):
            log.warning(
                "[%s] Order blocked by ExecutionGateway pre-flight: %s",
                self.strategy_name(),
                intent,
            )
            return False

        self._pending_submit_ts_ns = self.clock.timestamp_ns()
        self._guarded_submit = True
        try:
            submit_fn()
        finally:
            self._guarded_submit = False
            self._pending_submit_ts_ns = None
        return True

    def submit_exit_guarded(
        self,
        gateway: ExecutionGateway | None,
        intent: OrderIntent,
        submit_fn: Callable[[], None],
    ) -> bool:
        """Run gateway pre-flight for exit orders."""
        if gateway is None:
            submit_fn()
            return True

        if intent.notional_usd <= 0:
            log.critical(
                "[%s] Exit blocked: MID price unavailable with gateway wired (fail-closed)",
                self.strategy_name(),
            )
            return False

        return self.submit_order_guarded(gateway, intent, submit_fn)
