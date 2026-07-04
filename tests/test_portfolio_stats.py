"""Portfolio statistics helper tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.portfolio.stats import (
    portfolio_leverage,
    portfolio_notional_usd,
    portfolio_notional_usd_strict,
    refresh_portfolio_notional_metrics,
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

    def test_portfolio_notional_strict_returns_none_when_price_missing(self) -> None:
        instrument_id = SimpleNamespace()
        position = SimpleNamespace(
            is_open=True,
            instrument_id=instrument_id,
            quantity=Decimal("1"),
        )
        cache = SimpleNamespace(
            positions_open=lambda: [position],
            price=lambda _inst, _ptype: None,
        )
        portfolio = SimpleNamespace(accounts=lambda: [])

        assert portfolio_notional_usd_strict(cache, portfolio) is None

    def test_portfolio_notional_strict_sums_when_complete(self) -> None:
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

        assert portfolio_notional_usd_strict(cache, portfolio) == 200.0

    def test_refresh_portfolio_notional_metrics_marks_incomplete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("prometheus_client")
        from nautilus_trade.ops import metrics

        monkeypatch.setattr(metrics.PORTFOLIO_NOTIONAL_USD, "set", lambda value: None)
        incomplete_values: list[float] = []
        monkeypatch.setattr(
            metrics.PORTFOLIO_NOTIONAL_INCOMPLETE,
            "set",
            incomplete_values.append,
        )

        instrument_id = SimpleNamespace()
        position = SimpleNamespace(
            is_open=True,
            instrument_id=instrument_id,
            quantity=Decimal("1"),
        )
        cache = SimpleNamespace(
            positions_open=lambda: [position],
            price=lambda _inst, _ptype: None,
        )
        portfolio = SimpleNamespace(accounts=lambda: [])

        refresh_portfolio_notional_metrics(cache, portfolio)

        assert incomplete_values == [1.0]

    def test_refresh_portfolio_notional_metrics_sets_notional_when_complete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("prometheus_client")
        from nautilus_trade.ops import metrics

        notional_values: list[float] = []
        incomplete_values: list[float] = []
        monkeypatch.setattr(metrics.PORTFOLIO_NOTIONAL_USD, "set", notional_values.append)
        monkeypatch.setattr(
            metrics.PORTFOLIO_NOTIONAL_INCOMPLETE,
            "set",
            incomplete_values.append,
        )

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

        refresh_portfolio_notional_metrics(cache, portfolio)

        assert incomplete_values == [0.0]
        assert notional_values == [200.0]

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
