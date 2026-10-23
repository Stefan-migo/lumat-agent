"""A KB miss caused by conversational filler is rescued by the classifier's `service`.

Measured on the seeded customer KB with the real embedder (2026-10-22):

| query | similarity | vs `min_sim = 0.50` |
|---|---|---|
| `me dieron tu contacto para una mantencion de caldera` | 0.2686 | miss |
| `mantención de caldera` (the classifier's `service`) | 0.6070 | hit |

So the customer's first real message — a service request with polite filler —
escalated to a human while the KB held the answer. The customer text is still tried
FIRST: it carries the *aspect* the customer asked about (garantía, plazo, precio) that
the normalized `service` drops ("tienen garantia por la mantencion?" scores 0.510 raw
against 0.341 as `service`). The fallback is therefore strictly additive: every turn
that already found a chunk answers exactly as before, and only a miss pays the second
local retrieval (no extra LLM call).
"""

import psycopg
import pytest

from app.chat.state import ConversationState, get_or_create_conversation
from app.chat.subgraphs import research_triage
from app.db import SessionLocal
from app.models import Message, MessageDirection, MessageStatus, MessageType
from app.services import kb as kb_service
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()

RAW = "me dieron tu contacto para una mantencion de caldera"
SERVICE = "mantención de caldera"

RETRIEVED = {
    "document_id": 1,
    "version": 1,
    "chunk_index": 1,
    "content": "Mantención de caldera: inspección, limpieza y purgado.",
    "source_meta": None,
    "similarity": 0.61,
}


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _state(*, intent: str | None, service: str | None) -> ConversationState:
    """A conversation with one inbound message, classified as (intent, service)."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56900000777")
        conversation = get_or_create_conversation(session, customer, "+56900000777")
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=RAW,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        conversation_id = conversation.id
        state = ConversationState.from_db(session, conversation_id)
    state.intent = intent
    state.case = {"service": service} if service else {}
    return state


def _patch_retrieve(monkeypatch, hits: dict[str, list[dict]]) -> list[str]:
    """Record every query and answer only the queries listed in `hits`."""
    calls: list[str] = []

    def fake_retrieve(session, query, **kwargs):
        calls.append(query)
        return hits.get(query, [])

    monkeypatch.setattr(kb_service, "retrieve", fake_retrieve)
    return calls


def test_a_raw_miss_falls_back_to_the_classified_service(monkeypatch):
    """The regression: polite filler made the raw query miss and derive to a human."""
    state = _state(intent="consulta", service=SERVICE)
    calls = _patch_retrieve(monkeypatch, {SERVICE: [RETRIEVED]})

    result = research_triage._kb_check(state)

    assert calls == [RAW, SERVICE]
    assert result["next_step"] == "respond", result
    assert result.get("escalate") is not True, result


def test_a_raw_hit_answers_as_before_and_costs_one_retrieval(monkeypatch):
    """Guard: the fallback must not change any turn that already found a chunk."""
    state = _state(intent="consulta", service=SERVICE)
    calls = _patch_retrieve(monkeypatch, {RAW: [RETRIEVED]})

    result = research_triage._kb_check(state)

    assert calls == [RAW]
    assert result["next_step"] == "respond", result


def test_a_miss_without_a_fresh_classification_offers_paths(monkeypatch):
    """Guard: `unknown` writes no case, so its `service` is stale and must not be used."""
    state = _state(intent="unknown", service=SERVICE)
    state.triage_retry = research_triage.MAX_TRIAGE_RETRIES
    calls = _patch_retrieve(monkeypatch, {})

    result = research_triage._kb_check(state)

    assert calls == [RAW]
    assert result["next_step"] == "respond", result
    assert result.get("escalate") is not True
    assert "escalate_reason" not in result
