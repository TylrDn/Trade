"""Reconciliation actor tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("prometheus_client")

from nautilus_trade.adapters.binance_snapshot import VenueSnapshot
from nautilus_trade.live.actors.reconciliation import ReconciliationActorConfig
from nautilus_trade.live.runtime import create_live_runtime


class MockVenueProvider:
    def __init__(self, snapshot: VenueSnapshot) -> None:
        self._snapshot = snapshot

    def fetch(self) -> VenueSnapshot:
        return self._snapshot


class TestReconciliationActor:
    def test_trips_breaker_on_balance_mismatch(self, tmp_path, monkeypatch) -> None:
        pytest.importorskip("nautilus_trader")
        from nautilus_trade.live.actors.reconciliation import ReconciliationActor

        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("recon-run")
        try:
            balance = type("Balance", (), {"total": Decimal("10000")})()
            account = type("Account", (), {"balances": lambda self: {"USDT": balance}})()
            portfolio = type("Portfolio", (), {"accounts": lambda self: [account]})()
            cache = type("Cache", (), {"positions_open": lambda self: []})()

            actor = ReconciliationActor(
                ReconciliationActorConfig(
                    bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                    venue="BINANCE",
                ),
                runtime=runtime,
                venue_provider=MockVenueProvider(
                    VenueSnapshot(
                        balances={"USDT": Decimal("9000")},
                        positions={},
                        status="ok",
                    ),
                ),
            )
            actor.portfolio = portfolio  # type: ignore[attr-defined]
            actor.cache = cache  # type: ignore[attr-defined]
            actor.run_reconciliation("test")

            assert runtime.breaker.is_tripped
            contents = (tmp_path / "events_recon-run.jsonl").read_text()
            assert "reconciliation_failed" in contents
            assert "circuit_breaker_tripped" in contents
        finally:
            runtime.close()

    def test_passes_when_snapshots_match(self, tmp_path, monkeypatch) -> None:
        pytest.importorskip("nautilus_trader")
        from nautilus_trade.live.actors.reconciliation import ReconciliationActor

        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("recon-pass")
        try:
            balance = type("Balance", (), {"total": Decimal("10000")})()
            account = type("Account", (), {"balances": lambda self: {"USDT": balance}})()
            portfolio = type("Portfolio", (), {"accounts": lambda self: [account]})()
            cache = type("Cache", (), {"positions_open": lambda self: []})()

            actor = ReconciliationActor(
                ReconciliationActorConfig(
                    bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                    venue="BINANCE",
                ),
                runtime=runtime,
                venue_provider=MockVenueProvider(
                    VenueSnapshot(
                        balances={"USDT": Decimal("10000")},
                        positions={},
                        status="ok",
                    ),
                ),
            )
            actor.portfolio = portfolio  # type: ignore[attr-defined]
            actor.cache = cache  # type: ignore[attr-defined]
            actor.run_reconciliation("test")

            assert not runtime.breaker.is_tripped
        finally:
            runtime.close()

    def test_fail_closed_on_missing_credentials(self, tmp_path, monkeypatch) -> None:
        pytest.importorskip("nautilus_trader")
        from nautilus_trade.config import system_cfg
        from nautilus_trade.live.actors.reconciliation import ReconciliationActor

        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        monkeypatch.setattr(system_cfg, "is_research", False)
        runtime = create_live_runtime("recon-missing-creds")
        try:
            actor = ReconciliationActor(
                ReconciliationActorConfig(
                    bar_type="BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL",
                    venue="BINANCE",
                ),
                runtime=runtime,
                venue_provider=MockVenueProvider(
                    VenueSnapshot(
                        balances={},
                        positions={},
                        status="missing_credentials",
                        error="missing keys",
                    ),
                ),
            )
            actor.portfolio = type("Portfolio", (), {"accounts": lambda self: []})()
            actor.cache = type("Cache", (), {"positions_open": lambda self: []})()
            actor.run_reconciliation("test")

            assert runtime.breaker.is_tripped
            contents = (tmp_path / "events_recon-missing-creds.jsonl").read_text()
            assert "reconciliation_missing_credentials" in contents
        finally:
            runtime.close()
