"""Feed health guard tests.

Requires nautilus_trader and prometheus_client for full execution;
skipped cleanly in minimal environments without those dependencies.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

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

        guard._evaluate(now_ns)
        assert len(trips) == 1

    def test_stale_episode_resets_on_fresh_bar_and_can_trip_again(self) -> None:
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
        assert len(trips) == 1

        guard._last_bar_ts = now_ns
        guard._stale_tripped = False
        guard._evaluate(now_ns + int(60 * 1e9))
        assert len(trips) == 2

    def test_health_timer_refreshes_portfolio_notional_metrics(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[object, object]] = []

        def _refresh(cache: object, portfolio: object) -> None:
            calls.append((cache, portfolio))

        monkeypatch.setattr(
            "nautilus_trade.actors.feed_health.refresh_portfolio_notional_metrics",
            _refresh,
        )
        guard = FeedHealthGuard(
            FeedHealthGuardConfig(bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL"),
            breaker=CircuitBreaker(),
        )
        cache = SimpleNamespace()
        portfolio = SimpleNamespace()
        guard.cache = cache  # type: ignore[attr-defined]
        guard.portfolio = portfolio  # type: ignore[attr-defined]
        guard.clock = MagicMock(timestamp_ns=lambda: 1_700_000_000_000_000_000)
        guard._last_bar_ts = guard.clock.timestamp_ns() - int(5 * 1e9)

        guard._on_health_timer(None)

        assert calls == [(cache, portfolio)]

    def test_no_startup_trip_in_research_before_first_bar(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from nautilus_trade.config import system_cfg

        monkeypatch.setattr(system_cfg, "is_research", True)
        breaker = CircuitBreaker()
        guard = FeedHealthGuard(
            FeedHealthGuardConfig(
                bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                startup_grace_seconds=30,
            ),
            breaker=breaker,
        )
        now_ns = 1_700_000_000_000_000_000
        guard._started_at_ns = now_ns - int(120 * 1e9)
        guard._evaluate(now_ns)
        assert not breaker.is_tripped

    def test_trips_on_startup_timeout_in_staging(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nautilus_trade.config import system_cfg

        monkeypatch.setattr(system_cfg, "is_research", False)
        breaker = CircuitBreaker()
        trips: list[str] = []

        def trip_fn(reason: str) -> None:
            trips.append(reason)
            breaker.trip(reason)

        guard = FeedHealthGuard(
            FeedHealthGuardConfig(
                bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                startup_grace_seconds=30,
            ),
            breaker=breaker,
            trip_fn=trip_fn,
        )
        now_ns = 1_700_000_000_000_000_000
        guard._started_at_ns = now_ns - int(60 * 1e9)
        guard._evaluate(now_ns)
        assert breaker.is_tripped
        assert trips[0].startswith("feed_startup_timeout:")

        guard._evaluate(now_ns)
        assert len(trips) == 1

    @pytest.mark.staging
    def test_startup_timeout_respects_trade_env_staging(self) -> None:
        from nautilus_trade.config import system_cfg

        if system_cfg.is_research:
            pytest.skip("Requires TRADE_ENV=staging")

        breaker = CircuitBreaker()
        guard = FeedHealthGuard(
            FeedHealthGuardConfig(
                bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                startup_grace_seconds=30,
            ),
            breaker=breaker,
        )
        now_ns = 1_700_000_000_000_000_000
        guard._started_at_ns = now_ns - int(60 * 1e9)
        guard._evaluate(now_ns)
        assert breaker.is_tripped
