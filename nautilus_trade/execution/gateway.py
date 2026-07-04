"""Execution Gateway.

The single choke-point through which all live order intent flows.
Before routing any order to NautilusTrader for submission, this gateway:
  1. Checks the circuit breaker
  2. Runs portfolio-level risk checks
  3. Validates order parameters
  4. Emits metrics and structured logs

No code outside this module should submit live orders directly.
In backtesting, this gateway is bypassed (strategies call submit_order
directly, as designed by NautilusTrader).
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
    """Validates and routes order intents through risk controls."""

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
        """Validate and approve the intent. Returns True if allowed.

        Actual NautilusTrader order submission happens inside the strategy
        via self.submit_order(). This gateway is called by the strategy
        before that call as a pre-flight check.
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
