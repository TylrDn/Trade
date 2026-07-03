"""Shared pytest fixtures — env isolation for the trading system.

Every test runs with `TRADE_ENV=research` and a scratch catalog path so
that no test can accidentally reach a real venue or read a stale local
`.env`.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Force research env + scratch catalog for every test."""
    monkeypatch.setenv("TRADE_ENV", "research")
    monkeypatch.setenv("CATALOG_PATH", str(tmp_path / "catalog"))
    # Nuke live venue creds so a mis-imported adapter cannot connect anywhere.
    for var in (
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
        "SLACK_WEBHOOK_URL",
        "PAGERDUTY_INTEGRATION_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    # Sensible risk defaults for tests.
    monkeypatch.setenv("RISK_MAX_DAILY_LOSS_USD", "500")
    monkeypatch.setenv("RISK_MAX_POSITION_NOTIONAL_USD", "10000")
    monkeypatch.setenv("RISK_MAX_LEVERAGE", "3.0")


@pytest.fixture
def catalog_path(tmp_path: Path) -> Path:
    """Return a scratch catalog path for the test."""
    p = tmp_path / "catalog"
    p.mkdir(parents=True, exist_ok=True)
    return p
