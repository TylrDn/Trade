"""Live runtime composition tests.

Requires prometheus_client for full execution; skipped cleanly in minimal
environments without that dependency.
"""

from __future__ import annotations

import pytest

pytest.importorskip("prometheus_client")

from decimal import Decimal

from nautilus_trade.live.runtime import (
    bind_live_runtime,
    bound_live_runtime,
    create_live_runtime,
    get_live_runtime,
    unbind_live_runtime,
)


class TestLiveRuntime:
    def test_shared_breaker_across_components(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("test-run")
        try:
            assert runtime.gateway.breaker is runtime.breaker
            assert runtime.risk_engine.breaker is runtime.breaker
            assert runtime.reconciler._breaker is runtime.breaker
        finally:
            runtime.close()

    def test_record_breaker_trip_persists_event(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("audit-run")
        try:
            runtime.record_breaker_trip("test_trip")
            assert runtime.breaker.is_tripped
            contents = (tmp_path / "events_audit-run.jsonl").read_text()
            assert "circuit_breaker_tripped" in contents
            assert "test_trip" in contents
        finally:
            runtime.close()

    def test_bind_and_unbind_runtime(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("bind-run")
        try:
            bind_live_runtime(runtime)
            assert get_live_runtime() is runtime
            unbind_live_runtime()
            with pytest.raises(RuntimeError, match="not bound"):
                get_live_runtime()
        finally:
            runtime.close()

    def test_double_bind_raises(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("double-bind")
        try:
            bind_live_runtime(runtime)
            with pytest.raises(RuntimeError, match="already bound"):
                bind_live_runtime(runtime)
        finally:
            unbind_live_runtime()
            runtime.close()

    def test_bound_live_runtime_context_manager(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("ctx-run")
        try:
            with bound_live_runtime(runtime):
                assert get_live_runtime() is runtime
            with pytest.raises(RuntimeError, match="not bound"):
                get_live_runtime()
        finally:
            runtime.close()

    def test_reconciler_uses_shared_audit_trip_fn(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("recon-trip")
        try:
            runtime.reconciler.check_balances(
                internal_balances={"USDT": Decimal("100")},
                venue_balances={"USDT": Decimal("50")},
                tolerance=Decimal("0.01"),
            )
            assert runtime.breaker.is_tripped
            contents = (tmp_path / "events_recon-trip.jsonl").read_text()
            assert "circuit_breaker_tripped" in contents
        finally:
            runtime.close()

    def test_reset_breaker_persists_event(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("nautilus_trade.ops.event_store.EVENT_LOG_DIR", tmp_path)
        runtime = create_live_runtime("reset-run")
        try:
            runtime.record_breaker_trip("test_trip")
            runtime.reset_breaker("operator")
            assert not runtime.breaker.is_tripped
            contents = (tmp_path / "events_reset-run.jsonl").read_text()
            assert "circuit_breaker_reset" in contents
            assert "operator" in contents
        finally:
            runtime.close()
