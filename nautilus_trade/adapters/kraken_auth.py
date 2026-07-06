"""Kraken Futures REST authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac


def sign_kraken_futures_request(
    api_secret: str,
    endpoint_path: str,
    post_data: str,
    nonce: str,
) -> str:
    """Compute Kraken Futures ``Authent`` header value.

    Authent = Base64(HMAC-SHA512(SHA256(nonce + endpointPath + postData), secret))
    where secret is Base64-decoded from the API secret.
    """
    message = hashlib.sha256((nonce + endpoint_path + post_data).encode()).digest()
    secret = base64.b64decode(api_secret)
    signature = hmac.new(secret, message, hashlib.sha512).digest()
    return base64.b64encode(signature).decode()
