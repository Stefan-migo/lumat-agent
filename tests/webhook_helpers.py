"""Shared webhook plumbing for the Batch 6 suites (T6.1).

HMAC signature + Meta payload builders mirroring Meta's delivery format,
shared by tests/functional/test_conversation_flows.py, tests/functional/
test_customer_flows.py and tests/injection/test_injection_suite.py. Keeps
the signing + payload wiring in ONE place instead of three copies.

The webhook signature secret matches the harness conftest TEST_ENV
(APP_SECRET=test-app-secret).
"""

import hashlib
import hmac
import json

import httpx
from fastapi.testclient import TestClient

WEBHOOK_URL = "/webhook/whatsapp"
SECRET = "test-app-secret"
SENDER = "56912345678"  # Chilean mobile, as Meta's wa_id delivers it


def signature_for(body: bytes, secret: str = SECRET) -> str:
    """X-Hub-Signature-256 header for a raw body (HMAC-SHA256, WH-2)."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def message(wamid: str, text: str, sender: str = SENDER) -> dict:
    """One Meta message object (text type)."""
    return {
        "from": sender,
        "id": wamid,
        "timestamp": "1723000000",
        "type": "text",
        "text": {"body": text},
    }


def payload(messages_list: list[dict], sender: str = SENDER) -> dict:
    """A Meta webhook POST payload carrying the given messages."""
    value = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "15551234567", "phone_number_id": "101010"},
        "contacts": [{"profile": {"name": "Test"}, "wa_id": sender}],
        "messages": messages_list,
    }
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "111", "changes": [{"field": "messages", "value": value}]}],
    }


def post_message(
    client: TestClient, wamid: str, text: str, sender: str = SENDER
) -> httpx.Response:
    """POST one signed text message through the webhook (200-first pipeline).

    With the TestClient the BackgroundTask sweep runs synchronously, so after
    the response the message is processed and the bot replies are persisted.
    """
    body = json.dumps(payload([message(wamid, text, sender)], sender)).encode()
    return client.post(
        WEBHOOK_URL, content=body, headers={"X-Hub-Signature-256": signature_for(body)}
    )
