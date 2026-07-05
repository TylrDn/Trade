"""OMS enforcement tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.execution.gateway import ExecutionGateway
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.ops.order_timing import OrderTimingTracker
from nautilus_trade.risk.engine import PortfolioRiskEngine
from nautilus_trade.strategies.base import BaseStrategy


class _StubStrategy(BaseStrategy):
    def strategy_name(self) -> str:
        return "Stub"


class TestOmsEnforcement:
    def test_direct_submit_blocked_without_super_in_staging(self, monkeypatch) -> None:
        from nautilus_trade.config import system_cfg

        monkeypatch.setattr(system_cfg, "is_research", False)
        strategy = _StubStrategy.__new__(_StubStrategy)
        breaker = CircuitBreaker()
        gateway = ExecutionGateway(PortfolioRiskEngine(breaker=breaker), breaker)
        strategy.bind_execution_gateway(gateway, event_store=MagicMock(), order_timing_tracker=OrderTimingTracker())
        strategy.clock = MagicMock(timestamp_ns=lambda: 1)

        with patch.object(BaseStrategy, "submit_order") as mock_super:
            strategy.submit_order(MagicMock(client_order_id="cid-1"))
            mock_super.assert_not_called()
