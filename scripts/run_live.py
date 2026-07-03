"""Run the live TradingNode.

Usage:
    TRADE_ENV=staging python scripts/run_live.py
    TRADE_ENV=production python scripts/run_live.py

WARNING: Set TRADE_ENV=staging to paper-trade first.
Never run TRADE_ENV=production without completing all promotion gates.
"""

from __future__ import annotations

import logging

from nautilus_trade.adapters.binance_config import (
    DATA_FACTORY,
    EXEC_FACTORY,
    binance_data_config,
    binance_exec_config,
)
from nautilus_trade.config import system_cfg
from nautilus_trade.live.node import build_live_node
from nautilus_trade.ops.metrics import start_metrics_server

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    log.info("Starting live node: env=%s", system_cfg.trade_env.value)

    if system_cfg.is_live:
        log.warning(
            "⚠️  PRODUCTION mode active. Real capital at risk. Ensure all promotion gates passed."
        )

    # Start Prometheus metrics endpoint
    start_metrics_server()

    strategy_configs = [
        {
            "strategy_path": "nautilus_trade.strategies.ema_cross:EmaCrossStrategy",
            "config": {
                "instrument_id": "BTCUSDT-PERP.BINANCE",
                "bar_type": "BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                "fast_period": 10,
                "slow_period": 30,
                "trade_size": "0.01",
            },
        }
    ]

    node = build_live_node(
        venue="BINANCE",
        strategy_configs=strategy_configs,
        data_factory=DATA_FACTORY,
        exec_factory=EXEC_FACTORY,
        data_client_config=binance_data_config(),
        exec_client_config=binance_exec_config(),
    )

    try:
        node.start()
        node.run()
    except KeyboardInterrupt:
        log.info("Shutdown requested")
    finally:
        node.stop()
        node.dispose()
        log.info("Node stopped cleanly")


if __name__ == "__main__":
    main()
