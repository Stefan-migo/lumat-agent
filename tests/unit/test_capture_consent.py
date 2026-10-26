"""S1 consent gate behavior at the capture-node boundary."""
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from app.chat.nodes import capture as capture_node
from app.chat.state import ConversationState
from app.services.settings import REPLY_TEXT_DEFAULTS


class _Session:
    def get(self, *_args):
        return None


@pytest.fixture
def capture_harness(monkeypatch):
    session = _Session()

    @contextmanager
    def session_scope():
        yield session

    monkeypatch.setattr(capture_node, "session_scope", session_scope)
    monkeypatch.setattr(capture_node, "get_conduct", lambda _session: {
        "orden": ["failure", "equipment", "comuna", "availability", "name", "email", "address"],
        "max_preguntas_por_mensaje": 1,
        "derivaciones": ["cobertura"],
    })
    monkeypatch.setattr(capture_node, "get_coverage_communes", lambda _session: ["Ñuñoa"])
    monkeypatch.setattr(capture_node, "get_reply_texts", lambda _session: dict(REPLY_TEXT_DEFAULTS))
    monkeypatch.setattr(capture_node, "_persist_captured", lambda *_args: None)
    monkeypatch.setattr(capture_node, "_apply_consent_and_customer", lambda *_args: None)
    return session


def state(answer, *, captured=None, extracted=None):
    return ConversationState(
        customer_id=1,
        conversation_id=2,
        phone="+56912345678",
        captured=captured or {"failure": "no enciende", "equipment": "calefont", "comuna": "Ñuñoa", "availability": "mañana", "name": "Ana", "email": "ana@example.cl", "address": "Calle 1", "_pending": "consent"},
        extracted=extracted or {},
        window=[{"text": answer}],
    )


def test_consent_precedes_email_without_asking_identity_before_availability(capture_harness):
    before_availability = capture_node.capture(state(
        "",
        captured={"failure": "no enciende", "equipment": "calefont", "comuna": "Ñuñoa"},
    ))
    assert before_availability["captured"]["_pending"] == ["availability"]
    assert "horarios" in before_availability["replies"][0]

    before_email = capture_node.capture(state(
        "",
        captured={
            "failure": "no enciende", "equipment": "calefont", "comuna": "Ñuñoa",
            "availability": "mañana", "name": "Ana",
        },
    ))
    assert before_email["captured"]["_pending"] == "consent"
    assert before_email["replies"] == [REPLY_TEXT_DEFAULTS["capture_consent"]]


def test_explicit_yes_records_consent_and_proceeds_to_booking(capture_harness, monkeypatch):
    calls = []
    monkeypatch.setattr(capture_node, "_apply_consent_and_customer", lambda *_args: calls.append("record"))

    result = capture_node.capture(state("sí"))

    assert result["next_step"] == "booking"
    assert result["captured"]["consent"] == "sí"
    assert calls == ["record"]


def test_explicit_no_clears_personal_fields_and_derives(capture_harness, monkeypatch):
    calls = []
    monkeypatch.setattr(capture_node, "_apply_consent_and_customer", lambda *_args: calls.append("record"))

    result = capture_node.capture(state("no"))

    assert result["next_step"] == "handoff"
    assert result["escalate_reason"] == "consent_declined"
    assert "email" not in result["captured"] and "address" not in result["captured"]
    assert result["replies"] == [REPLY_TEXT_DEFAULTS["capture_consent_refused"]]
    assert calls == []


def test_unclear_and_skip_reask_then_derive(capture_harness):
    first = capture_node.capture(state("quiero hacer mantencion de caldera"))
    assert first["captured"]["_pending"] == "consent"
    assert first["captured"]["consent"] == "unknown"
    assert first["replies"] == [REPLY_TEXT_DEFAULTS["capture_consent_unclear"]]

    exhausted = {**first["captured"], "_asked": {"consent": capture_node.MAX_ASKS_PER_FIELD}}
    last = capture_node.capture(state("paso", captured=exhausted))
    assert last["next_step"] == "handoff"
    assert last["escalate_reason"] == "consent_unclear"
    assert last["replies"] == [REPLY_TEXT_DEFAULTS["capture_consent_unclear"]]
