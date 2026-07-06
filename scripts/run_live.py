"""Run the live TradingNode with the shared safety envelope.

Usage:
    TRADE_ENV=staging python3 scripts/run_live.py
    TRADE_ENV=production python3 scripts/run_live.py

WARNING: Set TRADE_ENV=staging to paper-trade first.
Never run TRADE_ENV=production without completing all promotion gates.
"""

from __future__ import annotations

import logging
import uuid

from nautilus_trade.adapters.venue_registry import resolve_venue_bundle
from nautilus_trade.config import system_cfg
from nautilus_trade.live.node import build_live_trading_node
from nautilus_trade.live.runtime import create_live_runtime, unbind_live_runtime
from nautilus_trade.ops.logging_setup import configure_observability
from nautilus_trade.ops.metrics import start_metrics_server

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    configure_observability()
    bundle = resolve_venue_bundle()
    log.info("Starting live node: env=%s venue=%s", system_cfg.trade_env.value, bundle.venue)

    if system_cfg.is_live:
        log.warning(
            "PRODUCTION mode active. Real capital at risk. Ensure all promotion gates passed."
        )

    start_metrics_server()
    runtime = create_live_runtime(run_id=str(uuid.uuid4())[:8])

    node = build_live_trading_node(
        runtime=runtime,
        venue=bundle.venue,
        strategy_specs=[{"config": bundle.strategy_config()}],
        data_factory=bundle.data_factory,
        exec_factory=bundle.exec_factory,
        data_client_config=bundle.data_config,
        exec_client_config=bundle.exec_config,
        recon_currencies=bundle.recon_currencies,
    )

    try:
        node.start()
        node.run()
    except KeyboardInterrupt:
        log.info("Shutdown requested")
    finally:
        try:
            node.stop()
        finally:
            node.dispose()
            runtime.close()
            unbind_live_runtime()
        log.info("Node stopped cleanly")


if __name__ == "__main__":
    main()
