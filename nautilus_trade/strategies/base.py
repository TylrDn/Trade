"""Base strategy mixin with standardized lifecycle hooks and logging."""

from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import Callable
from decimal import Decimal

from nautilus_trader.model.enums import OrderSide, PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

from nautilus_trade.execution.gateway import ExecutionGateway, OrderIntent
from nautilus_trade.portfolio.stats import (
    portfolio_leverage,
    portfolio_notional_usd_strict,
    total_open_order_count,
)

log = logging.getLogger(__name__)


class BaseStrategy(Strategy):
    """Extends NautilusTrader Strategy with shared risk-aware order helpers.

    ExecutionGateway integration is advisory pre-flight only. Strategies must
    call submit_order_guarded() to consult the gateway before submission.
    """

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
        """Run advisory gateway pre-flight, then submit if approved.

        Returns True when submission proceeds, False when blocked or no gateway.
        When gateway is None (backtest), submission proceeds without checks.
        """
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

        submit_fn()
        return True

    def submit_exit_guarded(
        self,
        gateway: ExecutionGateway | None,
        intent: OrderIntent,
        submit_fn: Callable[[], None],
    ) -> bool:
        """Run gateway pre-flight for exit orders.

        When the gateway is wired and exit notional is unknown (MID price missing),
        block the exit rather than bypassing safety checks. Backtest paths without
        a gateway proceed without checks.
        """
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
