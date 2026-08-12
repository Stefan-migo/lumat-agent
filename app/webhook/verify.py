"""Webhook verification helpers (specs WH-1, WH-2).

WH-1 — GET verify handshake: validate `hub.mode=subscribe` and
`hub.verify_token` against the configured token; return `hub.challenge` on
success, `None` otherwise (route answers 403).

WH-2 — POST signature verification: recompute the HMAC-SHA256 of the RAW
request body using the app secret and compare it constant-time with the
`X-Hub-Signature-256` header (`sha256=<hex>`). Any failure -> False, and the
request MUST be dropped with 403 (never persisted, never processed).
"""

import hashlib
import hmac
import logging
from typing import Mapping, Optional

logger = logging.getLogger(__name__)

SIGNATURE_PREFIX = "sha256="


def verify_handshake(params: Mapping[str, str], verify_token: str) -> Optional[str]:
    """Return the `hub.challenge` value when the handshake is valid, else None.

    Valid handshake (WH-1): `hub.mode == 'subscribe'` AND
    `hub.verify_token == configured token`.
    """
    if params.get("hub.mode") != "subscribe":
        return None
    if params.get("hub.verify_token") != verify_token:
        return None
    return params.get("hub.challenge")


def verify_signature(
    raw_body: bytes, signature_header: Optional[str], app_secret: str
) -> bool:
    """Verify `X-Hub-Signature-256` over the raw request body (WH-2).

    Returns True only when the header is present, well-formed (`sha256=<hex>`)
    and the digest matches, compared in constant time. The verification always
    runs over the exact bytes received — never over a re-encoded/parsed body.
    """
    if not signature_header or not signature_header.startswith(SIGNATURE_PREFIX):
        return False
    provided = signature_header[len(SIGNATURE_PREFIX):]
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)
