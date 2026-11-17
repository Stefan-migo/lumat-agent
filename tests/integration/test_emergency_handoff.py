"""The turn after an emergency never goes back to the questionnaire (S1, S5).

Two layers keep the customer out of the capture form after an emergency:

1. The `emergency` node hands the conversation to a human, and the brain answers
   nothing while the human owns it (`ownership_gate`; pinned in
   `test_brain_ownership_boundary.py`). In production the webhook adds a third.
2. The case stays flagged (`case.emergency`), and `capture` reads that flag before
   it asks anything. That is the layer reachable today: an operator returns the
   conversation to the bot from the panel while the case is still an emergency, and
   the next customer message must derive instead of resuming the form.

S5 gives the flag a real reader, so this file fails if a later change stops reading
it again.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.chat.nodes.capture import capture
from app.chat.state import ConversationState, get_or_create_conversation, set_conversation_state
from app.db import SessionLocal
from app.models import (
    Case,
    Conversation,
    ConversationState as ConvState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.cases import is_emergency_case, set_case_status
from app.services.customers import get_or_create_customer
from app.services.settings import REPLY_TEXT_DEFAULTS
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def no_emergency_notification(monkeypatch):
    """Keep the owner/technician notification offline; it has its own suite."""
    from app.chat.nodes import emergency as emergency_node

    calls: list = []
    monkeypatch.setattr(
        emergency_node,
        "send_emergency_notification",
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


def _conversation() -> tuple[int, int]:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conversation.id, customer.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conv_id,
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


def _return_to_bot(conv_id: int) -> None:
    """What the panel does when the operator hands the conversation back."""
    with SessionLocal() as session:
        conversation = session.get(Conversation, conv_id)
        set_conversation_state(
            session, conversation, ConvState.BOT, cause="panel:test", actor="operator"
        )
        session.commit()


def test_capture_derives_on_an_emergency_case_instead_of_asking(
    mock_openai_chat, no_emergency_notification
):
    """Corpus repro (`real-fuga-gas-bodega` turn 3): «Podrías venir a ayudarnos?».

    Node-level on purpose: what the guard reads is the case row, and the routing that
    reaches `capture` depends on the classifier. The graph-level half — a conversation
    the human owns is not answered at all — is pinned in
    `test_brain_ownership_boundary.py`.
    """
    conv_id, _ = _conversation()
    protocol = _turn(conv_id, "Fuga de gas en las cañerías hacia los hornos", "wamid.em1")
    assert "INSTRUCCIONES DE SEGURIDAD" in protocol[0]

    # The operator returns the conversation to the bot without closing the case, and
    # the customer's next message is a mid-capture field answer.
    _return_to_bot(conv_id)
    with SessionLocal() as session:
        state = ConversationState.from_db(session, conv_id)
    state.captured = {
        "failure": "Fuga de gas en las cañerías",
        "_pending": ["equipment"],
        "_asked": {"equipment": 1},
    }

    result = capture(state)

    assert result["next_step"] == "handoff"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "emergency"
    # Nothing is asked and nothing is invented: the capture state travels untouched.
    assert result["captured"] == state.captured
    assert "replies" not in result


def test_capture_still_asks_when_the_case_is_not_an_emergency(mock_openai_chat):
    """The guard is scoped to the flag: an ordinary fault keeps the form."""
    conv_id, _ = _conversation()

    replies = _turn(conv_id, "El calefont no enciende", "wamid.em3")

    assert replies
    assert replies != [REPLY_TEXT_DEFAULTS["handoff"]]
    with SessionLocal() as session:
        assert is_emergency_case(session, conv_id) is False


def test_is_emergency_case_reads_the_conversation_case():
    """S5: the flag has a real reader, and it reads the latest case."""
    conv_id, _ = _conversation()
    with SessionLocal() as session:
        assert is_emergency_case(session, conv_id) is False  # no case yet

    with SessionLocal() as session:
        conversation = session.get(Conversation, conv_id)
        session.add(
            Case(
                conversation_id=conv_id,
                customer_id=conversation.customer_id,
                status="escalado",
                emergency=True,
            )
        )
        session.commit()
        assert is_emergency_case(session, conv_id) is True

        case = session.scalars(
            select(Case).where(Case.conversation_id == conv_id)
        ).one()
        case.emergency = False
        session.commit()
        assert is_emergency_case(session, conv_id) is False

        case.emergency = True
        set_case_status(case, "closed")
        session.commit()
        assert is_emergency_case(session, conv_id) is False


def test_emergency_handoff_then_return_to_bot_does_not_resume_questionnaire(
    mock_openai_chat, no_emergency_notification
):
    conv_id, _ = _conversation()
    protocol = _turn(conv_id, "Fuga de gas en las cañerías que van hacia los hornos", "wamid.em4")
    assert "INSTRUCCIONES DE SEGURIDAD" in protocol[0]

    _return_to_bot(conv_id)
    replies = _turn(conv_id, "quiero agendar una visita", "wamid.em5")

    assert replies == ["Un asesor revisará tu caso y te contactará a la brevedad."]
    assert not any("?" in reply for reply in replies)
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state == ConvState.HUMAN
