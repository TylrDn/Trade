"""Reconciler tests."""

from __future__ import annotations

from decimal import Decimal

from nautilus_trade.live.reconciler import LiveReconciler


class TestLiveReconciler:
    def test_balance_reconciliation_passes_when_matching(self) -> None:
        rec = LiveReconciler()
        result = rec.check_balances(
            internal_balances={"USDT": Decimal("10000"), "BTC": Decimal("0.5")},
            venue_balances={"USDT": Decimal("10000"), "BTC": Decimal("0.5")},
        )
        assert result.passed
        assert result.mismatches == []

    def test_balance_reconciliation_fails_on_mismatch(self) -> None:
        rec = LiveReconciler()
        result = rec.check_balances(
            internal_balances={"USDT": Decimal("10000")},
            venue_balances={"USDT": Decimal("9000")},  # $1000 mismatch
            tolerance=Decimal("0.01"),
        )
        assert not result.passed
        assert len(result.mismatches) == 1
        assert "USDT" in result.mismatches[0]

    def test_balance_reconciliation_passes_within_tolerance(self) -> None:
        rec = LiveReconciler()
        result = rec.check_balances(
            internal_balances={"BTC": Decimal("0.50000")},
            venue_balances={"BTC": Decimal("0.50001")},
            tolerance=Decimal("0.001"),
        )
        assert result.passed

    def test_position_reconciliation_passes_when_matching(self) -> None:
        rec = LiveReconciler()
        result = rec.check_positions(
            internal_positions={"BTCUSDT-PERP.BINANCE": Decimal("0.1")},
            venue_positions={"BTCUSDT-PERP.BINANCE": Decimal("0.1")},
        )
        assert result.passed

    def test_position_reconciliation_detects_phantom_position(self) -> None:
        rec = LiveReconciler()
        result = rec.check_positions(
            internal_positions={},  # Internal thinks flat
            venue_positions={"BTCUSDT-PERP.BINANCE": Decimal("0.05")},  # Venue has position
            tolerance=Decimal("0.0001"),
        )
        assert not result.passed

    def test_str_representation(self) -> None:
        rec = LiveReconciler()
        result = rec.check_balances(
            internal_balances={"USDT": Decimal("100")},
            venue_balances={"USDT": Decimal("100")},
        )
        assert "PASSED" in str(result)
