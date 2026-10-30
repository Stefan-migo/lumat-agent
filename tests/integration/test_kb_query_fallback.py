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

from app.chat.nodes import respond as respond_node
from app.chat.state import ConversationState, get_or_create_conversation
from app.chat.subgraphs import research_triage
from app.db import SessionLocal
from app.models import ConversationEvent, Message, MessageDirection, MessageStatus, MessageType
from app.services.realtime import activity_events
from app.services.settings import MESSAGE_DEFAULTS
from app.services import kb as kb_service
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()

RAW = "me dieron tu contacto para una mantencion de caldera"
SERVICE = "mantención de caldera"
# S14 (chatbot-realismo-conversacional): the fallback query is the catalogue's own
# label, not the classifier's spacing and casing, so every phrasing converges.
CANONICAL = "Mantención de caldera"

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


def _patch_answer(monkeypatch) -> dict:
    """Capture the `<kb>` block the model would receive; never call the model."""
    seen: dict = {}

    def fake_answer(text, kb_text, **kwargs):
        seen["kb_text"] = kb_text
        return "respuesta anclada"

    monkeypatch.setattr(respond_node, "_answer_from_kb", fake_answer)
    return seen


def test_a_raw_miss_falls_back_to_the_classified_service(monkeypatch):
    """The regression: polite filler made the raw query miss and derive to a human."""
    state = _state(intent="consulta", service=SERVICE)
    calls = _patch_retrieve(monkeypatch, {CANONICAL: [RETRIEVED]})

    result = research_triage._kb_check(state)

    assert calls == [RAW, CANONICAL]
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


# ---------------------------------------------------------------------------
# H04: one retrieval per turn — `respond` consumes the triage verdict
# ---------------------------------------------------------------------------


def test_respond_consumes_the_retrieval_the_triage_already_made(monkeypatch):
    """The measured duplicate: `kb_check` retrieved, then `respond` retrieved again.

    The second call re-runs the same embed + pgvector query against a database
    that may have moved, so the chunks the model was grounded on were not the
    chunks the routing decision was made on.
    """
    state = _state(intent="consulta", service=SERVICE)
    calls = _patch_retrieve(monkeypatch, {RAW: [RETRIEVED]})
    update = research_triage._kb_check(state)
    state.retrieval = update["retrieval"]  # what the graph state merge does
    seen = _patch_answer(monkeypatch)

    result = respond_node.respond(state)

    assert calls == [RAW]
    assert seen["kb_text"] == f"1. {RETRIEVED['content']}"
    assert result == {"replies": ["respuesta anclada"]}


def test_a_recorded_miss_is_offered_without_a_second_retrieval(monkeypatch):
    """A recorded empty result means "already retrieved and missed", not "not yet".

    Re-retrieving here is what CM-6 would then log twice and what could turn a
    miss into a hit behind the routing decision.
    """
    state = _state(intent="consulta", service=SERVICE)
    state.triage_retry = research_triage.MAX_TRIAGE_RETRIES
    calls = _patch_retrieve(monkeypatch, {})
    update = research_triage._kb_check(state)
    state.retrieval = update["retrieval"]
    seen = _patch_answer(monkeypatch)

    result = respond_node.respond(state)

    assert calls == [RAW, CANONICAL]
    assert seen == {}
    assert len(result["replies"]) == 1


def test_soft_kb_miss_is_visible_in_reconnect_safe_activity_history(monkeypatch):
    state = _state(intent="consulta", service=None)
    state.retrieval = []

    result = respond_node.respond(state)

    assert result == {"replies": [MESSAGE_DEFAULTS["kb_miss_offer"]]}
    assert len(result["replies"]) == 1
    with SessionLocal() as session:
        events = list(session.scalars(activity_events(state.conversation_id)))
    assert [(event.event, event.cause, event.actor) for event in events] == [
        ("kb_miss", "intent=consulta", "bot")
    ]


def test_a_turn_that_skipped_triage_still_retrieves_in_respond(monkeypatch):
    """Guard: the direct `respond` path keeps its own retrieval (previous behaviour)."""
    state = _state(intent="consulta", service=SERVICE)
    calls = _patch_retrieve(monkeypatch, {RAW: [RETRIEVED]})
    _patch_answer(monkeypatch)

    result = respond_node.respond(state)

    assert calls == [RAW]
    assert state.retrieval is None
    assert result == {"replies": ["respuesta anclada"]}
