"""Execution Gateway.

Advisory pre-flight choke point for live order intent. Before a strategy
calls submit_order(), it should consult this gateway via
BaseStrategy.submit_order_guarded().

The gateway:
  1. Checks the circuit breaker
  2. Runs portfolio-level risk checks
  3. Emits metrics and structured logs

This is application-level advisory enforcement only. Emergency flatten,
on_stop flatten (when configured), and direct submit_order() calls bypass
this layer. True OMS-level blocking would require a deeper NautilusTrader hook.

In backtesting, the gateway is not wired (strategies submit directly).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.ops.metrics import ORDER_BLOCKED, ORDER_SUBMITTED
from nautilus_trade.risk.engine import PortfolioRiskEngine

log = logging.getLogger(__name__)


@dataclass
class OrderIntent:
    """Validated intent to place a live order."""

    instrument_id: str
    side: str  # BUY | SELL
    quantity: Decimal
    price: Decimal | None  # None = market order
    strategy_id: str
    notional_usd: float


class ExecutionGateway:
    """Advisory pre-flight validation for order intents."""

    def __init__(
        self,
        risk_engine: PortfolioRiskEngine,
        breaker: CircuitBreaker,
    ) -> None:
        self.risk = risk_engine
        self.breaker = breaker

    def submit(
        self,
        intent: OrderIntent,
        current_portfolio_notional_usd: float = 0.0,
        current_leverage: float = 1.0,
        open_order_count: int = 0,
    ) -> bool:
        """Return True if the intent passes pre-flight checks.

        Actual order submission remains the strategy's responsibility after approval.
        """
        if self.breaker.is_tripped:
            log.warning("GATEWAY BLOCKED (circuit open): %s", intent)
            ORDER_BLOCKED.labels(reason="circuit_open", strategy=intent.strategy_id).inc()
            return False

        allowed, reason = self.risk.check_before_order(
            side=intent.side,
            notional_usd=intent.notional_usd,
            current_portfolio_notional_usd=current_portfolio_notional_usd,
            current_leverage=current_leverage,
            open_order_count=open_order_count,
        )

        if not allowed:
            log.warning("GATEWAY BLOCKED (%s): %s", reason, intent)
            ORDER_BLOCKED.labels(reason=reason[:32], strategy=intent.strategy_id).inc()
            return False

        log.info("GATEWAY APPROVED: %s", intent)
        ORDER_SUBMITTED.labels(strategy=intent.strategy_id).inc()
        return True
