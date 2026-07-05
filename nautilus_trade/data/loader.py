"""Orchestrate catalog loading from Binance klines."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nautilus_trade.catalog import get_catalog
from nautilus_trade.config import system_cfg
from nautilus_trade.data.binance_history import (
    fetch_klines_page,
    ms_to_iso,
    parse_interval_ms,
)

log = logging.getLogger(__name__)


def load_klines_to_catalog(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    catalog_path: Path | None = None,
) -> int:
    """Download klines and append OHLCV bars to catalog as parquet via pandas staging.

    Returns number of bars written. Writes each API page before fetching the next
    (partial progress preserved on failure — re-run with adjusted start).
    """
    get_catalog(catalog_path)
    cat_path = Path(catalog_path) if catalog_path else system_cfg.catalog_path
    start_ms = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)
    interval_ms = parse_interval_ms(interval)

    total = 0
    cursor = start_ms
    staging_dir = cat_path / "staging_klines"
    staging_dir.mkdir(parents=True, exist_ok=True)

    while cursor < end_ms:
        page = fetch_klines_page(symbol, interval, cursor, end_ms)
        if not page:
            break

        rows = []
        for k in page:
            open_time = int(k[0])
            rows.append(
                {
                    "timestamp": open_time,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "symbol": symbol,
                    "interval": interval,
                }
            )

        df = pd.DataFrame(rows)
        chunk_path = staging_dir / f"{symbol}_{interval}_{cursor}.parquet"
        df.to_parquet(chunk_path, index=False)
        total += len(rows)
        log.info(
            "Wrote kline chunk %s rows (%s → %s)",
            len(rows),
            ms_to_iso(cursor),
            ms_to_iso(int(page[-1][0])),
        )

        last_open = int(page[-1][0])
        cursor = last_open + interval_ms
        if len(page) < 1500:
            break

    log.info("Catalog load complete: %s bars staged under %s", total, staging_dir)
    return total
