"""Parquet data catalog management.

All historical data lives here. The same catalog is used for backtesting
and for pre-loading reference data into live nodes.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from nautilus_trader.persistence.catalog import ParquetDataCatalog

from nautilus_trade.config import system_cfg

log = logging.getLogger(__name__)


def get_catalog(path: Path | None = None) -> ParquetDataCatalog:
    """Return the Parquet data catalog at the configured path."""
    catalog_path = path or system_cfg.catalog_path
    catalog_path.mkdir(parents=True, exist_ok=True)
    log.info("Opening data catalog at %s", catalog_path)
    return ParquetDataCatalog(str(catalog_path))


def catalog_summary(catalog: ParquetDataCatalog) -> pd.DataFrame:
    """Return a summary DataFrame of what's in the catalog."""
    instruments = catalog.instruments()
    rows = []
    for inst in instruments:
        rows.append(
            {
                "instrument_id": str(inst.id),
                "asset_class": str(inst.asset_class),
                "symbol": str(inst.symbol),
            }
        )
    return pd.DataFrame(rows)
