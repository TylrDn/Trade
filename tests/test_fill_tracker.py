"""Fill tracker PnL extraction tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.portfolio.pnl import realized_pnl_delta_usd


class TestRealizedPnlDelta:
    def test_position_delta_on_increase(self) -> None:
        position = SimpleNamespace(
            id="P-1",
            instrument_id="BTCUSDT-PERP.BINANCE",
            realized_pnl=SimpleNamespace(as_double=lambda: 100.0),
        )
        cache = SimpleNamespace(
            position=lambda _pid: position,
            position_for_instrument=lambda _iid: position,
        )
        event = SimpleNamespace(
            instrument_id="BTCUSDT-PERP.BINANCE",
            position_id="P-1",
        )
        last_seen: dict[str, Decimal] = {"P-1": Decimal("40")}

        delta, source = realized_pnl_delta_usd(cache, event, last_seen)

        assert delta == pytest.approx(60.0)
        assert source == "position_delta"
        assert last_seen["P-1"] == Decimal("100.0")

    def test_unavailable_without_position(self) -> None:
        cache = SimpleNamespace(
            position=lambda _pid: None,
            position_for_instrument=lambda _iid: None,
        )
        event = SimpleNamespace(
            instrument_id="BTCUSDT-PERP.BINANCE",
            position_id=None,
        )
        last_seen: dict[str, Decimal] = {}

        delta, source = realized_pnl_delta_usd(cache, event, last_seen)

        assert delta == 0.0
        assert source == "unavailable"
