"""Portfolio statistics helper tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.portfolio.stats import (
    portfolio_leverage,
    portfolio_notional_usd,
    total_open_order_count,
)


class TestPortfolioStats:
    def test_portfolio_notional_sums_open_positions(self) -> None:
        instrument_id = SimpleNamespace()
        position = SimpleNamespace(
            is_open=True,
            instrument_id=instrument_id,
            quantity=Decimal("2"),
        )
        cache = SimpleNamespace(
            positions_open=lambda: [position],
            price=lambda _inst, _ptype: Decimal("100"),
        )
        portfolio = SimpleNamespace(accounts=lambda: [])

        assert portfolio_notional_usd(cache, portfolio) == 200.0

    def test_portfolio_leverage_uses_equity(self) -> None:
        instrument_id = SimpleNamespace()
        position = SimpleNamespace(
            is_open=True,
            instrument_id=instrument_id,
            quantity=Decimal("1"),
        )
        cache = SimpleNamespace(
            positions_open=lambda: [position],
            price=lambda _inst, _ptype: Decimal("300"),
        )
        balance = SimpleNamespace(total=Decimal("100"))
        account = SimpleNamespace(balances=lambda: {"USDT": balance})
        portfolio = SimpleNamespace(accounts=lambda: [account])

        assert portfolio_leverage(cache, portfolio) == pytest.approx(3.0)

    def test_total_open_order_count(self) -> None:
        cache = SimpleNamespace(orders_open=lambda: [object(), object()])
        assert total_open_order_count(cache) == 2
