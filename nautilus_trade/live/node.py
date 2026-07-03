"""TradingNode factory for live and paper environments.

Builds a NautilusTrader TradingNode with:
- Venue adapters (Binance or Kraken)
- Strategies wired from config
- Risk engine and portfolio controls
- Observability hooks

The same strategy package validated in BacktestNode is used here with
no code changes — only venue configs differ.
"""

from __future__ import annotations

import logging

from nautilus_trader.config import (
    ImportableStrategyConfig,
    LiveDataEngineConfig,
    LiveExecEngineConfig,
    LiveRiskEngineConfig,
    LoggingConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode

from nautilus_trade.config import adapter_cfg, system_cfg

log = logging.getLogger(__name__)


def build_live_node(
    venue: str,
    strategy_configs: list[dict],
    data_factory,
    exec_factory,
    data_client_config,
    exec_client_config,
) -> TradingNode:
    """Build a fully configured TradingNode for the target venue."""
    log.info(
        "Building TradingNode: env=%s venue=%s",
        system_cfg.trade_env.value,
        venue,
    )

    strategies = [
        ImportableStrategyConfig(
            strategy_path=s["strategy_path"],
            config_path="",
            config=s["config"],
        )
        for s in strategy_configs
    ]

    node_config = TradingNodeConfig(
        trader_id=f"TRADER-{venue}-001",
        data_clients={venue: data_client_config},
        exec_clients={venue: exec_client_config},
        strategies=strategies,
        data_engine=LiveDataEngineConfig(debug=False),
        risk_engine=LiveRiskEngineConfig(bypass=False),  # Always enforce risk in live
        exec_engine=LiveExecEngineConfig(),
        logging=LoggingConfig(
            log_level=system_cfg.nautilus_log_level,
            log_level_file="DEBUG",
            log_file_path=f"./logs/{venue.lower()}_live.log",
        ),
    )

    node = TradingNode(config=node_config)
    node.add_data_client_factory(venue, data_factory)
    node.add_exec_client_factory(venue, exec_factory)
    node.build()
    return node
