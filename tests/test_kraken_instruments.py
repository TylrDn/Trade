"""Kraken instrument mapping tests."""

from decimal import Decimal

from nautilus_trade.adapters.kraken_instruments import (
    kraken_symbol_to_instrument_id,
    map_kraken_positions,
)


class TestKrakenInstruments:
    def test_symbol_to_instrument_id(self) -> None:
        assert kraken_symbol_to_instrument_id("PF_XBTUSD") == "PF_XBTUSD.KRAKEN"

    def test_map_positions(self) -> None:
        mapped = map_kraken_positions({"PF_XBTUSD": Decimal("0.01")})
        assert mapped == {"PF_XBTUSD.KRAKEN": Decimal("0.01")}
