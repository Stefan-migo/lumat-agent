"""S2b of the chatbot backlog: the unknown counter counts a streak, not a total.

Measured on `main` before this slice (H06, D6): `_record_unknown_intent` and
`ConversationState.from_db` counted every `unknown_intent` row of the
conversation, so two failures separated by a turn the bot understood still
escalated, and an exception inside classification was written as a
comprehension failure.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import ConversationState, get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConvState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
# The deterministic test double classifies a price question as a real intent, so
# it stands for any turn the bot understood.
UNDERSTOOD = "¿cuánto cuesta la revisión anual?"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _start_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conversation.id


def _turn(conversation_id: int, text: str, wamid: str) -> list[str]:
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conversation_id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            text=text,
            status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _events(name: str) -> list[ConversationEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(ConversationEvent).where(ConversationEvent.event == name)
            ).all()
        )


def _streak(conversation_id: int) -> int:
    with SessionLocal() as session:
        return ConversationState.from_db(session, conversation_id).unknown_count


def _conversation_state(conversation_id: int) -> ConvState:
    with SessionLocal() as session:
        return session.get(Conversation, conversation_id).state


def _record_understood(conversation_id: int) -> None:
    """Write the row an understood classification writes and the streak reads."""
    with SessionLocal() as session:
        session.add(
            ConversationEvent(
                conversation_id=conversation_id,
                event="classified",
                cause="intent:consulta",
                actor="bot",
            )
        )
        session.commit()


def test_streak_resets_after_a_turn_the_bot_understood(mock_openai_chat):
    conversation_id = _start_conversation()

    _turn(conversation_id, "no entiendo nada de esto", "wamid.streak.1")
    assert _streak(conversation_id) == 1

    _turn(conversation_id, UNDERSTOOD, "wamid.streak.2")
    assert _streak(conversation_id) == 0

    _turn(conversation_id, "sigo sin decir nada claro", "wamid.streak.3")
    assert _streak(conversation_id) == 1


def test_two_failures_split_by_an_understood_turn_do_not_escalate(mock_openai_chat):
    """A failure either side of an understood turn is not two failures in a row.

    The judged effect is the counter's own escalation, not the final conversation
    state: the state also moves on the separate `kb_miss` trigger, whose answer
    depends on knowledge-base rows this module's fixture does not reset, so
    asserting the state made the test depend on what another module left behind.
    """
    conversation_id = _start_conversation()

    _turn(conversation_id, "no entiendo nada de esto", "wamid.split.1")
    _record_understood(conversation_id)
    _turn(conversation_id, "sigo sin decir nada claro", "wamid.split.2")

    assert _streak(conversation_id) == 1
    causes = [event.cause for event in _events("escalation")]
    assert "handoff:unknown_intent_thrice" not in causes


def test_three_consecutive_failures_still_escalate(mock_openai_chat):
    """D17: the third consecutive failure derives; the second one only offers."""
    conversation_id = _start_conversation()

    _turn(conversation_id, "no entiendo nada de esto", "wamid.consec.1")
    _turn(conversation_id, "sigo sin decir nada claro", "wamid.consec.2")
    assert _conversation_state(conversation_id) == ConvState.BOT

    _turn(conversation_id, "y sigo sin decir nada claro", "wamid.consec.3")

    assert _conversation_state(conversation_id) == ConvState.HUMAN
    causes = [event.cause for event in _events("escalation")]
    assert "handoff:unknown_intent_thrice" in causes


def test_a_technical_failure_is_not_a_comprehension_failure(mock_openai_chat, monkeypatch):
    from app.chat.nodes import classify_intent

    def boom(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(classify_intent, "_llm_classify", boom)

    replies = _turn(_start_conversation(), "¿atienden en Ñuñoa?", "wamid.tech.1")

    assert replies, "the customer is still answered"
    assert _events("unknown_intent") == []
    assert _events("classify_failed"), "the failure is recorded for diagnosis"
