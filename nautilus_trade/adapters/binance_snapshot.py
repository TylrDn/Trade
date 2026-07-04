"""Independent Binance futures snapshot for application-layer reconciliation."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Protocol
from urllib.parse import urlencode

import httpx

from nautilus_trade.adapters.binance_instruments import binance_symbol_to_instrument_id
from nautilus_trade.config import adapter_cfg

log = logging.getLogger(__name__)

SnapshotStatus = Literal["ok", "missing_credentials", "fetch_error"]


@dataclass(frozen=True)
class VenueSnapshot:
    """Venue balances and positions with explicit fetch status."""

    balances: dict[str, Decimal]
    positions: dict[str, Decimal]
    status: SnapshotStatus
    error: str | None = None
    raw_positions: dict[str, Decimal] = field(default_factory=dict)
    balance_details: dict[str, dict[str, str]] = field(default_factory=dict)


class VenueSnapshotProvider(Protocol):
    """Fetch venue balances and positions for reconciliation."""

    def fetch(self) -> VenueSnapshot:
        """Return venue snapshot with explicit status."""
        ...


class BinanceVenueSnapshotProvider:
    """Fetch Binance USDT-M futures account state via signed REST."""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        testnet: bool | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else adapter_cfg.binance_api_key
        self._api_secret = (
            api_secret if api_secret is not None else adapter_cfg.binance_api_secret
        )
        self._testnet = (
            testnet if testnet is not None else adapter_cfg.binance_testnet
        )
        self._base_url = (
            "https://testnet.binancefuture.com"
            if self._testnet
            else "https://fapi.binance.com"
        )

    def fetch(self) -> VenueSnapshot:
        if not self._api_key or not self._api_secret:
            log.warning("Binance credentials missing; venue snapshot unavailable")
            return VenueSnapshot(
                balances={},
                positions={},
                status="missing_credentials",
                error="BINANCE_API_KEY or BINANCE_API_SECRET not configured",
            )

        try:
            params = {"timestamp": int(time.time() * 1000)}
            query = urlencode(params)
            signature = hmac.new(
                self._api_secret.encode(),
                query.encode(),
                hashlib.sha256,
            ).hexdigest()
            url = f"{self._base_url}/fapi/v2/account?{query}&signature={signature}"
            headers = {"X-MBX-APIKEY": self._api_key}

            response = httpx.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            log.error("Binance venue snapshot fetch failed: %s", exc)
            return VenueSnapshot(
                balances={},
                positions={},
                status="fetch_error",
                error=str(exc),
            )

        balances: dict[str, Decimal] = {}
        balance_details: dict[str, dict[str, str]] = {}
        for asset in data.get("assets", []):
            asset_name = str(asset.get("asset", ""))
            wallet = asset.get("walletBalance", "0")
            balances[asset_name] = Decimal(str(wallet))
            balance_details[asset_name] = {
                "walletBalance": str(asset.get("walletBalance", "0")),
                "availableBalance": str(asset.get("availableBalance", "0")),
                "crossWalletBalance": str(asset.get("crossWalletBalance", "0")),
            }

        raw_positions: dict[str, Decimal] = {}
        positions: dict[str, Decimal] = {}
        for pos in data.get("positions", []):
            amt = Decimal(str(pos.get("positionAmt", "0")))
            if amt == 0:
                continue
            symbol = str(pos.get("symbol", ""))
            raw_positions[symbol] = amt
            positions[binance_symbol_to_instrument_id(symbol)] = amt

        return VenueSnapshot(
            balances=balances,
            positions=positions,
            status="ok",
            raw_positions=raw_positions,
            balance_details=balance_details,
        )
