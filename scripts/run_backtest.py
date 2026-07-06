"""Run a configured backtest.

Usage:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --tag my_experiment
"""

from __future__ import annotations

import argparse
import logging

from nautilus_trade.adapters.venue_registry import resolve_venue_bundle
from nautilus_trade.backtest.node import build_backtest_config, run_backtest
from nautilus_trade.backtest.report import print_manifest_table
from nautilus_trade.ops.logging_setup import configure_observability

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

DEFAULT_START = "2024-01-01"
DEFAULT_END = "2025-01-01"


def main() -> None:
    configure_observability()
    parser = argparse.ArgumentParser(description="Run NautilusTrader backtest")
    parser.add_argument("--tag", default="", help="Optional run label")
    parser.add_argument("--list", action="store_true", help="List previous runs")
    args = parser.parse_args()

    if args.list:
        print_manifest_table()
        return

    bundle = resolve_venue_bundle()
    strategy_config = bundle.strategy_config()
    starting_balance = "100000 USD" if bundle.venue == "KRAKEN" else "100000 USDT"

    config = build_backtest_config(
        venue_name=bundle.venue,
        instrument_id=bundle.instrument_id,
        bar_type=bundle.bar_type,
        strategy_path="nautilus_trade.strategies.ema_cross:EmaCrossStrategy",
        strategy_config=strategy_config,
        start=DEFAULT_START,
        end=DEFAULT_END,
        starting_balance=starting_balance,
    )

    manifest = run_backtest(config, tag=args.tag)
    log.info("Run complete: run_id=%s", manifest["run_id"])


if __name__ == "__main__":
    main()
