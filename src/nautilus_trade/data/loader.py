"""Historical data loader.

Loads external OHLCV data (e.g. from exchange REST or CSV files)
and writes it to the Parquet data catalog in NautilusTrader format.

This is the entry point for populating the catalog before backtesting.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from nautilus_trade.catalog import get_catalog

log = logging.getLogger(__name__)


def load_bars_from_csv(
    csv_path: Path,
    bar_type: str,
    catalog: ParquetDataCatalog | None = None,
) -> int:
    """Load OHLCV bars from a CSV file into the Parquet catalog.

    CSV must have columns: timestamp, open, high, low, close, volume
    where timestamp is a UTC ISO8601 string or Unix nanoseconds.

    Returns the number of bars written.
    """
    cat = catalog or get_catalog()
    bt = BarType.from_str(bar_type)

    log.info("Loading bars from %s into catalog (bar_type=%s)", csv_path, bar_type)
    df = pd.read_csv(csv_path)

    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    bars: list[Bar] = []
    for row in df.itertuples(index=False):
        # NautilusTrader Bar construction requires instrument + precision
        # Use the catalog instrument definition for correct precision
        instrument = cat.instruments(instrument_ids=[str(bt.instrument_id)])
        if not instrument:
            log.error("Instrument %s not in catalog — add it before loading bars", bt.instrument_id)
            return 0

        # Minimal bar construction (extend with full precision handling as needed)
        bar = Bar(
            bar_type=bt,
            open=instrument[0].make_price(row.open),
            high=instrument[0].make_price(row.high),
            low=instrument[0].make_price(row.low),
            close=instrument[0].make_price(row.close),
            volume=instrument[0].make_qty(row.volume),
            ts_event=pd.Timestamp(row.timestamp, tz="UTC").value,
            ts_init=pd.Timestamp(row.timestamp, tz="UTC").value,
        )
        bars.append(bar)

    cat.write_chunk(data=bars)
    log.info("Wrote %d bars to catalog", len(bars))
    return len(bars)
