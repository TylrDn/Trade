"""Kraken Futures auth tests."""

from __future__ import annotations

import base64
import hashlib
import hmac

from nautilus_trade.adapters.kraken_auth import sign_kraken_futures_request


class TestKrakenFuturesAuth:
    def test_sign_matches_reference_implementation(self) -> None:
        secret_b64 = base64.b64encode(b"test-secret-key").decode()
        nonce = "1234567890"
        endpoint = "/derivatives/api/v3/accounts"
        post_data = ""

        expected_message = hashlib.sha256((nonce + endpoint + post_data).encode()).digest()
        expected = base64.b64encode(
            hmac.new(base64.b64decode(secret_b64), expected_message, hashlib.sha512).digest()
        ).decode()

        assert (
            sign_kraken_futures_request(secret_b64, endpoint, post_data, nonce) == expected
        )

    def test_sign_changes_with_nonce(self) -> None:
        secret_b64 = base64.b64encode(b"another-secret").decode()
        endpoint = "/derivatives/api/v3/openorders"
        a = sign_kraken_futures_request(secret_b64, endpoint, "", "1")
        b = sign_kraken_futures_request(secret_b64, endpoint, "", "2")
        assert a != b
