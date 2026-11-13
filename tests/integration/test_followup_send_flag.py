from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    NotificationTemplateVersion,
)
from app.services.settings import set_setting
from app.services.followup import sweep_followup


def _idle_conversation(phone: str, now: datetime) -> int:
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name="Ana")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id, wa_phone=phone, state=ConversationState.HUMAN
        )
        session.add(conversation)
        session.flush()
        session.add(Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.TEXT,
            status=MessageStatus.PROCESSED,
            text="Consulta",
            created_at=now - timedelta(hours=30),
        ))
        conversation_id = conversation.id
        session.commit()
        return conversation_id


def _set_options(*, enabled: bool, template: str = ""):
    with SessionLocal() as session:
        set_setting(session, "followup.idle_enabled", enabled)
        set_setting(session, "followup.idle_template_name", template)
        session.commit()


def _event_count(conversation_id: int, event: str) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count(ConversationEvent.id)).where(
            ConversationEvent.conversation_id == conversation_id,
            ConversationEvent.event == event,
        ))


def test_disabled_or_unconfigured_template_never_sends_or_marks_sent(monkeypatch):
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    sent = []
    monkeypatch.setattr("app.services.followup.notify.send_template", lambda *a, **k: sent.append((a, k)))

    disabled_id = _idle_conversation("+56970000021", now)
    _set_options(enabled=False, template="idle_followup")
    with SessionLocal() as session:
        sweep_followup(session, now=now)
        session.commit()
    assert sent == []
    assert _event_count(disabled_id, "idle_followup_sent") == 0

    unconfigured_id = _idle_conversation("+56970000022", now)
    _set_options(enabled=True)
    with SessionLocal() as session:
        sweep_followup(session, now=now)
        session.commit()
    assert sent == []
    assert _event_count(unconfigured_id, "idle_followup_sent") == 0


def test_enabled_template_sends_once_and_records_success_marker(monkeypatch):
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    conversation_id = _idle_conversation("+56970000023", now)
    _set_options(enabled=True, template="idle_followup")
    sent = []
    monkeypatch.setattr(
        "app.services.followup.notify.send_template",
        lambda phone, params, *, template_name: sent.append((phone, params, template_name)) or "wamid.test",
    )

    for _ in range(2):
        with SessionLocal() as session:
            sweep_followup(session, now=now)
            session.commit()

    assert sent == [("+56970000023", [], "idle_followup")]
    assert _event_count(conversation_id, "idle_followup_sent") == 1


def test_send_needs_no_locally_published_template_version(monkeypatch):
    """D5: the owner's configured template name is the contract, not a local row.

    Requiring a published `NotificationTemplateVersion` for `followup.idle` would
    silently disable the feature for a name the operator already knows works —
    the technician visit actions send the same way, by name.
    """
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    _idle_conversation("+56970000024", now)
    _set_options(enabled=True, template="idle_followup")
    sent = []
    monkeypatch.setattr(
        "app.services.followup.notify.send_template",
        lambda phone, params, *, template_name: sent.append((phone, template_name)) or "wamid.test",
    )

    def published_versions() -> int:
        with SessionLocal() as session:
            return session.scalar(
                select(func.count(NotificationTemplateVersion.id)).where(
                    NotificationTemplateVersion.event == "followup.idle"
                )
            )

    before = published_versions()
    with SessionLocal() as session:
        sweep_followup(session, now=now)
        session.commit()

    # The send happened without publishing anything locally: the name is the contract.
    assert published_versions() == before
    assert sent == [("+56970000024", "idle_followup")]
