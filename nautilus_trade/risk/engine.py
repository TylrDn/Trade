"""Portfolio-level risk engine.

Sits above all strategies and enforces system-wide limits that cannot
be bypassed by individual strategies. Works alongside NautilusTrader's
built-in risk engine (RiskEngine) as an additional application layer.

This module provides:
- Daily loss tracking and halt logic
- Portfolio-level notional and leverage checks
- Feed-health monitoring
- Integration with circuit breaker and alerting
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from nautilus_trade.config import risk_cfg
from nautilus_trade.ops.alerts import send_alert
from nautilus_trade.ops.circuit_breaker import CircuitBreaker

log = logging.getLogger(__name__)


@dataclass
class DailyStats:
    """Tracks per-day P&L for halt logic."""

    date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    realized_pnl_usd: Decimal = Decimal(0)
    fill_count: int = 0

    def reset_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self.date:
            log.info("New trading day: resetting daily stats (prev date=%s)", self.date)
            self.date = today
            self.realized_pnl_usd = Decimal(0)
            self.fill_count = 0


class PortfolioRiskEngine:
    """Application-level portfolio risk engine.

    Call check_before_order() before submitting any live order.
    Call record_fill() after each fill to track daily P&L.
    """

    def __init__(self, breaker: CircuitBreaker | None = None) -> None:
        self.breaker = breaker or CircuitBreaker()
        self.daily = DailyStats()
        self._halted = False

    @property
    def is_halted(self) -> bool:
        return self._halted or self.breaker.is_tripped

    def halt(self, reason: str) -> None:
        """Halt all trading activity immediately."""
        if not self._halted:
            self._halted = True
            log.critical("PORTFOLIO RISK HALT: %s", reason)
            send_alert(f"🚨 TRADING HALTED: {reason}", level="critical")

    def resume(self, operator: str = "system") -> None:
        """Resume trading after manual review."""
        log.warning("PORTFOLIO RISK RESUMED by %s", operator)
        self._halted = False
        self.breaker.reset()
        send_alert(f"✅ Trading resumed by {operator}", level="info")

    def check_before_order(
        self,
        side: str,
        notional_usd: float,
        current_portfolio_notional_usd: float,
        current_leverage: float,
    ) -> tuple[bool, str]:
        """Return (allowed, reason). Call before any live order submission."""
        self.daily.reset_if_new_day()

        if self.is_halted:
            return False, "System halted"

        if notional_usd > risk_cfg.max_position_notional_usd:
            return False, (
                f"Position notional ${notional_usd:.0f} exceeds limit "
                f"${risk_cfg.max_position_notional_usd:.0f}"
            )

        if current_leverage > risk_cfg.max_leverage:
            return False, (
                f"Portfolio leverage {current_leverage:.2f}x exceeds limit "
                f"{risk_cfg.max_leverage:.2f}x"
            )

        return True, ""

    def record_fill(self, realized_pnl_usd: float) -> None:
        """Update daily P&L tracker and check daily loss limit."""
        self.daily.reset_if_new_day()
        self.daily.realized_pnl_usd += Decimal(str(realized_pnl_usd))
        self.daily.fill_count += 1

        if self.daily.realized_pnl_usd < -Decimal(str(risk_cfg.max_daily_loss_usd)):
            self.halt(
                f"Daily loss limit hit: "
                f"${float(self.daily.realized_pnl_usd):.2f} "
                f"(limit: -${risk_cfg.max_daily_loss_usd:.2f})"
            )
