"""Venue registry — resolve live/backtest bundles for Binance and Kraken."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nautilus_trade.config import adapter_cfg, recon_cfg, system_cfg

VENUE_DEFAULTS: dict[str, dict[str, Any]] = {
    "BINANCE": {
        "venue": "BINANCE",
        "instrument_id": "BTCUSDT-PERP.BINANCE",
        "bar_type": "BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
        "recon_currencies": frozenset({"USDT"}),
    },
    "KRAKEN": {
        "venue": "KRAKEN",
        "instrument_id": "PF_XBTUSD.KRAKEN",
        "bar_type": "PF_XBTUSD.KRAKEN-1-MINUTE-LAST-INTERNAL",
        "recon_currencies": frozenset({"USD"}),
    },
}


@dataclass(frozen=True)
class VenueBundle:
    """Resolved venue wiring for live TradingNode construction.

    ``data_config`` / ``exec_config`` / factories are typed ``Any`` because
    NautilusTrader uses separate Binance vs Kraken client config classes with
    no shared base. Pass through to ``TradingNode`` only — do not access
    venue-specific fields on the bundle.
    """

    venue: str
    instrument_id: str
    bar_type: str
    recon_currencies: frozenset[str]
    data_config: Any
    exec_config: Any
    data_factory: Any
    exec_factory: Any

    def strategy_config(self, **overrides: Any) -> dict[str, Any]:
        base = {
            "instrument_id": self.instrument_id,
            "bar_type": self.bar_type,
            "fast_period": 10,
            "slow_period": 30,
            "trade_size": "0.01",
        }
        base.update(overrides)
        return base


def _resolve_recon_currencies(defaults: frozenset[str]) -> frozenset[str]:
    override = recon_cfg.currencies.strip()
    if override:
        return frozenset(c.strip().upper() for c in override.split(",") if c.strip())
    return defaults


def resolve_venue_bundle(venue: str | None = None) -> VenueBundle:
    """Build a venue bundle from TRADE_VENUE and optional overrides."""
    key = (venue or system_cfg.trade_venue or "kraken").upper()
    if key not in VENUE_DEFAULTS:
        raise ValueError(f"Unsupported TRADE_VENUE={key!r}; supported: BINANCE, KRAKEN")

    defaults = VENUE_DEFAULTS[key]
    instrument_id = system_cfg.trade_instrument.strip() or defaults["instrument_id"]
    bar_type = system_cfg.trade_bar_type.strip() or defaults["bar_type"]
    recon_currencies = _resolve_recon_currencies(defaults["recon_currencies"])

    if key == "BINANCE":
        from nautilus_trade.adapters import binance_config

        return VenueBundle(
            venue="BINANCE",
            instrument_id=instrument_id,
            bar_type=bar_type,
            recon_currencies=recon_currencies,
            data_config=binance_config.binance_data_config(),
            exec_config=binance_config.binance_exec_config(),
            data_factory=binance_config.DATA_FACTORY,
            exec_factory=binance_config.EXEC_FACTORY,
        )

    from nautilus_trade.adapters import kraken_config

    return VenueBundle(
        venue="KRAKEN",
        instrument_id=instrument_id,
        bar_type=bar_type,
        recon_currencies=recon_currencies,
        data_config=kraken_config.kraken_data_config(),
        exec_config=kraken_config.kraken_exec_config(),
        data_factory=kraken_config.DATA_FACTORY,
        exec_factory=kraken_config.EXEC_FACTORY,
    )
