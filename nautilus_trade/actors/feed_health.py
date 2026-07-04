"""Feed health monitor actor.

Trips the circuit breaker when bar data stops arriving within the
configured staleness threshold.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from nautilus_trader.config import ActorConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.trading.actor import Actor

from nautilus_trade.config import risk_cfg
from nautilus_trade.ops.alerts import send_alert
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.ops.metrics import FEED_STALE

log = logging.getLogger(__name__)

_TIMER_NAME = "feed_health_check"


class FeedHealthGuardConfig(ActorConfig, frozen=True):
    bar_type: str
    stale_seconds: int | None = None
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
        self.bar_type = BarType.from_str(config.bar_type)
        self._last_bar_ts: int | None = None

    def on_start(self) -> None:
        self.subscribe_bars(self.bar_type)
        self.clock.set_timer(
            name=_TIMER_NAME,
            interval=self.cfg.check_interval_seconds,
            callback=self._on_health_timer,
        )
        log.info(
            "FeedHealthGuard started for %s (stale=%ss, interval=%ss)",
            self.cfg.bar_type,
            self._stale_seconds,
            self.cfg.check_interval_seconds,
        )

    def on_bar(self, bar: Bar) -> None:
        self._last_bar_ts = bar.ts_event

    def _on_health_timer(self, _event: object) -> None:
        now_ns = self.clock.timestamp_ns()
        self._evaluate(now_ns)

    def _evaluate(self, now_ns: int) -> None:
        """Check feed staleness. Exposed for direct testing."""
        if self._last_bar_ts is None:
            return

        elapsed_seconds = (now_ns - self._last_bar_ts) / 1e9
        if elapsed_seconds > self._stale_seconds:
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
