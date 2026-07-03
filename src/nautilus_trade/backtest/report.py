"""Post-backtest report utilities.

Loads saved run manifests and produces summary statistics.
Extend with portfolio analytics (Sharpe, Sortino, max drawdown) as needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

MANIFEST_DIR = Path("./runs")


def load_manifests() -> list[dict]:
    """Load all saved backtest manifests."""
    if not MANIFEST_DIR.exists():
        return []
    records = []
    for p in sorted(MANIFEST_DIR.glob("backtest_*.json")):
        records.append(json.loads(p.read_text()))
    return records


def manifests_to_dataframe() -> pd.DataFrame:
    """Return all backtest run manifests as a DataFrame."""
    records = load_manifests()
    return pd.DataFrame(
        [
            {
                "run_id": r["run_id"],
                "tag": r.get("tag", ""),
                "timestamp": r["timestamp"],
            }
            for r in records
        ]
    )


def print_manifest_table() -> None:
    """Print a formatted table of all backtest runs."""
    df = manifests_to_dataframe()
    if df.empty:
        print("No backtest manifests found in", MANIFEST_DIR)
        return
    print(df.to_string(index=False))
