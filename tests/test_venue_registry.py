"""Venue registry tests."""

import pytest

from nautilus_trade.adapters.venue_registry import VENUE_DEFAULTS, resolve_venue_bundle


class TestVenueRegistry:
    def test_binance_bundle(self) -> None:
        pytest.importorskip("nautilus_trader")
        bundle = resolve_venue_bundle("binance")
        assert bundle.venue == "BINANCE"
        assert bundle.instrument_id == "BTCUSDT-PERP.BINANCE"
        assert "EXTERNAL" in bundle.bar_type
        assert bundle.recon_currencies == frozenset({"USDT"})

    def test_kraken_defaults(self) -> None:
        defaults = VENUE_DEFAULTS["KRAKEN"]
        assert defaults["instrument_id"] == "PF_XBTUSD.KRAKEN"
        assert "INTERNAL" in defaults["bar_type"]
        assert defaults["recon_currencies"] == frozenset({"USD"})

    def test_kraken_bundle_when_kraken_extra_installed(self) -> None:
        pytest.importorskip("nautilus_trader")
        try:
            bundle = resolve_venue_bundle("kraken")
        except ImportError as exc:
            pytest.skip(f"Kraken adapter unavailable: {exc}")
        assert bundle.venue == "KRAKEN"
        assert bundle.instrument_id == "PF_XBTUSD.KRAKEN"
