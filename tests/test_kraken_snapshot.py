"""Kraken venue snapshot tests."""

from decimal import Decimal

import httpx
import respx

from nautilus_trade.adapters.kraken_snapshot import KrakenVenueSnapshotProvider


class TestKrakenVenueSnapshot:
    @respx.mock
    def test_missing_credentials(self) -> None:
        provider = KrakenVenueSnapshotProvider(api_key="", api_secret="", demo=True)
        snapshot = provider.fetch()
        assert snapshot.status == "missing_credentials"

    @respx.mock
    def test_fetch_parses_accounts_positions_orders(self) -> None:
        secret_b64 = "aGVsbG8="
        provider = KrakenVenueSnapshotProvider(
            api_key="test-key",
            api_secret=secret_b64,
            demo=True,
        )
        base = "https://demo-futures.kraken.com"

        respx.get(f"{base}/derivatives/api/v3/accounts").mock(
            return_value=httpx.Response(
                200,
                json={
                    "accounts": {
                        "flex": {"currency": "USD", "balance": "10000.0"},
                    },
                },
            )
        )
        respx.get(f"{base}/derivatives/api/v3/openpositions").mock(
            return_value=httpx.Response(
                200,
                json={"openPositions": [{"symbol": "PF_XBTUSD", "size": "0.01"}]},
            )
        )
        respx.get(f"{base}/derivatives/api/v3/openorders").mock(
            return_value=httpx.Response(
                200,
                json={"openOrders": [{"cliOrdId": "order-1"}]},
            )
        )

        snapshot = provider.fetch()
        assert snapshot.status == "ok"
        assert snapshot.balances["USD"] == Decimal("10000.0")
        assert snapshot.positions["PF_XBTUSD.KRAKEN"] == Decimal("0.01")
        assert snapshot.open_order_client_ids == frozenset({"order-1"})
