"""Staging environment wiring tests.

These tests verify fail-closed behavior uses real TRADE_ENV=staging wiring,
not monkeypatched properties. Run via `make test-staging` or CI staging job.
"""

from __future__ import annotations

import pytest

from nautilus_trade.config import TradeEnv, system_cfg


@pytest.mark.staging
def test_trade_env_is_staging_when_configured() -> None:
    if system_cfg.trade_env != TradeEnv.STAGING:
        pytest.skip("Requires TRADE_ENV=staging")

    assert not system_cfg.is_research
    assert system_cfg.is_staging
    assert not system_cfg.is_live
