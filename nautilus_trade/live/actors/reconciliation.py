"""Periodic reconciliation actor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nautilus_trader.config import ActorConfig
from nautilus_trader.trading.actor import Actor

from nautilus_trade.adapters.binance_snapshot import VenueSnapshot, VenueSnapshotProvider
from nautilus_trade.config import system_cfg
from nautilus_trade.live.portfolio_snapshot import (
    extract_internal_balances,
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

    def on_start(self) -> None:
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

    def _run_reconciliation(self, phase: str) -> None:
        snapshot = self._venue_provider.fetch()
        if snapshot.status != "ok":
            self._handle_snapshot_failure(phase, snapshot)
            return

        internal_balances = extract_internal_balances(self.portfolio)
        internal_positions = extract_internal_positions(self.cache)

        balance_result = self._runtime.reconciler.check_balances(
            internal_balances,
            snapshot.balances,
        )
        position_result = self._runtime.reconciler.check_positions(
            internal_positions,
            snapshot.positions,
        )

        if not balance_result.passed or not position_result.passed:
            self._runtime.event_store.record(
                "reconciliation_failed",
                {
                    "phase": phase,
                    "balance_mismatches": balance_result.mismatches,
                    "position_mismatches": position_result.mismatches,
                },
            )

        log.info(
            "Reconciliation %s complete: balances=%s positions=%s",
            phase,
            "PASS" if balance_result.passed else "FAIL",
            "PASS" if position_result.passed else "FAIL",
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
