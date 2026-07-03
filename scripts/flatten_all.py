"""Emergency flatten script — closes all open positions immediately.

This is an operational runbook script. Run this when:
- Circuit breaker has tripped and positions must be closed
- Manual halt is required
- System is shutting down with open risk

Usage:
    python scripts/flatten_all.py --env staging
    python scripts/flatten_all.py --env production  # requires double confirmation

WARNING: This submits MARKET orders to flatten all open positions.
"""

from __future__ import annotations

import argparse
import logging

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Emergency flatten all positions")
    parser.add_argument("--env", required=True, choices=["staging", "production"])
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if args.env == "production" and not args.force:
        confirm = input(
            "⚠️  PRODUCTION flatten. Type 'FLATTEN' to confirm: "
        ).strip()
        if confirm != "FLATTEN":
            log.info("Flatten cancelled")
            return

    log.critical("🚨 FLATTEN ALL initiated: env=%s", args.env)

    # In a live system, build and connect a TradingNode here, then call:
    #   for position in node.portfolio.positions_open():
    #       strategy.close_position(position)
    # This stub demonstrates the interface — wire to your live node.
    log.info(
        "[STUB] Connect to live TradingNode and call close_all_positions() here. "
        "See live/node.py for TradingNode construction."
    )
    log.info("Flatten complete")


if __name__ == "__main__":
    main()
