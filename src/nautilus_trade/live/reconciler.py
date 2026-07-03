"""Live reconciliation checks.

Verifies that NautilusTrader's internal state (orders, positions, balances)
matches what the venue reports after startup and periodically during
operation.

Integrate with TradingNode's on_start lifecycle and a periodic actor
for continuous reconciliation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from nautilus_trade.ops.alerts import send_alert

log = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    passed: bool
    mismatches: list[str]

    def __str__(self) -> str:
        if self.passed:
            return "Reconciliation PASSED"
        return f"Reconciliation FAILED — mismatches: {self.mismatches}"


class LiveReconciler:
    """Compares internal and venue state after startup or reconnect."""

    def check_balances(
        self,
        internal_balances: dict[str, Decimal],
        venue_balances: dict[str, Decimal],
        tolerance: Decimal = Decimal("0.001"),
    ) -> ReconciliationResult:
        """Compare internal vs venue balances within tolerance."""
        mismatches: list[str] = []
        all_currencies = set(internal_balances) | set(venue_balances)
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
        else:
            log.info("Reconciliation passed")
        return result

    def check_positions(
        self,
        internal_positions: dict[str, Decimal],
        venue_positions: dict[str, Decimal],
        tolerance: Decimal = Decimal("0.0001"),
    ) -> ReconciliationResult:
        """Compare internal vs venue positions within tolerance."""
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
        return result
