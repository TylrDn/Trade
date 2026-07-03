"""Binance adapter configuration factory.

Builds NautilusTrader BinanceDataClientConfig and
BinanceExecutionClientConfig from environment-loaded settings.

Testnet mode is default; set BINANCE_TESTNET=false in .env for live.
"""

from __future__ import annotations

from nautilus_trader.adapters.binance.config import (
    BinanceDataClientConfig,
    BinanceExecutionClientConfig,
)
from nautilus_trader.adapters.binance.factories import (
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory,
)

from nautilus_trade.config import adapter_cfg


def binance_data_config() -> BinanceDataClientConfig:
    return BinanceDataClientConfig(
        api_key=adapter_cfg.binance_api_key,
        api_secret=adapter_cfg.binance_api_secret,
        is_testnet=adapter_cfg.binance_testnet,
    )


def binance_exec_config() -> BinanceExecutionClientConfig:
    return BinanceExecutionClientConfig(
        api_key=adapter_cfg.binance_api_key,
        api_secret=adapter_cfg.binance_api_secret,
        is_testnet=adapter_cfg.binance_testnet,
    )


DATA_FACTORY = BinanceLiveDataClientFactory
EXEC_FACTORY = BinanceLiveExecClientFactory
