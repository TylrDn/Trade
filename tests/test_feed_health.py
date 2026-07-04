"""Feed health guard tests.

Requires nautilus_trader and prometheus_client for full execution;
skipped cleanly in minimal environments without those dependencies.
"""

from __future__ import annotations

import pytest

pytest.importorskip("nautilus_trader")
pytest.importorskip("prometheus_client")

from nautilus_trade.actors.feed_health import FeedHealthGuard, FeedHealthGuardConfig
from nautilus_trade.ops.circuit_breaker import CircuitBreaker


class TestFeedHealthGuard:
    def test_no_trip_when_feed_is_fresh(self) -> None:
        breaker = CircuitBreaker()
        guard = FeedHealthGuard(
            FeedHealthGuardConfig(bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL"),
            breaker=breaker,
        )
        now_ns = 1_700_000_000_000_000_000
        guard._last_bar_ts = now_ns - int(5 * 1e9)
        guard._evaluate(now_ns)
        assert not breaker.is_tripped

    def test_trips_circuit_on_stale_feed(self) -> None:
        breaker = CircuitBreaker()
        trips: list[str] = []

        def trip_fn(reason: str) -> None:
            trips.append(reason)
            breaker.trip(reason)

        guard = FeedHealthGuard(
            FeedHealthGuardConfig(
                bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                stale_seconds=30,
            ),
            breaker=breaker,
            trip_fn=trip_fn,
        )
        now_ns = 1_700_000_000_000_000_000
        guard._last_bar_ts = now_ns - int(60 * 1e9)
        guard._evaluate(now_ns)
        assert breaker.is_tripped
        assert trips[0].startswith("stale_feed:")

    def test_no_check_before_first_bar(self) -> None:
        breaker = CircuitBreaker()
        guard = FeedHealthGuard(
            FeedHealthGuardConfig(bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL"),
            breaker=breaker,
        )
        now_ns = 1_700_000_000_000_000_000
        guard._evaluate(now_ns)
        assert not breaker.is_tripped
