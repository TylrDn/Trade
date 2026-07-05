"""Periodic reconciliation actor."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from nautilus_trader.config import ActorConfig
from nautilus_trader.trading.actor import Actor

from nautilus_trade.adapters.binance_instruments import (
    map_binance_positions,
    mapping_warnings_for_positions,
)
from nautilus_trade.adapters.binance_snapshot import VenueSnapshot, VenueSnapshotProvider
from nautilus_trade.config import recon_cfg, system_cfg
from nautilus_trade.live.portfolio_snapshot import (
    extract_internal_balances,
    extract_internal_open_order_client_ids,
    extract_internal_positions,
)

if TYPE_CHECKING:
    from nautilus_trade.live.runtime import LiveRuntime

log = logging.getLogger(__name__)

_STARTUP_TIMER = "reconciliation_startup"
_PERIODIC_TIMER = "reconciliation_periodic"


class ReconciliationActorConfig(ActorConfig, frozen=True):
    bar_type: str
    venue: str = "BINANCE"
    interval_seconds: int = 60
    startup_delay_seconds: int = 15


class ReconciliationActor(Actor):
    """Runs startup and periodic venue reconciliation checks."""

    def __init__(
        self,
        config: ReconciliationActorConfig,
        runtime: LiveRuntime,
        venue_provider: VenueSnapshotProvider,
    ) -> None:
        super().__init__(config)
        self.cfg = config
        self._runtime = runtime
        self._venue_provider = venue_provider
        self._started_at_ns: int | None = None
        self._startup_timing_recorded = False

    def on_start(self) -> None:
        self._started_at_ns = self.clock.timestamp_ns()
        self.clock.set_timer(
            name=_STARTUP_TIMER,
            interval=self.cfg.startup_delay_seconds,
            callback=self._on_startup_timer,
        )
        self.clock.set_timer(
            name=_PERIODIC_TIMER,
            interval=self.cfg.interval_seconds,
            callback=self._on_periodic_timer,
        )
        log.info(
            "ReconciliationActor started venue=%s bar=%s (startup=%ss, interval=%ss)",
            self.cfg.venue,
            self.cfg.bar_type,
            self.cfg.startup_delay_seconds,
            self.cfg.interval_seconds,
        )

    def _on_startup_timer(self, _event: object) -> None:
        self._run_reconciliation("startup")

    def _on_periodic_timer(self, _event: object) -> None:
        self._run_reconciliation("periodic")

    def _resolve_venue_positions(self, snapshot: VenueSnapshot) -> dict[str, Decimal]:
        if snapshot.raw_positions:
            return map_binance_positions(snapshot.raw_positions, self.cache)
        return snapshot.positions

    def _run_reconciliation(self, phase: str) -> None:
        if phase == "startup" and not self._startup_timing_recorded:
            started_at_ns = self._started_at_ns
            if started_at_ns is None:
                started_at_ns = self.clock.timestamp_ns()
            elapsed_seconds = (self.clock.timestamp_ns() - started_at_ns) / 1e9
            log.info(
                "Reconciliation startup timing: elapsed=%.2fs configured_delay=%ss",
                elapsed_seconds,
                self.cfg.startup_delay_seconds,
            )
            self._runtime.event_store.record(
                "reconciliation_startup_timing",
                {
                    "phase": phase,
                    "elapsed_seconds": elapsed_seconds,
                    "configured_delay_seconds": self.cfg.startup_delay_seconds,
                },
            )
            self._startup_timing_recorded = True

        snapshot = self._venue_provider.fetch()
        if snapshot.status != "ok":
            self._handle_snapshot_failure(phase, snapshot)
            return

        venue_positions = self._resolve_venue_positions(snapshot)
        mapping_warnings = mapping_warnings_for_positions(venue_positions, self.cache)
        if mapping_warnings:
            self._runtime.event_store.record(
                "reconciliation_mapping_warning",
                {"phase": phase, "warnings": mapping_warnings},
            )
            log.warning("Reconciliation mapping warnings (%s): %s", phase, mapping_warnings)
            if not system_cfg.is_research and venue_positions:
                self._runtime.record_breaker_trip("reconciliation_mapping_mismatch")
                return

        internal_balances = extract_internal_balances(self.portfolio)
        internal_positions = extract_internal_positions(self.cache)
        internal_open_orders = extract_internal_open_order_client_ids(self.cache)
        recon_currencies = frozenset(
            c.strip().upper() for c in recon_cfg.currencies.split(",") if c.strip()
        )

        balance_result = self._runtime.reconciler.check_balances(
            internal_balances,
            snapshot.balances,
            currencies=recon_currencies,
        )
        position_result = self._runtime.reconciler.check_positions(
            internal_positions,
            venue_positions,
        )
        open_orders_result = self._runtime.reconciler.check_open_orders(
            internal_open_orders,
            snapshot.open_order_client_ids,
        )

        if not balance_result.passed or not position_result.passed:
            payload = {
                "phase": phase,
                "balance_mismatches": balance_result.mismatches,
                "position_mismatches": position_result.mismatches,
            }
            if balance_result.mismatches and "USDT" in snapshot.balance_details:
                payload["usdt_balance_details"] = snapshot.balance_details["USDT"]
            self._runtime.event_store.record("reconciliation_failed", payload)

        if not open_orders_result.passed:
            self._runtime.event_store.record(
                "reconciliation_open_orders_mismatch",
                {"phase": phase, "mismatches": open_orders_result.mismatches},
            )
            if not system_cfg.is_research:
                self._runtime.record_breaker_trip("reconciliation_open_orders_mismatch")

        all_passed = (
            balance_result.passed
            and position_result.passed
            and open_orders_result.passed
        )
        if all_passed:
            self._runtime.event_store.record(
                "reconciliation_ok",
                {
                    "phase": phase,
                    "balances": "PASS",
                    "positions": "PASS",
                    "open_orders": "PASS",
                },
            )

        log.info(
            "Reconciliation %s complete: balances=%s positions=%s open_orders=%s",
            phase,
            "PASS" if balance_result.passed else "FAIL",
            "PASS" if position_result.passed else "FAIL",
            "PASS" if open_orders_result.passed else "FAIL",
        )

    def _handle_snapshot_failure(self, phase: str, snapshot: VenueSnapshot) -> None:
        if snapshot.status == "missing_credentials":
            event_type = "reconciliation_missing_credentials"
            trip_reason = "reconciliation_missing_credentials"
            log.critical(
                "Reconciliation aborted (%s): missing Binance credentials",
                phase,
            )
        else:
            event_type = "reconciliation_fetch_failed"
            trip_reason = "reconciliation_fetch_failed"
            log.error(
                "Reconciliation aborted (%s): venue fetch failed: %s",
                phase,
                snapshot.error,
            )

        self._runtime.event_store.record(
            event_type,
            {"phase": phase, "error": snapshot.error or snapshot.status},
        )

        if not system_cfg.is_research:
            self._runtime.record_breaker_trip(trip_reason)

    def run_reconciliation(self, phase: str = "manual") -> None:
        """Run reconciliation immediately. Exposed for testing."""
        self._run_reconciliation(phase)
