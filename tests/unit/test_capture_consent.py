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


def test_an_explicit_refusal_phrase_is_a_decline_not_an_unclear_answer(capture_harness, monkeypatch):
    """`no autorizo` answers the consent question; it is a decision, not confusion."""
    calls = []
    monkeypatch.setattr(capture_node, "_apply_consent_and_customer", lambda *_args: calls.append("record"))

    result = capture_node.capture(state("no autorizo"))

    assert result["next_step"] == "handoff"
    assert result["escalate_reason"] == "consent_declined"
    assert result["replies"] == [REPLY_TEXT_DEFAULTS["capture_consent_refused"]]
    assert calls == []
