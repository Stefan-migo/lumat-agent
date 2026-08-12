"""T0.3 — webhook GET verify handshake (WH-1) and POST signature check (WH-2).

Scenarios mapped 1:1 from openspec/changes/hito-1-setup-whatsapp/specs/whatsapp-webhook/spec.md:
- WH-1 "Meta subscribes the webhook": correct token -> 200 + exact challenge
- WH-1 "Token mismatch": wrong/missing token or mode -> 403 + logged attempt
- WH-2 "Valid signature": accepted (200, no processing yet — persist stub)
- WH-2 "Invalid signature": missing/malformed/wrong header -> 403, payload dropped

Full persist + 200-before-process behavior lands with the messages table in T2.2.
"""

import hashlib
import hmac

import pytest

WEBHOOK_URL = "/webhook/whatsapp"


def _signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.spec("WH-1")
def test_get_verify_returns_challenge_with_correct_token(client):
    challenge = "challenge-12345"
    resp = client.get(
        WEBHOOK_URL,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": challenge,
        },
    )
    assert resp.status_code == 200
    assert resp.text == challenge


@pytest.mark.spec("WH-1")
@pytest.mark.parametrize(
    "params",
    [
        {"hub.mode": "subscribe", "hub.verify_token": "wrong-token", "hub.challenge": "x"},
        {"hub.mode": "subscribe", "hub.challenge": "x"},  # missing token
        {"hub.mode": "unsubscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "x"},
        {},  # empty params
    ],
)
def test_get_verify_rejects_invalid_handshake(client, params):
    resp = client.get(WEBHOOK_URL, params=params)
    assert resp.status_code == 403


@pytest.mark.spec("WH-2")
def test_post_with_valid_signature_returns_200(client):
    body = b'{"object":"whatsapp_business_account","entry":[]}'
    resp = client.post(
        WEBHOOK_URL,
        content=body,
        headers={"X-Hub-Signature-256": _signature(body, "test-app-secret")},
    )
    assert resp.status_code == 200


@pytest.mark.spec("WH-2")
@pytest.mark.parametrize(
    "signature",
    [
        None,  # missing header
        "sha256=nothex",  # malformed digest
        "sha256=" + "0" * 64,  # wrong digest
        "sha512=" + "0" * 128,  # wrong algorithm prefix
    ],
)
def test_post_with_invalid_signature_returns_403(client, signature):
    body = b'{"object":"whatsapp_business_account","entry":[]}'
    headers = {} if signature is None else {"X-Hub-Signature-256": signature}
    resp = client.post(WEBHOOK_URL, content=body, headers=headers)
    assert resp.status_code == 403
