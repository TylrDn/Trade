"""BacktestNode factory and runner.

This module builds and runs deterministic backtests via NautilusTrader's
BacktestNode (config-driven, Parquet catalog–based).

Design rules:
- All backtest configs are serializable and stored with the run manifest.
- The same strategy package used in backtest is promoted to live.
- No live credentials are loaded in research/backtest environments.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import (
    BacktestDataConfig,
    BacktestEngineConfig,
    BacktestRunConfig,
    BacktestVenueConfig,
    ImportableStrategyConfig,
    LoggingConfig,
    RiskEngineConfig,
)
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import Venue

from nautilus_trade.catalog import get_catalog
from nautilus_trade.config import system_cfg

log = logging.getLogger(__name__)

MANIFEST_DIR = Path("./runs")


def build_backtest_config(
    venue_name: str,
    instrument_id: str,
    bar_type: str,
    strategy_path: str,
    strategy_config: dict,
    start: str,
    end: str,
    starting_balance: str = "100000 USDT",
) -> BacktestRunConfig:
    """Build a fully typed BacktestRunConfig from simple parameters."""
    catalog = get_catalog()
    bt = BarType.from_str(bar_type)

    venue_config = BacktestVenueConfig(
        name=venue_name,
        oms_type="NETTING",
        account_type="MARGIN",
        starting_balances=[starting_balance],
    )

    data_config = BacktestDataConfig(
        catalog_path=str(system_cfg.catalog_path),
        data_cls="nautilus_trader.model.data:Bar",
        instrument_id=instrument_id,
        bar_spec=str(bt.spec),
        start_time=start,
        end_time=end,
    )

    engine_config = BacktestEngineConfig(
        strategies=[
            ImportableStrategyConfig(
                strategy_path=strategy_path,
                config_path="",
                config=strategy_config,
            )
        ],
        risk_engine=RiskEngineConfig(bypass=False),
        logging=LoggingConfig(log_level=system_cfg.nautilus_log_level),
    )

    return BacktestRunConfig(
        engine=engine_config,
        venues=[venue_config],
        data=[data_config],
    )


def run_backtest(config: BacktestRunConfig, tag: str = "") -> dict:
    """Run a backtest and save the manifest. Returns run metadata dict."""
    run_id = str(uuid.uuid4())[:8]
    ts = datetime.now(timezone.utc).isoformat()
    log.info("Starting backtest run_id=%s tag=%s", run_id, tag)

    node = BacktestNode(configs=[config])
    results = node.run()

    manifest = {
        "run_id": run_id,
        "tag": tag,
        "timestamp": ts,
        "config": config.json(),
        "results_summary": str(results),
    }

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFEST_DIR / f"backtest_{run_id}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("Backtest complete. Manifest saved: %s", manifest_path)
    return manifest
