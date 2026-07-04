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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from nautilus_trade.config import risk_cfg, system_cfg
from nautilus_trade.ops.alerts import send_alert
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.ops.metrics import PORTFOLIO_HALTED

if TYPE_CHECKING:
    from nautilus_trade.ops.event_store import EventStore

log = logging.getLogger(__name__)

TripFn = Callable[[str], None]


@dataclass
class DailyStats:
    """Tracks per-day P&L for halt logic."""

    date: date = field(default_factory=lambda: datetime.now(UTC).date())
    realized_pnl_usd: Decimal = Decimal(0)
    fill_count: int = 0

    def reset_if_new_day(self) -> None:
        today = datetime.now(UTC).date()
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

    def __init__(
        self,
        breaker: CircuitBreaker | None = None,
        trip_fn: TripFn | None = None,
        event_store: EventStore | None = None,
    ) -> None:
        self.breaker = breaker or CircuitBreaker()
        self._trip_fn = trip_fn
        self._event_store = event_store
        self.daily = DailyStats()
        self._halted = False
        self._pnl_tracking_degraded = False

    @property
    def is_halted(self) -> bool:
        return self._halted or self.breaker.is_tripped

    @property
    def pnl_tracking_degraded(self) -> bool:
        return self._pnl_tracking_degraded

    def mark_pnl_tracking_degraded(self) -> None:
        """Mark daily PnL accounting as unreliable after unresolved fill PnL."""
        self._pnl_tracking_degraded = True

    def halt(self, reason: str) -> None:
        """Halt all trading activity immediately."""
        if not self._halted:
            self._halted = True
            PORTFOLIO_HALTED.set(1)
            log.critical("PORTFOLIO RISK HALT: %s", reason)
            send_alert(f"🚨 TRADING HALTED: {reason}", level="critical")

    def resume(self, operator: str = "system") -> None:
        """Resume trading after manual review."""
        if system_cfg.is_live and operator == "system":
            log.error(
                "Resume rejected in production: operator='system' is not allowed in live env. "
                "Provide an explicit operator identifier."
            )
            raise ValueError(
                "Trading resume in production requires an explicit human operator identifier, "
                "not 'system'."
            )
        log.warning("PORTFOLIO RISK RESUMED by %s", operator)
        self._halted = False
        self._pnl_tracking_degraded = False
        PORTFOLIO_HALTED.set(0)
        self.breaker.reset(operator, event_store=self._event_store)
        send_alert(f"✅ Trading resumed by {operator}", level="info")

    def check_before_order(
        self,
        side: str,
        notional_usd: float,
        current_portfolio_notional_usd: float | None = None,
        current_leverage: float = 1.0,
        open_order_count: int = 0,
    ) -> tuple[bool, str]:
        """Return (allowed, reason). Call before any live order submission."""
        self.daily.reset_if_new_day()

        if self.is_halted:
            return False, "System halted"

        if not system_cfg.is_research and self._pnl_tracking_degraded:
            return False, "PnL tracking degraded"

        if not system_cfg.is_research and current_portfolio_notional_usd is None:
            return False, "Portfolio notional incomplete (missing MID prices)"

        portfolio_notional = (
            0.0 if current_portfolio_notional_usd is None else current_portfolio_notional_usd
        )

        if notional_usd > risk_cfg.max_position_notional_usd:
            return False, (
                f"Position notional ${notional_usd:.0f} exceeds limit "
                f"${risk_cfg.max_position_notional_usd:.0f}"
            )

        if side.upper() == "BUY":
            projected = portfolio_notional + notional_usd
            if projected > risk_cfg.max_portfolio_notional_usd:
                return False, (
                    f"Portfolio notional ${projected:.0f} would exceed limit "
                    f"${risk_cfg.max_portfolio_notional_usd:.0f}"
                )

        if current_leverage > risk_cfg.max_leverage:
            return False, (
                f"Portfolio leverage {current_leverage:.2f}x exceeds limit "
                f"{risk_cfg.max_leverage:.2f}x"
            )

        if open_order_count >= risk_cfg.max_open_orders:
            return False, (
                f"Open order count {open_order_count} at or above limit "
                f"{risk_cfg.max_open_orders}"
            )

        return True, ""

    def record_fill(self, realized_pnl_usd: float) -> None:
        """Update daily P&L tracker and check daily loss limit."""
        self.daily.reset_if_new_day()
        self.daily.realized_pnl_usd += Decimal(str(realized_pnl_usd))
        self.daily.fill_count += 1

        if self.daily.realized_pnl_usd < -Decimal(str(risk_cfg.max_daily_loss_usd)):
            reason = (
                f"Daily loss limit hit: "
                f"${float(self.daily.realized_pnl_usd):.2f} "
                f"(limit: -${risk_cfg.max_daily_loss_usd:.2f})"
            )
            self.halt(reason)
            if self._trip_fn is not None:
                self._trip_fn("daily_loss_limit")
