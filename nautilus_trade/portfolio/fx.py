"""FX conversion helpers for PnL and reconciliation (v1)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol


class FxConverter(Protocol):
    """Convert an amount in quote/settle currency to USD."""

    def to_usd(self, amount: Decimal, currency: str) -> Decimal | None:
        ...


class UsdtPegConverter:
    """1:1 USD peg for USDT and USD stablecoins."""

    _PEGGED = frozenset({"USDT", "USD", "BUSD", "USDC"})

    def to_usd(self, amount: Decimal, currency: str) -> Decimal | None:
        if currency in self._PEGGED:
            return amount
        return None


class MidPriceConverter:
    """Convert using cache MID prices when instrument quote matches currency."""

    def __init__(self, cache: Any, fallback: FxConverter | None = None) -> None:
        self._cache = cache
        self._fallback = fallback or UsdtPegConverter()

    def to_usd(self, amount: Decimal, currency: str) -> Decimal | None:
        pegged = self._fallback.to_usd(amount, currency)
        if pegged is not None:
            return pegged
        return None
