"""FX converter tests."""

from decimal import Decimal

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.portfolio.fx import UsdtPegConverter


class TestUsdtPegConverter:
    def test_usdt_pegged_to_usd(self) -> None:
        converter = UsdtPegConverter()
        assert converter.to_usd(Decimal("100"), "USDT") == Decimal("100")

    def test_unknown_currency_returns_none(self) -> None:
        converter = UsdtPegConverter()
        assert converter.to_usd(Decimal("1"), "EUR") is None
