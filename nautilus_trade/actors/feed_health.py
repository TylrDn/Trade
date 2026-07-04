"""Feed health monitor actor.

Trips the circuit breaker when bar data stops arriving within the
configured staleness threshold, or when no bar arrives within the startup
grace period in staging/production.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from nautilus_trader.config import ActorConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.trading.actor import Actor

from nautilus_trade.config import risk_cfg, system_cfg
from nautilus_trade.ops.alerts import send_alert
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.ops.metrics import FEED_STALE
from nautilus_trade.portfolio.stats import refresh_portfolio_notional_metrics

log = logging.getLogger(__name__)

_TIMER_NAME = "feed_health_check"


class FeedHealthGuardConfig(ActorConfig, frozen=True):
    bar_type: str
    stale_seconds: int | None = None
    startup_grace_seconds: int | None = None
    check_interval_seconds: int = 10


class FeedHealthGuard(Actor):
    """Monitors bar feed freshness and trips the circuit breaker on stale data."""

    def __init__(
        self,
        config: FeedHealthGuardConfig,
        breaker: CircuitBreaker,
        trip_fn: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(config)
        self.cfg = config
        self._breaker = breaker
        self._trip_fn = trip_fn or breaker.trip
        self._stale_seconds = (
            config.stale_seconds
            if config.stale_seconds is not None
            else risk_cfg.stale_feed_seconds
        )
        self._startup_grace_seconds = (
            config.startup_grace_seconds
            if config.startup_grace_seconds is not None
            else risk_cfg.feed_startup_grace_seconds
        )
        self.bar_type = BarType.from_str(config.bar_type)
        self._last_bar_ts: int | None = None
        self._started_at_ns: int | None = None
        self._startup_tripped = False
        self._stale_tripped = False

    def on_start(self) -> None:
        self._started_at_ns = self.clock.timestamp_ns()
        self.subscribe_bars(self.bar_type)
        self.clock.set_timer(
            name=_TIMER_NAME,
            interval=self.cfg.check_interval_seconds,
            callback=self._on_health_timer,
        )
        log.info(
            "FeedHealthGuard started for %s (stale=%ss, startup_grace=%ss, interval=%ss)",
            self.cfg.bar_type,
            self._stale_seconds,
            self._startup_grace_seconds,
            self.cfg.check_interval_seconds,
        )

    def on_bar(self, bar: Bar) -> None:
        self._last_bar_ts = bar.ts_event
        self._stale_tripped = False

    def _on_health_timer(self, _event: object) -> None:
        now_ns = self.clock.timestamp_ns()
        self._evaluate(now_ns)
        cache = getattr(self, "cache", None)
        portfolio = getattr(self, "portfolio", None)
        if cache is not None and portfolio is not None:
            refresh_portfolio_notional_metrics(cache, portfolio)

    def _evaluate(self, now_ns: int) -> None:
        """Check feed staleness. Exposed for direct testing."""
        if self._last_bar_ts is None:
            self._evaluate_startup_timeout(now_ns)
            return

        elapsed_seconds = (now_ns - self._last_bar_ts) / 1e9
        if elapsed_seconds > self._stale_seconds:
            if self._stale_tripped:
                return

            self._stale_tripped = True
            log.critical(
                "Feed stale: %s seconds since last bar (%s)",
                elapsed_seconds,
                self.cfg.bar_type,
            )
            send_alert(
                f"🚨 Feed stale: {elapsed_seconds:.0f}s since last bar",
                level="critical",
            )
            FEED_STALE.labels(instrument=self.cfg.bar_type).inc()
            self._trip_fn(f"stale_feed:{self.cfg.bar_type}")

    def _evaluate_startup_timeout(self, now_ns: int) -> None:
        if system_cfg.is_research or self._startup_tripped:
            return

        started_at_ns = self._started_at_ns if self._started_at_ns is not None else now_ns
        elapsed_seconds = (now_ns - started_at_ns) / 1e9
        if elapsed_seconds <= self._startup_grace_seconds:
            return

        self._startup_tripped = True
        log.critical(
            "Feed startup timeout: no bar received within %ss (%s)",
            self._startup_grace_seconds,
            self.cfg.bar_type,
        )
        send_alert(
            f"🚨 Feed startup timeout: no bar within {self._startup_grace_seconds}s",
            level="critical",
        )
        FEED_STALE.labels(instrument=self.cfg.bar_type).inc()
        self._trip_fn(f"feed_startup_timeout:{self.cfg.bar_type}")
