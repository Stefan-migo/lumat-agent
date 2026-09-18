"""Integration coverage for the chat-harness core (ODD: chat-harness).

The harness is a manual QA surface over `run_conversation` — it adds no
production seam. These tests pin the contracts the REPL depends on, so the
surface cannot silently rot when the graph or the services move.

Only deterministic paths are asserted here:
- `ensure_conversation` is pure DB (customer + open conversation get-or-create).
- The emergency route is the one full path that reaches END with **zero LLM
  calls** (the gate runs before any model call — `app/chat/graph.py:194-199`).
- The first-contact greeting comes from `receive`, which is deterministic in
  content, but the turn still continues into `classify_intent` — so an LLM
  call is expected and mocked, never asserted away.
"""

import os
import sys
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import func, select

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from chat_harness import ensure_conversation, inspect, run_turn  # noqa: E402

from app.chat.state import MENU_CATEGORIES  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Case, Conversation, ConversationState, Customer  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)

PHONE = "+56912345678"
STRONG_EMERGENCY = "hay una fuga de gas en el calefont"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset the tables this unit reads, including `settings`.

    `settings` is in the list on purpose: the test database is shared by every
    worktree's pytest run, and emergency keyword overrides written by another
    suite leak into `emergency.keywords` and silently change gate outcomes
    (observed: a leaked `["caja de fusibles quemada"]` turned a strong hit into
    a weak one). Resetting it keeps these tests order- and neighbour-independent.
    """
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, memories, memory_relations, memory_observations, "
            "audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def no_emergency_notification(monkeypatch):
    """Stub the owner/technician notification, which reaches the network.

    The emergency node fires a WhatsApp template with an email fallback
    (`app/chat/nodes/emergency.py:107-113`). That behaviour is owned by
    `test_emergency_notify.py`, not by this unit, so the boundary is stubbed
    here to keep these tests offline and deterministic. The stub still proves
    the call happens — it records it.
    """
    from app.chat.nodes import emergency as emergency_node

    calls: list = []
    monkeypatch.setattr(
        emergency_node,
        "send_emergency_notification",
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


# ---------------------------------------------------------------------------
# ensure_conversation — get-or-create, idempotent per phone
# ---------------------------------------------------------------------------


def test_ensure_conversation_is_idempotent_per_phone():
    with SessionLocal() as session:
        first = ensure_conversation(session, PHONE)
        session.commit()
        second = ensure_conversation(session, PHONE)
        session.commit()

    assert first == second
    with SessionLocal() as session:
        assert session.scalar(select(func.count(Customer.id))) == 1
        assert session.scalar(select(func.count(Conversation.id))) == 1


def test_ensure_conversation_never_reopens_a_closed_conversation():
    with SessionLocal() as session:
        first = ensure_conversation(session, PHONE)
        session.commit()
        closed = session.get(Conversation, first)
        closed.state = ConversationState.CLOSED
        session.commit()

        second = ensure_conversation(session, PHONE)
        session.commit()

    assert second != first
    with SessionLocal() as session:
        states = session.scalars(
            select(Conversation.state).order_by(Conversation.id)
        ).all()
    assert states == [ConversationState.CLOSED, ConversationState.BOT]


# ---------------------------------------------------------------------------
# run_turn — drives the real entry point
# ---------------------------------------------------------------------------


def test_first_turn_returns_the_greeting_with_the_full_menu(mock_openai_chat):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        replies = run_turn(session, conversation_id, "hola")
        session.commit()

    assert replies, "a first contact must produce at least the greeting"
    greeting = replies[0]
    assert "asistente virtual" in greeting.lower()
    for category in MENU_CATEGORIES:
        assert category in greeting

    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        # The panel's active list filters on `last_message_at IS NOT NULL`
        # (`app/panel/api/routes/conversations.py:238-239`), so a turn that
        # leaves it unset produces a conversation nobody can see in the UI.
        assert conversation.last_message_at is not None


def test_emergency_turn_escalates_without_any_llm_call(mock_openai_chat, no_emergency_notification):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        replies = run_turn(session, conversation_id, STRONG_EMERGENCY)
        session.commit()

    # The gate runs before any model call; a fresh conversation adds none.
    assert mock_openai_chat == []
    assert any("Bomberos" in reply for reply in replies)

    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        assert conversation.state == ConversationState.HUMAN
        assert session.scalar(select(func.count(Case.id))) == 1


# ---------------------------------------------------------------------------
# inspect — the observables the REPL prints
# ---------------------------------------------------------------------------


def test_inspect_surfaces_state_intent_events_and_memories(mock_openai_chat):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(session, conversation_id, "mi calefont falla")
        session.commit()
        result = inspect(session, conversation_id)

    assert result["conversation_id"] == conversation_id
    assert result["state"] == "bot"
    assert "captured_data" in result
    # The classified intent is persisted from inside the production path.
    assert any(
        event["event"] == "classified" and event["cause"] == "intent:calefont"
        for event in result["events"]
    ), result["events"]
    # The per-turn session memory is written by run_conversation itself.
    assert any(memory["topic_key"] == "session" for memory in result["memories"]), result["memories"]


def test_inspect_reports_the_emergency_case_and_human_state(mock_openai_chat, no_emergency_notification):
    with SessionLocal() as session:
        conversation_id = ensure_conversation(session, PHONE)
        session.commit()
        run_turn(session, conversation_id, STRONG_EMERGENCY)
        session.commit()
        result = inspect(session, conversation_id)

    assert result["state"] == "human"
    assert result["case"] is not None
    assert result["case"]["emergency"] is True
