"""Execution gateway tests."""

from __future__ import annotations

import pytest

pytest.importorskip("prometheus_client")

from nautilus_trade.execution.gateway import ExecutionGateway, OrderIntent
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.risk.engine import PortfolioRiskEngine


def _intent(notional: float = 500.0, side: str = "BUY") -> OrderIntent:
    return OrderIntent(
        instrument_id="BTCUSDT-PERP.BINANCE",
        side=side,
        quantity=1,
        price=None,
        strategy_id="test",
        notional_usd=notional,
    )


class TestExecutionGateway:
    def test_approved_path(self) -> None:
        gateway = ExecutionGateway(PortfolioRiskEngine(), CircuitBreaker())
        assert gateway.submit(
            _intent(500.0),
            current_portfolio_notional_usd=1000.0,
            current_leverage=1.5,
            open_order_count=1,
        )

    def test_blocked_when_halted(self) -> None:
        engine = PortfolioRiskEngine()
        engine.halt("test")
        gateway = ExecutionGateway(engine, CircuitBreaker())
        assert not gateway.submit(_intent())

    def test_blocked_when_breaker_tripped(self) -> None:
        breaker = CircuitBreaker()
        breaker.trip("test")
        gateway = ExecutionGateway(PortfolioRiskEngine(breaker=breaker), breaker)
        assert not gateway.submit(_intent())

    def test_blocked_at_open_order_limit(self) -> None:
        gateway = ExecutionGateway(PortfolioRiskEngine(), CircuitBreaker())
        assert not gateway.submit(
            _intent(),
            current_portfolio_notional_usd=1000.0,
            current_leverage=1.0,
            open_order_count=25,
        )

    def test_blocked_at_portfolio_notional_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nautilus_trade.config import risk_cfg

        monkeypatch.setattr(risk_cfg, "max_portfolio_notional_usd", 5000.0)
        gateway = ExecutionGateway(PortfolioRiskEngine(), CircuitBreaker())
        assert not gateway.submit(
            _intent(notional=1000.0, side="BUY"),
            current_portfolio_notional_usd=4500.0,
            current_leverage=1.0,
            open_order_count=0,
        )

    def test_sell_does_not_add_portfolio_notional(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nautilus_trade.config import risk_cfg

        monkeypatch.setattr(risk_cfg, "max_portfolio_notional_usd", 5000.0)
        gateway = ExecutionGateway(PortfolioRiskEngine(), CircuitBreaker())
        assert gateway.submit(
            _intent(notional=1000.0, side="SELL"),
            current_portfolio_notional_usd=4500.0,
            current_leverage=1.0,
            open_order_count=0,
        )
