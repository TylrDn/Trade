#!/usr/bin/env python3
"""Load historical Binance USDT-M klines into the catalog staging area.

Recommend --start/--end ranges of 30 days or less per invocation for v1.
If download aborts, re-run with --start set to the last written bar timestamp.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from nautilus_trade.data.loader import load_klines_to_catalog

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

EPILOG = """
v1 partial-download behavior:
  Each API page is written before the next request. If the run aborts mid-range,
  already-written parquet chunks remain under catalog/staging_klines/. There is no
  automatic resume cursor — re-run with an adjusted --start from the last bar time.

  Recommended: keep each invocation to <= 30 days of 1m bars.
"""


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load Binance klines into catalog staging",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--venue", choices=["binance", "kraken"], default="binance")
    parser.add_argument("--symbol", default=None, help="Venue symbol (default: BTCUSDT or PF_XBTUSD)")
    parser.add_argument("--interval", default="1m", help="Kline interval")
    parser.add_argument("--start", required=True, help="ISO start datetime (UTC)")
    parser.add_argument("--end", required=True, help="ISO end datetime (UTC)")
    parser.add_argument("--catalog-path", default="./catalog", help="Catalog path")
    args = parser.parse_args()

    if args.venue == "kraken":
        raise SystemExit(
            "Kraken catalog loader (Phase 9) is not implemented yet. Use --venue binance."
        )

    start = _parse_dt(args.start)
    end = _parse_dt(args.end)
    symbol = args.symbol or "BTCUSDT"
    count = load_klines_to_catalog(
        symbol=symbol,
        interval=args.interval,
        start=start,
        end=end,
    )
    log.info("Loaded %s bars for %s", count, symbol)


if __name__ == "__main__":
    main()
