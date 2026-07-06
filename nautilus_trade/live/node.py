"""TradingNode factory for live and paper environments.

Builds a NautilusTrader TradingNode with the shared LiveRuntime safety
envelope: gateway injection, feed health, regime filter, fill tracking,
and periodic reconciliation.
"""

from __future__ import annotations

import logging
from typing import Any

from nautilus_trader.config import (
    ImportableActorConfig,
    ImportableStrategyConfig,
    LiveDataEngineConfig,
    LiveExecEngineConfig,
    LiveRiskEngineConfig,
    LoggingConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode

from nautilus_trade.config import recon_cfg, system_cfg
from nautilus_trade.live.runtime import LiveRuntime, bind_live_runtime, unbind_live_runtime

log = logging.getLogger(__name__)


def build_live_trading_node(
    runtime: LiveRuntime,
    venue: str,
    strategy_specs: list[dict[str, Any]],
    data_factory: Any,
    exec_factory: Any,
    data_client_config: Any,
    exec_client_config: Any,
    recon_currencies: frozenset[str] | None = None,
) -> TradingNode:
    """Build a TradingNode with the shared live runtime safety envelope."""
    if not strategy_specs:
        raise ValueError("At least one strategy spec is required")

    primary = strategy_specs[0]["config"]
    bar_type = primary["bar_type"]
    instrument_id = primary["instrument_id"]

    log.info(
        "Building live TradingNode: env=%s venue=%s run_id=%s",
        system_cfg.trade_env.value,
        venue,
        runtime.run_id,
    )

    if not recon_currencies:
        raise ValueError(
            "recon_currencies is required — pass VenueBundle.recon_currencies "
            "from resolve_venue_bundle()"
        )
    currencies_tuple = tuple(sorted(recon_currencies))

    strategies = [
        ImportableStrategyConfig(
            strategy_path="nautilus_trade.live.factories:create_ema_cross_strategy",
            config_path="nautilus_trade.strategies.ema_cross:EmaCrossConfig",
            config=spec["config"],
        )
        for spec in strategy_specs
    ]

    actors = [
        ImportableActorConfig(
            actor_path="nautilus_trade.actors.regime_filter:RegimeFilterActor",
            config_path="nautilus_trade.actors.regime_filter:RegimeFilterConfig",
            config={"bar_type": bar_type},
        ),
        ImportableActorConfig(
            actor_path="nautilus_trade.live.factories:create_feed_health_guard",
            config_path="nautilus_trade.actors.feed_health:FeedHealthGuardConfig",
            config={"bar_type": bar_type},
        ),
        ImportableActorConfig(
            actor_path="nautilus_trade.live.factories:create_fill_tracker",
            config_path="nautilus_trade.live.actors.fill_tracker:FillTrackerConfig",
            config={"instrument_id": instrument_id},
        ),
        ImportableActorConfig(
            actor_path="nautilus_trade.live.factories:create_reconciliation_actor",
            config_path="nautilus_trade.live.actors.reconciliation:ReconciliationActorConfig",
            config={
                "bar_type": bar_type,
                "venue": venue,
                "startup_delay_seconds": recon_cfg.startup_delay_seconds,
                "currencies": currencies_tuple,
            },
        ),
    ]

    node_config = TradingNodeConfig(
        trader_id=f"TRADER-{venue}-001",
        data_clients={venue: data_client_config},
        exec_clients={venue: exec_client_config},
        strategies=strategies,
        actors=actors,
        data_engine=LiveDataEngineConfig(debug=False),
        risk_engine=LiveRiskEngineConfig(bypass=False),
        exec_engine=LiveExecEngineConfig(reconciliation=True),
        logging=LoggingConfig(
            log_level=system_cfg.nautilus_log_level,
            log_level_file="DEBUG",
            log_file_path=f"./logs/{venue.lower()}_live.log",
        ),
    )

    bind_live_runtime(runtime)
    try:
        node = TradingNode(config=node_config)
        node.add_data_client_factory(venue, data_factory)
        node.add_exec_client_factory(venue, exec_factory)
        node.build()
    except Exception:
        unbind_live_runtime()
        raise

    return node


def build_live_node(
    venue: str,
    strategy_configs: list[dict[str, Any]],
    data_factory: Any,
    exec_factory: Any,
    data_client_config: Any,
    exec_client_config: Any,
    runtime: LiveRuntime | None = None,
    recon_currencies: frozenset[str] | None = None,
) -> TradingNode:
    """Backward-compatible wrapper requiring an explicit LiveRuntime."""
    if runtime is None:
        raise ValueError(
            "build_live_node requires a LiveRuntime; use create_live_runtime() and "
            "build_live_trading_node() instead"
        )
    return build_live_trading_node(
        runtime=runtime,
        venue=venue,
        strategy_specs=strategy_configs,
        data_factory=data_factory,
        exec_factory=exec_factory,
        data_client_config=data_client_config,
        exec_client_config=exec_client_config,
        recon_currencies=recon_currencies,
    )


def build_flatten_trading_node(
    runtime: LiveRuntime,
    venue: str,
    data_factory: Any,
    exec_factory: Any,
    data_client_config: Any,
    exec_client_config: Any,
) -> TradingNode:
    """Build a minimal TradingNode that closes all open positions on start."""
    log.info(
        "Building flatten TradingNode: env=%s venue=%s run_id=%s",
        system_cfg.trade_env.value,
        venue,
        runtime.run_id,
    )

    strategies = [
        ImportableStrategyConfig(
            strategy_path="nautilus_trade.live.factories:create_flatten_strategy",
            config_path="nautilus_trade.live.flatten:FlattenConfig",
            config={},
        )
    ]

    node_config = TradingNodeConfig(
        trader_id=f"TRADER-{venue}-FLATTEN",
        data_clients={venue: data_client_config},
        exec_clients={venue: exec_client_config},
        strategies=strategies,
        data_engine=LiveDataEngineConfig(debug=False),
        risk_engine=LiveRiskEngineConfig(bypass=False),
        exec_engine=LiveExecEngineConfig(reconciliation=True),
        logging=LoggingConfig(
            log_level=system_cfg.nautilus_log_level,
            log_level_file="DEBUG",
            log_file_path=f"./logs/{venue.lower()}_flatten.log",
        ),
    )

    bind_live_runtime(runtime)
    try:
        node = TradingNode(config=node_config)
        node.add_data_client_factory(venue, data_factory)
        node.add_exec_client_factory(venue, exec_factory)
        node.build()
    except Exception:
        unbind_live_runtime()
        raise

    return node
