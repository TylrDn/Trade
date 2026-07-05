"""Live reconciliation checks.

Verifies that NautilusTrader's internal state (orders, positions, balances)
matches what the venue reports after startup and periodically during
operation.

Integrate with TradingNode's on_start lifecycle and a periodic actor
for continuous reconciliation.

On mismatch, an alert is sent and the circuit breaker is tripped (when wired).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from nautilus_trade.ops.alerts import send_alert

if TYPE_CHECKING:
    from nautilus_trade.ops.circuit_breaker import CircuitBreaker

log = logging.getLogger(__name__)

TripFn = Callable[[str], None]


@dataclass
class ReconciliationResult:
    passed: bool
    mismatches: list[str]

    def __str__(self) -> str:
        if self.passed:
            return "Reconciliation PASSED"
        return f"Reconciliation FAILED — mismatches: {self.mismatches}"


class LiveReconciler:
    """Compares internal and venue state after startup or reconnect.

    When a ``CircuitBreaker`` is provided, mismatches trip the breaker
    to halt trading until an operator resolves the discrepancy.
    """

    def __init__(
        self,
        breaker: CircuitBreaker | None = None,
        trip_fn: TripFn | None = None,
    ) -> None:
        self._breaker = breaker
        if trip_fn is not None:
            self._trip_fn = trip_fn
        elif breaker is not None:
            self._trip_fn = breaker.trip
        else:
            self._trip_fn = None

    def _trip_breaker(self, reason: str) -> None:
        if self._trip_fn is not None:
            self._trip_fn(reason)

    def check_balances(
        self,
        internal_balances: dict[str, Decimal],
        venue_balances: dict[str, Decimal],
        tolerance: Decimal = Decimal("0.001"),
        currencies: frozenset[str] | None = frozenset({"USDT"}),
    ) -> ReconciliationResult:
        """Compare internal vs venue balances within tolerance.

        Defaults to USDT-only scope to reduce false positives from unused assets.
        On mismatch, sends an alert and trips the circuit breaker (if wired).
        """
        mismatches: list[str] = []
        if currencies is None:
            all_currencies = set(internal_balances) | set(venue_balances)
        else:
            all_currencies = currencies
        for ccy in all_currencies:
            internal = internal_balances.get(ccy, Decimal(0))
            venue = venue_balances.get(ccy, Decimal(0))
            diff = abs(internal - venue)
            if diff > tolerance:
                msg = f"{ccy}: internal={internal} venue={venue} diff={diff}"
                mismatches.append(msg)
                log.warning("Balance mismatch: %s", msg)

        result = ReconciliationResult(passed=not mismatches, mismatches=mismatches)
        if not result.passed:
            send_alert(f"❌ Reconciliation failed: {mismatches}", level="error")
            self._trip_breaker("reconciliation_balance_mismatch")
        else:
            log.info("Reconciliation passed")
        return result

    def check_positions(
        self,
        internal_positions: dict[str, Decimal],
        venue_positions: dict[str, Decimal],
        tolerance: Decimal = Decimal("0.0001"),
    ) -> ReconciliationResult:
        """Compare internal vs venue positions within tolerance.

        On mismatch, sends an alert and trips the circuit breaker (if wired).
        """
        mismatches: list[str] = []
        all_instruments = set(internal_positions) | set(venue_positions)
        for inst in all_instruments:
            internal = internal_positions.get(inst, Decimal(0))
            venue = venue_positions.get(inst, Decimal(0))
            diff = abs(internal - venue)
            if diff > tolerance:
                msg = f"{inst}: internal={internal} venue={venue} diff={diff}"
                mismatches.append(msg)
                log.warning("Position mismatch: %s", msg)

        result = ReconciliationResult(passed=not mismatches, mismatches=mismatches)
        if not result.passed:
            send_alert(f"❌ Position reconciliation failed: {mismatches}", level="error")
            self._trip_breaker("reconciliation_position_mismatch")
        return result

    def check_open_orders(
        self,
        internal_client_ids: frozenset[str],
        venue_client_ids: frozenset[str],
    ) -> ReconciliationResult:
        """Compare open order client IDs between internal cache and venue."""
        missing_at_venue = internal_client_ids - venue_client_ids
        phantom_at_venue = venue_client_ids - internal_client_ids
        mismatches: list[str] = []
        if missing_at_venue:
            mismatches.append(f"missing_at_venue={sorted(missing_at_venue)}")
        if phantom_at_venue:
            mismatches.append(f"phantom_at_venue={sorted(phantom_at_venue)}")

        result = ReconciliationResult(passed=not mismatches, mismatches=mismatches)
        if not result.passed:
            send_alert(f"Open order reconciliation failed: {mismatches}", level="error")
            self._trip_breaker("reconciliation_open_orders_mismatch")
        return result
