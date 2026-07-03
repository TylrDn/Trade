"""Run a configured backtest.

Usage:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --tag my_experiment
"""

from __future__ import annotations

import argparse
import logging

from nautilus_trade.backtest.node import build_backtest_config, run_backtest
from nautilus_trade.backtest.report import print_manifest_table

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

# ── Default configuration ─────────────────────────────────────────────────────
# Modify these defaults or pass a JSON config file for production use
DEFAULT_VENUE = "BINANCE"
DEFAULT_INSTRUMENT = "BTCUSDT-PERP.BINANCE"
DEFAULT_BAR_TYPE = "BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL"
DEFAULT_START = "2024-01-01"
DEFAULT_END = "2025-01-01"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NautilusTrader backtest")
    parser.add_argument("--tag", default="", help="Optional run label")
    parser.add_argument("--list", action="store_true", help="List previous runs")
    args = parser.parse_args()

    if args.list:
        print_manifest_table()
        return

    config = build_backtest_config(
        venue_name=DEFAULT_VENUE,
        instrument_id=DEFAULT_INSTRUMENT,
        bar_type=DEFAULT_BAR_TYPE,
        strategy_path="nautilus_trade.strategies.ema_cross:EmaCrossStrategy",
        strategy_config={
            "instrument_id": DEFAULT_INSTRUMENT,
            "bar_type": DEFAULT_BAR_TYPE,
            "fast_period": 10,
            "slow_period": 30,
            "trade_size": "0.01",
        },
        start=DEFAULT_START,
        end=DEFAULT_END,
        starting_balance="100000 USDT",
    )

    manifest = run_backtest(config, tag=args.tag)
    log.info("Run complete: run_id=%s", manifest["run_id"])


if __name__ == "__main__":
    main()
