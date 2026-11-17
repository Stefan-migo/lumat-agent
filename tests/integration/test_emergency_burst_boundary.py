"""S8 on the production burst path: the strong message is not necessarily the last.

`test_emergency_webhook_boundary.py` drives `process_turn` with a single `received`
message, which is not how the webhook reaches the brain. Real inbound messages arrive
as a burst of rows in `processing`, claimed by `_run_burst`, and the brain collapses the
trailing run into one utterance (`ConversationState.from_db`). The boundary decides per
message, the brain classifies the collapsed text, so the two only agree when the burst
is merged — the independent verification found this by probing both paths and getting
different answers.

These tests pin the merged path, and the two silences the boundary must keep.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.state import get_or_create_conversation, set_conversation_state
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
from app.services.customers import get_or_create_customer
from app.webhook import ingest
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()
STRONG = "Fuga de gas en las cañerías que van hacia los hornos"


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
    from app.chat.nodes import emergency as emergency_node

    calls: list = []
    monkeypatch.setattr(
        emergency_node,
        "send_emergency_notification",
        lambda *args, **kwargs: calls.append(args),
    )
    return calls


def _conversation(state: ConvState = ConvState.HUMAN) -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912340001")
        conversation = get_or_create_conversation(session, customer, "+56912340001")
        set_conversation_state(
            session, conversation, state, cause="test_setup", actor="rule"
        )
        session.commit()
        return conversation.id


def _row(conv_id: int, *, text: str | None = None, wamid: str, msg_type=MessageType.TEXT) -> int:
    with SessionLocal() as session:
        message = Message(
            wamid=wamid,
            conversation_id=conv_id,
            direction=MessageDirection.INBOUND,
            msg_type=msg_type,
            text=text,
            status=MessageStatus.RECEIVED,
        )
        session.add(message)
        session.commit()
        return message.id


def _burst(conv_id: int, message_ids: list[int]) -> list[str]:
    """Run the production burst path: claim the rows, run one turn, deliver."""
    ingest._run_burst(conv_id, message_ids)
    with SessionLocal() as session:
        return [
            message.text
            for message in session.scalars(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.direction == MessageDirection.OUTBOUND,
                ).order_by(Message.id)
            )
        ]


def test_strong_first_message_of_a_burst_is_delivered(
    mock_openai_chat, no_emergency_notification, monkeypatch
):
    """The safety protocol does not depend on the strong message being the last one."""
    monkeypatch.setattr(ingest, "deliver_outbound", lambda *args: None)
    conv_id = _conversation()

    replies = _burst(
        conv_id,
        [
            _row(conv_id, text=STRONG, wamid="wamid.burst1"),
            _row(conv_id, text="y el perro esta asustado", wamid="wamid.burst2"),
        ],
    )

    assert len(replies) == 3
    assert "INSTRUCCIONES DE SEGURIDAD" in replies[0]
    assert not any("?" in reply for reply in replies)
    assert not mock_openai_chat  # the emergency path never calls the model
    with SessionLocal() as session:
        assert session.get(Conversation, conv_id).state == ConvState.HUMAN
        case = session.scalars(select(Case).where(Case.conversation_id == conv_id)).one()
    assert case.emergency is True


def test_weak_hit_in_a_burst_stays_mute(mock_openai_chat):
    """A weak hit is not a licence to speak inside a human conversation (HH-5)."""
    conv_id = _conversation()

    assert _burst(conv_id, [_row(conv_id, text="huele raro aca", wamid="wamid.burst3")]) == []

    with SessionLocal() as session:
        assert session.scalar(select(Case.id).where(Case.conversation_id == conv_id)) is None
    assert not mock_openai_chat


def test_media_only_burst_stays_mute(mock_openai_chat):
    """CI-4 media evidence never becomes speech in a conversation a human owns."""
    conv_id = _conversation()

    replies = _burst(
        conv_id, [_row(conv_id, wamid="wamid.burst4", msg_type=MessageType.IMAGE)]
    )

    assert replies == []
    assert not mock_openai_chat
