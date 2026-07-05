"""Emergency flatten script — closes all open positions immediately.

This is an operational runbook script. Run this when:
- Circuit breaker has tripped and positions must be closed
- Manual halt is required
- System is shutting down with open risk

Usage:
    python3 scripts/flatten_all.py --env staging
    python3 scripts/flatten_all.py --env production  # requires double confirmation

WARNING: This submits MARKET orders to flatten all open positions.
Emergency flatten bypasses the ExecutionGateway pre-flight layer.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nautilus_trade.ops.logging_setup import configure_observability


def main() -> None:
    configure_observability()
    parser = argparse.ArgumentParser(description="Emergency flatten all positions")
    parser.add_argument("--env", required=True, choices=["staging", "production"])
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if args.env == "production" and not args.force:
        confirm = input(
            "PRODUCTION flatten. Type 'FLATTEN' to confirm: "
        ).strip()
        if confirm != "FLATTEN":
            print("Flatten cancelled")
            return

    os.environ["TRADE_ENV"] = args.env

    from nautilus_trade.adapters.binance_config import (
        DATA_FACTORY,
        EXEC_FACTORY,
        binance_data_config,
        binance_exec_config,
    )
    from nautilus_trade.live.node import build_flatten_trading_node
    from nautilus_trade.live.runtime import create_live_runtime, unbind_live_runtime

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log = logging.getLogger(__name__)
    log.critical("FLATTEN ALL initiated: env=%s", args.env)

    runtime = create_live_runtime(run_id=f"flatten-{uuid.uuid4().hex[:8]}")
    node = build_flatten_trading_node(
        runtime=runtime,
        venue="BINANCE",
        data_factory=DATA_FACTORY,
        exec_factory=EXEC_FACTORY,
        data_client_config=binance_data_config(),
        exec_client_config=binance_exec_config(),
    )

    try:
        node.start()
        node.run()
    except KeyboardInterrupt:
        log.info("Flatten interrupted")
    finally:
        try:
            node.stop()
        finally:
            node.dispose()
            runtime.close()
            unbind_live_runtime()
        log.info("Flatten node stopped")


if __name__ == "__main__":
    main()
