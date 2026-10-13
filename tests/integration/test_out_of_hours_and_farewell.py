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

    assert any("correo" in reply.lower() for reply in replies)
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


@pytest.mark.parametrize("text", ["gracias, chau", "eso fue todo gracias"])
def test_farewell_gets_farewell(text, mock_openai_chat):
    replies = _turn(_start_conversation(), text, f"wamid.farewell.{text[:3]}")

    assert replies == [FAREWELL]
    assert mock_openai_chat == []


def test_closure_message_overrides_are_used(mock_openai_chat):
    farewell = "Despedida configurada."
    notice = "Aviso de horario configurado."
    with SessionLocal() as session:
        settings.set_setting(session, "messages.farewell", farewell, actor="test")
        settings.set_setting(session, "messages.out_of_hours", notice, actor="test")
        session.commit()

    assert _turn(_start_conversation(), "gracias, chau", "wamid.override.1") == [farewell]
    _set_closed_hours()
    assert _turn(_start_conversation(), "hola", "wamid.override.2") == [notice]
