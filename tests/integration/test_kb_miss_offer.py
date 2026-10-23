"""S3b of the chatbot backlog: a knowledge miss offers the two paths (D18).

Measured on `main` before this slice: a question the knowledge base could not
answer derived the conversation on the first turn. With production's customer
knowledge base empty, that was every knowledge question, and the customer never
got the choice of booking a visit or asking for a person.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConvState,
    DocumentFormat,
    KbVisibility,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import settings
from app.services.customers import get_or_create_customer
from app.services import kb as kb_service
from app.services.settings import MESSAGE_DEFAULTS
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
OFFER = MESSAGE_DEFAULTS["kb_miss_offer"]
# A knowledge question the empty knowledge base cannot answer. "cuánto cuesta"
# is what the deterministic test double classifies as `valores`, one of the
# retrieval intents, so the turn reaches the research sub-graph instead of
# stopping at `unknown` or entering capture. The plain `respond` path is covered
# by tests/integration/test_single_reply_contract.py.
RESEARCH_MISS = "¿cuánto cuesta el lavado de estanque solar?"


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
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(select(Message).where(Message.wamid == wamid)).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _state(conversation_id: int) -> ConvState:
    with SessionLocal() as session:
        return session.get(Conversation, conversation_id).state


def _causes() -> list[str | None]:
    with SessionLocal() as session:
        return [
            row.cause
            for row in session.scalars(
                select(ConversationEvent).where(ConversationEvent.event == "escalation")
            ).all()
        ]


def test_a_knowledge_miss_offers_the_two_paths_and_keeps_the_bot(mock_openai_chat):
    question = RESEARCH_MISS
    conversation_id = _start_conversation()
    # A greeting first, so the turn under test is not the first contact and CM-1
    # cannot fuse its greeting ahead of the offer.
    _turn(conversation_id, "hola", f"wamid.kbmiss.hello.{abs(hash(question))}")
    replies = _turn(conversation_id, question, f"wamid.kbmiss.{abs(hash(question))}")

    assert replies == [OFFER]
    assert _state(conversation_id) == ConvState.BOT
    assert not any(cause and "kb_miss" in cause for cause in _causes())


def test_the_kb_miss_offer_is_configurable(mock_openai_chat):
    marker = "No tengo ese dato todavía, ¿te tomo los datos o te derivo?"
    with SessionLocal() as session:
        settings.set_setting(session, "messages.kb_miss_offer", marker, actor="test")
        session.commit()

    conversation_id = _start_conversation()
    _turn(conversation_id, "hola", "wamid.kbmiss.custom.hello")
    replies = _turn(conversation_id, RESEARCH_MISS, "wamid.kbmiss.custom")

    assert replies == [marker]


def test_a_knowledge_hit_still_answers_from_the_base(mock_openai_chat):
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual",
            fmt=DocumentFormat.MD,
            content="cuanto cuesta la revision anual de calefont: 15000 pesos".encode(),
            visibility=KbVisibility.CUSTOMER,
        )
        session.commit()

    conversation_id = _start_conversation()
    replies = _turn(conversation_id, "cuanto cuesta la revision anual", "wamid.kbhit.1")

    assert OFFER not in replies
    assert any("15000" in reply for reply in replies)
    assert _state(conversation_id) == ConvState.BOT
