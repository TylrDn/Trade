"""Kraken Futures venue snapshot for application-layer reconciliation."""

from __future__ import annotations

import logging
import time
from decimal import Decimal

import httpx

from nautilus_trade.adapters.kraken_auth import sign_kraken_futures_request
from nautilus_trade.adapters.kraken_instruments import kraken_symbol_to_instrument_id
from nautilus_trade.adapters.snapshot_types import VenueSnapshot
from nautilus_trade.config import adapter_cfg

log = logging.getLogger(__name__)

_ACCOUNTS_PATH = "/derivatives/api/v3/accounts"
_OPEN_POSITIONS_PATH = "/derivatives/api/v3/openpositions"
_OPEN_ORDERS_PATH = "/derivatives/api/v3/openorders"


class KrakenVenueSnapshotProvider:
    """Fetch Kraken Futures account state via signed REST."""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        demo: bool | None = None,
    ) -> None:
        self._demo = demo if demo is not None else adapter_cfg.kraken_demo
        if self._demo:
            self._api_key = (
                api_key if api_key is not None else adapter_cfg.kraken_futures_demo_api_key
            )
            self._api_secret = (
                api_secret
                if api_secret is not None
                else adapter_cfg.kraken_futures_demo_api_secret
            )
        else:
            self._api_key = (
                api_key if api_key is not None else adapter_cfg.kraken_futures_api_key
            )
            self._api_secret = (
                api_secret
                if api_secret is not None
                else adapter_cfg.kraken_futures_api_secret
            )
        self._base_url = (
            "https://demo-futures.kraken.com"
            if self._demo
            else "https://futures.kraken.com"
        )

    def fetch(self) -> VenueSnapshot:
        if not self._api_key or not self._api_secret:
            log.warning("Kraken Futures credentials missing; venue snapshot unavailable")
            return VenueSnapshot(
                balances={},
                positions={},
                status="missing_credentials",
                error="Kraken Futures API key/secret not configured",
            )

        try:
            accounts_data = self._get(_ACCOUNTS_PATH)
            positions_data = self._get(_OPEN_POSITIONS_PATH)
            orders_data = self._get(_OPEN_ORDERS_PATH)
        except Exception as exc:  # noqa: BLE001
            log.error("Kraken venue snapshot fetch failed: %s", exc)
            return VenueSnapshot(
                balances={},
                positions={},
                status="fetch_error",
                error=str(exc),
            )

        return self._parse(accounts_data, positions_data, orders_data)

    def _get(self, endpoint_path: str) -> dict:
        nonce = str(int(time.time() * 1000))
        authent = sign_kraken_futures_request(
            self._api_secret,
            endpoint_path,
            post_data="",
            nonce=nonce,
        )
        headers = {
            "APIKey": self._api_key,
            "Authent": authent,
            "Nonce": nonce,
        }
        url = f"{self._base_url}{endpoint_path}"
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        if payload.get("result") == "error":
            raise RuntimeError(str(payload.get("error", payload)))
        return payload

    def _parse(
        self,
        accounts_data: dict,
        positions_data: dict,
        orders_data: dict,
    ) -> VenueSnapshot:
        balances: dict[str, Decimal] = {}
        balance_details: dict[str, dict[str, str]] = {}

        accounts = accounts_data.get("accounts", accounts_data)
        if isinstance(accounts, dict):
            for name, account in accounts.items():
                if not isinstance(account, dict):
                    continue
                currency = str(account.get("currency", name)).upper()
                balance_value = account.get("balance", account.get("auxiliary", {}).get("usd"))
                if balance_value is None:
                    balance_value = account.get("available")
                if balance_value is None:
                    continue
                balances[currency] = Decimal(str(balance_value))
                balance_details[currency] = {
                    "balance": str(balance_value),
                    "account": str(name),
                }

        raw_positions: dict[str, Decimal] = {}
        positions: dict[str, Decimal] = {}
        open_positions = positions_data.get("openPositions", positions_data.get("openpositions", []))
        if isinstance(open_positions, list):
            for pos in open_positions:
                if not isinstance(pos, dict):
                    continue
                symbol = str(pos.get("symbol", ""))
                size = Decimal(str(pos.get("size", pos.get("quantity", "0"))))
                if size == 0 or not symbol:
                    continue
                raw_positions[symbol] = size
                positions[kraken_symbol_to_instrument_id(symbol)] = size

        open_order_client_ids: set[str] = set()
        open_orders = orders_data.get("openOrders", orders_data.get("openorders", []))
        if isinstance(open_orders, list):
            for order in open_orders:
                if not isinstance(order, dict):
                    continue
                client_id = str(order.get("cliOrdId", order.get("clientOrderId", "")))
                if client_id:
                    open_order_client_ids.add(client_id)

        return VenueSnapshot(
            balances=balances,
            positions=positions,
            status="ok",
            raw_positions=raw_positions,
            balance_details=balance_details,
            open_order_client_ids=frozenset(open_order_client_ids),
        )
