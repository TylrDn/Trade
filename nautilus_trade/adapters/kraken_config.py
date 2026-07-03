"""Kraken adapter configuration factory.

Builds NautilusTrader Kraken client configs from environment-loaded
settings. Kraken support requires nautilus_trader[kraken].
"""

from __future__ import annotations

from nautilus_trader.adapters.kraken.config import (
    KrakenDataClientConfig,
    KrakenExecutionClientConfig,
)
from nautilus_trader.adapters.kraken.factories import (
    KrakenLiveDataClientFactory,
    KrakenLiveExecClientFactory,
)

from nautilus_trade.config import adapter_cfg


def kraken_data_config() -> KrakenDataClientConfig:
    return KrakenDataClientConfig(
        api_key=adapter_cfg.kraken_api_key,
        api_secret=adapter_cfg.kraken_api_secret,
    )


def kraken_exec_config() -> KrakenExecutionClientConfig:
    return KrakenExecutionClientConfig(
        api_key=adapter_cfg.kraken_api_key,
        api_secret=adapter_cfg.kraken_api_secret,
    )


DATA_FACTORY = KrakenLiveDataClientFactory
EXEC_FACTORY = KrakenLiveExecClientFactory
