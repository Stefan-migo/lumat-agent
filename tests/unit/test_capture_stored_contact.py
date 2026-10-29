"""S3: a returning customer confirms their contact data once instead of retyping it.

Owner decision (2026-10-29): confirm in a single message, and trust a stored record for
one year. Production conversation #23 asked name, comuna, email, address and consent
again to a customer whose ficha already held all of them.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

from app.chat.nodes import capture as capture_node
from app.chat.state import ConversationState
from app.services.settings import REPLY_TEXT_DEFAULTS


class _StoredCustomer:
    def __init__(self, *, age_days: int = 10, consent: bool = True):
        self.consent_status = consent
        self.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
        self.name = "Stefan"
        self.comuna = "La Reina"
        self.email = "Stefan@mail.com"
        self.address = "Rey de reyes 765"


class _Session:
    def __init__(self, customer):
        self._customer = customer

    def get(self, model, *_args):
        return self._customer if getattr(model, "__name__", "") == "Customer" else None


def _harness(monkeypatch, customer):
    session = _Session(customer)

    @contextmanager
    def session_scope():
        yield session

    monkeypatch.setattr(capture_node, "session_scope", session_scope)
    monkeypatch.setattr(capture_node, "get_conduct", lambda _session: {
        "orden": ["failure", "equipment", "comuna", "availability", "name", "email", "address"],
        "max_preguntas_por_mensaje": 1,
        "derivaciones": ["cobertura"],
    })
    monkeypatch.setattr(capture_node, "get_coverage_communes", lambda _session: ["La Reina"])
    monkeypatch.setattr(capture_node, "get_reply_texts", lambda _session: dict(REPLY_TEXT_DEFAULTS))
    monkeypatch.setattr(capture_node, "_persist_captured", lambda *_args: None)
    monkeypatch.setattr(capture_node, "_apply_consent_and_customer", lambda *_args: None)
    monkeypatch.setattr(capture_node, "_sync_customer_fields", lambda *_args: None)
    monkeypatch.setattr(capture_node, "get_capture_questions", lambda _session: {})
    return session


def _state(text: str, captured: dict) -> ConversationState:
    return ConversationState(
        customer_id=1, conversation_id=2, phone="+56912345678",
        captured=captured, extracted={}, window=[{"text": text}],
    )


_KNOWN_CUSTOMER_CAPTURED = {
    "failure": "no enciende", "equipment": "calefont", "name": "Stefan",
    "availability": "3 de noviembre",
}


def test_a_returning_customer_confirms_their_contact_in_one_message(monkeypatch):
    _harness(monkeypatch, _StoredCustomer())

    result = capture_node.capture(_state("necesito una mantención", dict(_KNOWN_CUSTOMER_CAPTURED)))

    reply = result["replies"][0]
    assert "Rey de reyes 765" in reply and "La Reina" in reply and "Stefan@mail.com" in reply
    assert "cambió algo" in reply
    assert "correo electrónico" not in reply
    assert result["captured"]["_pending"] == "confirm_contact"


def test_a_stale_record_is_asked_normally(monkeypatch):
    """Older than a year: ask, never offer data nobody can vouch for."""
    _harness(monkeypatch, _StoredCustomer(age_days=400))

    result = capture_node.capture(_state("necesito una mantención", dict(_KNOWN_CUSTOMER_CAPTURED)))

    reply = result["replies"][0]
    assert "Rey de reyes 765" not in reply
    assert result["captured"]["_pending"] != "confirm_contact"


def test_confirming_keeps_the_data_and_books(monkeypatch):
    _harness(monkeypatch, _StoredCustomer())

    result = capture_node.capture(_state("sí", {
        **_KNOWN_CUSTOMER_CAPTURED,
        "comuna": "La Reina", "email": "Stefan@mail.com", "address": "Rey de reyes 765",
        "_pending": "confirm_contact", "_contact_offered": True,
        "_seeded_contact": ["comuna", "email", "address"],
    }))

    assert result["next_step"] == "booking"
    assert result["captured"]["address"] == "Rey de reyes 765"
    assert result["captured"]["_consent_previously_granted"] is True


def test_a_correction_drops_what_the_customer_did_not_confirm(monkeypatch):
    """A "no" is not an approval: the unconfirmed data is asked again, never assumed."""
    _harness(monkeypatch, _StoredCustomer())

    result = capture_node.capture(_state("no, cambié de casa", {
        **_KNOWN_CUSTOMER_CAPTURED,
        "comuna": "La Reina", "email": "Stefan@mail.com", "address": "Rey de reyes 765",
        "_pending": "confirm_contact", "_contact_offered": True,
        "_seeded_contact": ["comuna", "email", "address"],
    }))

    assert result.get("next_step") != "booking"
    assert "address" not in result["captured"]
    reply = result["replies"][0]
    assert any(word in reply for word in ("comuna", "correo electrónico", "dirección")), reply
