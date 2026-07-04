"""Exit guarded submission tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("prometheus_client")
pytest.importorskip("nautilus_trader")

from nautilus_trade.execution.gateway import ExecutionGateway, OrderIntent
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.risk.engine import PortfolioRiskEngine
from nautilus_trade.strategies.base import BaseStrategy


class _StubStrategy(BaseStrategy):
    def strategy_name(self) -> str:
        return "Stub"


def _exit_intent(notional: float = 0.0) -> OrderIntent:
    return OrderIntent(
        instrument_id="BTCUSDT-PERP.BINANCE",
        side="SELL",
        quantity=Decimal("0.01"),
        price=None,
        strategy_id="Stub",
        notional_usd=notional,
    )


class TestSubmitExitGuarded:
    def test_blocks_exit_when_gateway_wired_and_notional_zero(self) -> None:
        strategy = _StubStrategy.__new__(_StubStrategy)
        strategy.cache = SimpleNamespace()
        strategy.portfolio = SimpleNamespace()
        gateway = ExecutionGateway(PortfolioRiskEngine(), CircuitBreaker())
        submit_fn = MagicMock()

        result = strategy.submit_exit_guarded(gateway, _exit_intent(0.0), submit_fn)

        assert result is False
        submit_fn.assert_not_called()

    def test_proceeds_without_gateway_when_notional_zero(self) -> None:
        strategy = _StubStrategy.__new__(_StubStrategy)
        strategy.cache = SimpleNamespace()
        strategy.portfolio = SimpleNamespace()
        submit_fn = MagicMock()

        result = strategy.submit_exit_guarded(None, _exit_intent(0.0), submit_fn)

        assert result is True
        submit_fn.assert_called_once()

    def test_uses_gateway_when_notional_positive(self) -> None:
        strategy = _StubStrategy.__new__(_StubStrategy)
        strategy.cache = SimpleNamespace(
            positions_open=lambda: [],
            price=lambda *_args: None,
        )
        strategy.portfolio = SimpleNamespace(accounts=lambda: [])
        gateway = ExecutionGateway(PortfolioRiskEngine(), CircuitBreaker())
        submit_fn = MagicMock()

        result = strategy.submit_exit_guarded(gateway, _exit_intent(500.0), submit_fn)

        assert result is True
        submit_fn.assert_called_once()
