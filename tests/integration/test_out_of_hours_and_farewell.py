"""WU3 integration coverage for closure and out-of-hours gates."""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation
from app.db import SessionLocal
from app.models import ConversationEvent, Message, MessageDirection, MessageStatus, MessageType
from app.services import settings
from app.services.customers import get_or_create_customer
from app.chat.state import get_or_create_conversation
from _testdb import admin_database_url


ADMIN_DB_URL = admin_database_url()
OUT_OF_HOURS = "Estamos fuera de nuestro horario de atención. Te responderemos cuando volvamos a atender."
FAREWELL = "¡Gracias por escribirnos! Que tengas buen día."


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _closed_schedule() -> list[dict]:
    now = datetime.now(timezone.utc).astimezone()
    minute = now.minute
    opening = 2 if minute < 2 else 0
    return [{"days": list(range(1, 8)), "open": f"{opening:02d}:00", "close": f"{opening:02d}:01"}]


def _start_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conversation.id


def _set_closed_hours() -> None:
    with SessionLocal() as session:
        settings.set_setting(session, "hours.timezone", "UTC", actor="test")
        settings.set_setting(session, "hours.schedule", _closed_schedule(), actor="test")
        settings.set_setting(session, "hours.closure_enabled", True, actor="test")
        session.commit()


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


def test_closed_normal_question_gets_notice_without_classification(mock_openai_chat):
    _set_closed_hours()
    replies = _turn(_start_conversation(), "¿cuánto cuesta la revisión anual?", "wamid.closed.1")

    assert replies == [OUT_OF_HOURS]
    assert mock_openai_chat == []
    with SessionLocal() as session:
        assert session.scalars(select(ConversationEvent).where(ConversationEvent.event == "unknown_intent")).all() == []


def test_closed_schedule_is_ignored_when_closure_is_disabled(mock_openai_chat):
    with SessionLocal() as session:
        settings.set_setting(session, "hours.timezone", "UTC", actor="test")
        settings.set_setting(session, "hours.schedule", _closed_schedule(), actor="test")
        settings.set_setting(session, "hours.closure_enabled", False, actor="test")
        session.commit()

    replies = _turn(_start_conversation(), "¿cuánto cuesta la revisión anual?", "wamid.closure.disabled")

    assert OUT_OF_HOURS not in replies
    assert mock_openai_chat


def test_strong_emergency_during_closed_hours_keeps_safety_protocol(mock_openai_chat, monkeypatch):
    from app.chat.nodes import emergency

    monkeypatch.setattr(emergency, "send_emergency_notification", lambda *args, **kwargs: None)
    _set_closed_hours()
    replies = _turn(_start_conversation(), "hay una fuga de gas en el calefont", "wamid.closed.2")

    assert any("Corta el suministro" in reply for reply in replies)
    assert OUT_OF_HOURS not in replies
    assert mock_openai_chat == []


def test_weak_emergency_during_closed_hours_keeps_handoff(mock_openai_chat):
    _set_closed_hours()
    replies = _turn(_start_conversation(), "huele raro el calefont", "wamid.closed.3")

    assert any("asesor" in reply.lower() or "persona" in reply.lower() for reply in replies)
    assert OUT_OF_HOURS not in replies


def test_capture_in_progress_during_closed_hours_continues_capture(mock_openai_chat):
    conversation_id = _start_conversation()
    _turn(conversation_id, "quiero una visita", "wamid.closed.4")
    _set_closed_hours()

    replies = _turn(conversation_id, "Juan", "wamid.closed.5")

    assert any("equipo" in reply.lower() for reply in replies)
    assert OUT_OF_HOURS not in replies


def test_open_hours_normal_question_keeps_normal_flow(mock_openai_chat, monkeypatch):
    # `is_open_at` treats `close` as EXCLUSIVE, so no schedule expresses a full
    # 24h day: "00:00-23:59" still leaves 23:59:00-23:59:59 closed. Against the
    # real clock this test failed whenever it ran inside that minute (the CI
    # merge of PR #355 landed at 23:58Z and hit it). Freeze the gate's clock at
    # a mid-day instant instead of racing it.
    frozen = datetime(2026, 3, 10, 15, 30, tzinfo=timezone.utc)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz is not None else frozen

    from app.chat.nodes import closure_gate

    monkeypatch.setattr(closure_gate, "datetime", _FrozenDatetime)

    with SessionLocal() as session:
        settings.set_setting(
            session,
            "hours.schedule",
            [{"days": list(range(1, 8)), "open": "00:00", "close": "23:59"}],
            actor="test",
        )
        settings.set_setting(session, "hours.timezone", "UTC", actor="test")
        session.commit()

    replies = _turn(_start_conversation(), "hola, tengo una consulta", "wamid.open.1")

    assert OUT_OF_HOURS not in replies
    assert mock_openai_chat


def test_empty_schedule_leaves_flow_unchanged(mock_openai_chat):
    replies = _turn(_start_conversation(), "hola, tengo una consulta", "wamid.open.2")

    assert OUT_OF_HOURS not in replies
    assert mock_openai_chat


@pytest.mark.parametrize(
    "text",
    [
        "gracias, ¿cuánto sale la revisión anual?",
        "chau, pero antes dime los valores",
        "hola, necesito una visita",
    ],
)
def test_non_farewell_messages_are_not_closed(text, mock_openai_chat):
    replies = _turn(_start_conversation(), text, f"wamid.not-farewell.{text[:3]}")

    assert FAREWELL not in replies
    assert mock_openai_chat


@pytest.mark.parametrize(
    "text",
    [
        "chau",
        "eso fue todo",
        "eso seria todo muchas gracias! que tengas buen dia",
        "eso seria todo. gracias nuevament",
    ],
)
def test_farewell_gets_farewell(text, mock_openai_chat):
    replies = _turn(_start_conversation(), text, f"wamid.farewell.{text[:3]}")

    assert replies == [FAREWELL]
    assert mock_openai_chat == []


def test_production_sequence_closes_after_temporal_qualifier(mock_openai_chat):
    from app.chat.state import ConvState
    from app.models import Conversation

    conversation_id = _start_conversation()
    priming_replies = _turn(conversation_id, "¿Qué servicios ofrecen?", "wamid.prod-sequence.0")
    assert priming_replies == [
        "Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso."
    ]

    courtesy_replies = _turn(
        conversation_id, "Perfecto muchas gracias", "wamid.prod-sequence.1"
    )
    # The bot answers courtesy with a question, in either of its two configured
    # forms (thanks vs refusal). The exact text is the classifier double's call,
    # so the assertion pins the shape the refusal rule depends on.
    assert len(courtesy_replies) == 1 and courtesy_replies[0].endswith("?")
    replies = _turn(conversation_id, "No, eso sería todo por ahora", "wamid.prod-sequence.2")

    assert replies == [FAREWELL]
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        assert conversation.state == ConvState.CLOSED
        event = session.scalar(
            select(ConversationEvent).where(
                ConversationEvent.conversation_id == conversation_id,
                ConversationEvent.event == "state_change",
            )
        )
        assert event is not None
        assert event.cause == "bot->closed: farewell"


def test_two_refusals_close_but_one_refusal_does_not(mock_openai_chat):
    from app.chat.state import ConvState
    from app.models import Conversation

    conversation_id = _start_conversation()
    priming_replies = _turn(conversation_id, "¿Qué servicios ofrecen?", "wamid.refusal.0")
    assert priming_replies == [
        "Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso."
    ]

    first_reply = _turn(conversation_id, "No", "wamid.refusal.1")
    assert len(first_reply) == 1 and first_reply[0].endswith("?")
    with SessionLocal() as session:
        assert session.get(Conversation, conversation_id).state == ConvState.BOT

    second_reply = _turn(conversation_id, "Nop", "wamid.refusal.2")
    assert second_reply == [FAREWELL]
    with SessionLocal() as session:
        assert session.get(Conversation, conversation_id).state == ConvState.CLOSED
        event = session.scalar(
            select(ConversationEvent).where(
                ConversationEvent.conversation_id == conversation_id,
                ConversationEvent.event == "state_change",
            )
        )
        assert event is not None
        assert event.cause == "bot->closed: farewell"


def test_refusal_during_capture_does_not_close(mock_openai_chat):
    from app.chat.state import ConvState
    from app.models import Conversation

    conversation_id = _start_conversation()
    with SessionLocal() as session:
        session.get(Conversation, conversation_id).captured_data = {"_pending": "name"}
        session.commit()

    replies = _turn(conversation_id, "No", "wamid.refusal.pending")
    assert FAREWELL not in replies
    with SessionLocal() as session:
        assert session.get(Conversation, conversation_id).state == ConvState.BOT


def test_closure_message_overrides_are_used(mock_openai_chat):
    farewell = "Despedida configurada."
    notice = "Aviso de horario configurado."
    with SessionLocal() as session:
        settings.set_setting(session, "messages.farewell", farewell, actor="test")
        settings.set_setting(session, "messages.out_of_hours", notice, actor="test")
        session.commit()

    assert _turn(_start_conversation(), "chau", "wamid.override.1") == [farewell]
    _set_closed_hours()
    assert _turn(_start_conversation(), "hola", "wamid.override.2") == [notice]


@pytest.mark.parametrize("text", ["chau", "no, eso seria todo gracias"])
def test_a_farewell_closes_the_conversation(text, mock_openai_chat):
    """Owner decision (#53): a clear goodbye ends the conversation, not just the turn.

    The reply was already the farewell, but the conversation stayed `bot`, so the
    owner saw a thread that never finished. A closed conversation opens a new one
    on the next inbound message, which is what makes the closure real.
    """
    from app.chat.state import ConvState
    from app.models import Conversation

    conversation_id = _start_conversation()
    replies = _turn(conversation_id, text, f"wamid.close.{text[:3]}")

    assert replies == [FAREWELL]
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        assert conversation.state == ConvState.CLOSED
        assert conversation.closed_at is not None
