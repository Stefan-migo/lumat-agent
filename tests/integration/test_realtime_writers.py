"""Phase 4 RED contracts for activity and conversation recency writers."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.chat.nodes.classify_intent import classify_intent
from app.chat.nodes.handoff import handoff
from app.chat.state import ConversationState
from app.chat.subgraphs import research_triage
from app.db import SessionLocal, session_scope
from app.models import (
    Conversation,
    ConversationEvent,
    ConversationState as ConversationStateEnum,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
)
from app.services.conversations import send_operator_message
from app.services.customers import get_or_create_customer
from app.services.realtime import activity_events
from app.services.users import hash_password
from app.webhook.ingest import normalize_message, persist_message


def _conversation(session):
    customer = Customer(phone_e164="+56900000041")
    session.add(customer)
    session.flush()
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    return customer, conversation


def test_classification_persists_classified_activity(migrated_db, monkeypatch):
    with SessionLocal() as session:
        customer, conversation = _conversation(session)
        session.commit()
        monkeypatch.setattr(
            "app.chat.nodes.classify_intent._llm_classify",
            lambda text, message_id, conversation="": {
                "intent": "calefont",
                "service": "calefont",
                "priority": "media",
                "status": "abierto",
                "injection": False,
            },
        )
        state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            window=[{"id": 1, "text": "Necesito revisar el calefont"}],
        )

        result = classify_intent(state)
    with SessionLocal() as session:
        events = session.scalars(activity_events(conversation.id)).all()
        assert result["intent"] == "calefont"
        assert [event.event for event in events] == ["classified"]


def test_unknown_classification_also_persists_classified_activity(migrated_db, monkeypatch):
    with SessionLocal() as session:
        customer, conversation = _conversation(session)
        session.commit()
        monkeypatch.setattr(
            "app.chat.nodes.classify_intent._llm_classify",
            lambda text, message_id, conversation="": {"intent": "unknown", "injection": False},
        )
        state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            window=[{"id": 1, "text": "Una pregunta"}],
        )

        classify_intent(state)

    with SessionLocal() as session:
        events = session.scalars(activity_events(conversation.id)).all()
        assert [event.event for event in events] == ["classified"]


def test_classification_propagates_selected_template_id(migrated_db, monkeypatch):
    # T4: the id the classifier picked flows into the state updates so the
    # send path can render it (D3).
    with SessionLocal() as session:
        customer, conversation = _conversation(session)
        session.commit()
        monkeypatch.setattr(
            "app.chat.nodes.classify_intent._llm_classify",
            lambda text, message_id, conversation="": {
                "intent": "consulta",
                "service": "consulta",
                "priority": "baja",
                "status": "abierto",
                "injection": False,
                "template_id": "horarios",
            },
        )
        state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            window=[{"id": 1, "text": "a qué hora abren"}],
        )

        result = classify_intent(state)

    assert result["intent"] == "consulta"
    assert result["template_id"] == "horarios"


def test_kb_hit_persists_kb_retrieved_activity(migrated_db, monkeypatch):
    with SessionLocal() as session:
        customer, conversation = _conversation(session)
        session.commit()
        monkeypatch.setattr(research_triage, "_sub_whitelist", lambda: ("kb.retrieve",))
        monkeypatch.setattr(research_triage.kb, "retrieve", lambda *args, **kwargs: [object()])
        state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            window=[{"id": 1, "text": "Cuanto cuesta"}],
        )

        assert research_triage._kb_check(state)["next_step"] == "respond"
    with SessionLocal() as session:
        events = session.scalars(activity_events(conversation.id)).all()
        assert [event.event for event in events] == ["kb_retrieved"]


def test_handoff_publishes_one_escalation_activity(migrated_db, monkeypatch):
    published = []

    async def capture(envelope):
        published.append(envelope)

    monkeypatch.setattr("app.services.realtime.publisher.publish", capture)
    monkeypatch.setattr("app.chat.nodes.handoff.generate_summary", lambda state, customer: "summary")
    with SessionLocal() as session:
        customer, conversation = _conversation(session)
        session.commit()
        state = ConversationState(
            customer_id=customer.id,
            conversation_id=conversation.id,
            phone=customer.phone_e164,
            escalate_reason="persona",
        )
        handoff(state)

    with SessionLocal() as session:
        events = session.scalars(activity_events(conversation.id)).all()
        assert [event.event for event in events] == ["escalation"]
    activities = [event for event in published if event.type == "activity"]
    assert len(activities) == 1
    assert activities[0].data["event"] == "escalation"


def test_webhook_message_updates_conversation_recency(migrated_db):
    normalized = normalize_message(
        {"id": "wamid.recency", "from": "56900000042", "type": "text", "text": {"body": "Hola"}},
        {"contacts": [{"wa_id": "56900000042"}]},
    )
    before = datetime.now(timezone.utc)
    with session_scope() as session:
        persist_message(session, normalized)
        conversation = session.scalar(select(Conversation))
        assert conversation.last_message_at is not None
        assert conversation.last_message_at >= before


def test_panel_message_updates_conversation_recency(migrated_db, monkeypatch):
    monkeypatch.setattr(
        "app.services.conversations.deliver_message",
        lambda message_id: None,
    )
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56900000043")
        conversation = Conversation(
            customer_id=customer.id,
            wa_phone=customer.phone_e164,
            state=ConversationStateEnum.HUMAN,
        )
        session.add(conversation)
        session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="Necesito ayuda",
                status=MessageStatus.PROCESSED,
            )
        )
        user = User(username="writer-admin", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.commit()
        before = datetime.now(timezone.utc)

        send_operator_message(session, conversation.id, user, "Te ayudamos", "req-recency")

        session.refresh(conversation)
        assert conversation.last_message_at is not None
        assert conversation.last_message_at >= before


def test_activity_history_remains_queryable_after_new_session(migrated_db):
    with session_scope() as session:
        _, conversation = _conversation(session)
        from app.services.realtime import record_activity

        record_activity(session, conversation.id, "classified", cause="calefont")
        record_activity(session, conversation.id, "kb_retrieved", cause="kb")
        record_activity(session, conversation.id, "escalation", cause="handoff:persona")

    with SessionLocal() as session:
        events = session.scalars(activity_events(conversation.id)).all()
        assert [event.event for event in events] == [
            "classified",
            "kb_retrieved",
            "escalation",
        ]


def test_state_transition_publishes_conversation_event(migrated_db, monkeypatch):
    published = []

    async def capture(envelope):
        published.append(envelope)

    monkeypatch.setattr("app.services.realtime.publisher.publish", capture)
    with SessionLocal() as session:
        _, conversation = _conversation(session)
        session.commit()

    from app.chat.state import set_conversation_state

    with session_scope() as session:
        conversation = session.get(Conversation, conversation.id)
        set_conversation_state(
            session,
            conversation,
            ConversationStateEnum.HUMAN,
            cause="persona",
            actor="rule",
        )

    events = [event for event in published if event.type == "conversation"]
    assert len(events) == 1
    assert events[0].conversation_id == conversation.id
    assert events[0].data == {
        "conversation_id": conversation.id,
        "from_state": "bot",
        "state": "human",
        "cause": "persona",
        "actor": "rule",
    }


def test_state_transition_publication_failure_does_not_rollback_transition(
    migrated_db, monkeypatch
):
    attempts = []

    async def fail(envelope):
        attempts.append(envelope)
        raise RuntimeError("subscriber disappeared")

    monkeypatch.setattr("app.services.realtime.publisher.publish", fail)
    with SessionLocal() as session:
        _, conversation = _conversation(session)
        session.commit()

    from app.chat.state import set_conversation_state

    with session_scope() as session:
        conversation = session.get(Conversation, conversation.id)
        set_conversation_state(
            session,
            conversation,
            ConversationStateEnum.HUMAN,
            cause="persona",
            actor="rule",
        )

    with SessionLocal() as session:
        persisted = session.get(Conversation, conversation.id)
        assert persisted.state == ConversationStateEnum.HUMAN
    assert len(attempts) == 1
    assert attempts[0].type == "conversation"
