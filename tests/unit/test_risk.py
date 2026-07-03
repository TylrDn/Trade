"""Risk engine tests."""

from __future__ import annotations

from decimal import Decimal

from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.risk.engine import DailyStats, PortfolioRiskEngine


class TestCircuitBreaker:
    def test_initial_state_is_open(self) -> None:
        cb = CircuitBreaker()
        assert not cb.is_tripped

    def test_trip_sets_tripped(self) -> None:
        cb = CircuitBreaker()
        cb.trip("test reason")
        assert cb.is_tripped

    def test_trip_is_idempotent(self) -> None:
        cb = CircuitBreaker()
        cb.trip("reason 1")
        cb.trip("reason 2")  # Should not raise
        assert cb.is_tripped

    def test_reset_clears_state(self) -> None:
        cb = CircuitBreaker()
        cb.trip("test")
        cb.reset()
        assert not cb.is_tripped

    def test_status_reflects_state(self) -> None:
        cb = CircuitBreaker()
        status = cb.status()
        assert status["tripped"] is False
        assert status["tripped_at"] is None

        cb.trip("stale feed")
        status = cb.status()
        assert status["tripped"] is True
        assert status["reason"] == "stale feed"
        assert status["tripped_at"] is not None


class TestPortfolioRiskEngine:
    def test_check_allows_valid_order(self) -> None:
        engine = PortfolioRiskEngine()
        allowed, reason = engine.check_before_order(
            side="BUY",
            notional_usd=1000.0,
            current_portfolio_notional_usd=5000.0,
            current_leverage=1.5,
        )
        assert allowed
        assert reason == ""

    def test_check_blocks_oversized_notional(self) -> None:
        engine = PortfolioRiskEngine()
        allowed, reason = engine.check_before_order(
            side="BUY",
            notional_usd=999_999.0,  # Way over limit
            current_portfolio_notional_usd=5000.0,
            current_leverage=1.5,
        )
        assert not allowed
        assert "notional" in reason.lower()

    def test_check_blocks_excess_leverage(self) -> None:
        engine = PortfolioRiskEngine()
        allowed, reason = engine.check_before_order(
            side="BUY",
            notional_usd=500.0,
            current_portfolio_notional_usd=5000.0,
            current_leverage=10.0,  # Way over max_leverage=3.0
        )
        assert not allowed
        assert "leverage" in reason.lower()

    def test_check_blocks_when_halted(self) -> None:
        engine = PortfolioRiskEngine()
        engine._halted = True
        allowed, reason = engine.check_before_order(
            side="BUY",
            notional_usd=500.0,
            current_portfolio_notional_usd=5000.0,
            current_leverage=1.0,
        )
        assert not allowed
        assert "halted" in reason.lower()

    def test_check_blocks_when_circuit_tripped(self) -> None:
        cb = CircuitBreaker()
        cb.trip("test")
        engine = PortfolioRiskEngine(breaker=cb)
        allowed, _reason = engine.check_before_order(
            side="BUY",
            notional_usd=500.0,
            current_portfolio_notional_usd=5000.0,
            current_leverage=1.0,
        )
        assert not allowed

    def test_daily_loss_halt(self) -> None:
        engine = PortfolioRiskEngine()
        # Simulate large loss
        engine.record_fill(-600.0)  # Default limit is 500
        assert engine.is_halted

    def test_resume_clears_halt(self) -> None:
        engine = PortfolioRiskEngine()
        engine.record_fill(-600.0)
        assert engine.is_halted
        engine.resume("operator")
        assert not engine.is_halted


class TestDailyStats:
    def test_initial_state(self) -> None:
        stats = DailyStats()
        assert stats.realized_pnl_usd == Decimal(0)
        assert stats.fill_count == 0

    def test_reset_if_new_day_is_idempotent_same_day(self) -> None:
        stats = DailyStats()
        stats.realized_pnl_usd = Decimal("-100")
        stats.fill_count = 5
        stats.reset_if_new_day()  # Same day — should not reset
        assert stats.realized_pnl_usd == Decimal("-100")
        assert stats.fill_count == 5
