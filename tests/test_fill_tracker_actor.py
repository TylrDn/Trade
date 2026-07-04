"""Fill tracker actor fail-closed tests."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("prometheus_client")
pytest.importorskip("nautilus_trader")

from nautilus_trade.live.actors.fill_tracker import FillTrackerActor, FillTrackerConfig
from nautilus_trade.live.runtime import create_live_runtime


def _fill_event() -> SimpleNamespace:
    return SimpleNamespace(
        instrument_id="BTCUSDT-PERP.BINANCE",
        client_order_id="O-1",
        order_side=SimpleNamespace(name="SELL"),
        last_qty="0.01",
        last_px="50000",
        position_id=None,
    )


class TestFillTrackerActorFailClosed:
    def test_unavailable_pnl_trips_in_staging(self, tmp_path, monkeypatch) -> None:
        from nautilus_trade.config import system_cfg

        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        monkeypatch.setattr(system_cfg, "is_research", False)
        runtime = create_live_runtime("fill-fail")
        try:
            actor = FillTrackerActor(
                FillTrackerConfig(instrument_id="BTCUSDT-PERP.BINANCE"),
                runtime=runtime,
            )
            actor.cache = SimpleNamespace(
                position=lambda _pid: None,
                position_for_instrument=lambda _iid: None,
                positions_open=lambda: [],
            )
            actor.portfolio = SimpleNamespace(accounts=lambda: [])

            actor.on_order_filled(_fill_event())  # type: ignore[arg-type]

            assert runtime.breaker.is_tripped
            assert runtime.risk_engine.pnl_tracking_degraded
            assert runtime.risk_engine.daily.realized_pnl_usd == Decimal(0)
            contents = (tmp_path / "events_fill-fail.jsonl").read_text()
            assert "fill_pnl_unavailable" in contents
        finally:
            runtime.close()

    def test_unavailable_pnl_does_not_trip_in_research(self, tmp_path, monkeypatch) -> None:
        from nautilus_trade.config import system_cfg

        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        monkeypatch.setattr(system_cfg, "is_research", True)
        runtime = create_live_runtime("fill-research")
        try:
            actor = FillTrackerActor(
                FillTrackerConfig(instrument_id="BTCUSDT-PERP.BINANCE"),
                runtime=runtime,
            )
            actor.cache = SimpleNamespace(
                position=lambda _pid: None,
                position_for_instrument=lambda _iid: None,
                positions_open=lambda: [],
            )
            actor.portfolio = SimpleNamespace(accounts=lambda: [])

            actor.on_order_filled(_fill_event())  # type: ignore[arg-type]

            assert not runtime.breaker.is_tripped
            assert not runtime.risk_engine.pnl_tracking_degraded
        finally:
            runtime.close()
