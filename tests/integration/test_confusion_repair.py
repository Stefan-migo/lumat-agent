"""S4 of `odd/tasks/saludo-informal.md`: the repair, measured end to end.

Production #40, verbatim:

    No te entendí            -> Perdón. No entendí tu mensaje.
    Jaja                     -> Con gusto. ¿Te puedo ayudar en algo más?

The customer said they did not understand the bot, and the bot answered that it
did not understand the customer. The turn also charged one `unknown_intent`
against the customer, which is the counter that escalates the conversation.
"""

import psycopg

from app.chat.graph import run_conversation
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer
from app.services.settings import MESSAGE_DEFAULTS, set_setting
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


def _conversation() -> int:
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


def _events(conversation_id: int, event: str) -> list[ConversationEvent]:
    with SessionLocal() as session:
        return [
            row
            for row in session.query(ConversationEvent)
            .filter(ConversationEvent.conversation_id == conversation_id)
            .filter(ConversationEvent.event == event)
            .all()
        ]


def test_not_understanding_the_bot_gets_the_repair_not_the_mirror(migrated_db, monkeypatch):
    conversation_id = _conversation()
    _turn(conversation_id, "Holaa", "wamid.confusion.greeting")

    def classify(*_args, **_kwargs):
        raise AssertionError("a repair request must not reach classification")

    from app.chat.nodes import classify_intent
    monkeypatch.setattr(classify_intent, "_llm_classify", classify)

    replies = _turn(conversation_id, "No te entendí", "wamid.confusion.repair")

    assert replies == [MESSAGE_DEFAULTS["confusion"]]
    assert "no entendí tu mensaje" not in replies[0].lower()
    assert _events(conversation_id, "unknown_intent") == []
    assert _events(conversation_id, "classified") == []
    # The conversation is not escalated: the customer's confusion is the bot's to
    # repair, and it costs the customer nothing.
    assert _events(conversation_id, "escalation") == []


def test_the_repair_text_is_the_configured_one(migrated_db, monkeypatch):
    conversation_id = _conversation()
    _turn(conversation_id, "Holaa", "wamid.confusion.configured.seed")
    with SessionLocal() as session:
        set_setting(session, "messages.confusion", "Texto configurado por Lumat.")
        session.commit()

    replies = _turn(conversation_id, "no entendí nada", "wamid.confusion.configured")

    assert replies == ["Texto configurado por Lumat."]


def test_a_complaint_that_opens_the_same_way_keeps_its_path(migrated_db, monkeypatch):
    """The guard: "no entiendo" plus a stated problem is content, not a repair."""
    conversation_id = _conversation()
    _turn(conversation_id, "Holaa", "wamid.confusion.complaint.seed")
    observed: list[str] = []

    def classify(text, **_kwargs):
        observed.append(text)
        return {
            "intent": "unknown", "service": None, "priority": None, "status": None,
            "injection": False, "fields": {}, "template_id": None,
        }

    from app.chat.nodes import classify_intent
    monkeypatch.setattr(classify_intent, "_llm_classify", classify)

    replies = _turn(
        conversation_id,
        "no entiendo por qué me cobraron eso",
        "wamid.confusion.complaint",
    )

    assert observed == ["no entiendo por qué me cobraron eso"]
    assert replies == [MESSAGE_DEFAULTS["clarification"]]
    assert len(_events(conversation_id, "unknown_intent")) == 1
