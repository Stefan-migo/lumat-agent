"""Integration tests for the approved, non-delivering chatbot simulation tool (S3)."""

import pytest
from sqlalchemy import func, select

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool, get_tool
from app.db import SessionLocal
from app.models import Case, Conversation, ConversationEvent, Customer, DomainEvent, Message, MessageDirection
from app.services.prompts import load_assistant_config

TOOL = "chatbot.simulate"


def _approval(arguments: dict) -> dict:
    normalized = get_tool(TOOL).args_model.model_validate(arguments).model_dump()
    approval = issue_approval({"tool": TOOL, "arguments": normalized})
    assert consume_approval(approval, approval["token"]) is True
    return approval


def _stub_brain_models(monkeypatch):
    from app.chat.nodes import classify_intent
    from app.services import settings

    monkeypatch.setattr(settings, "get_simulation_enabled", lambda _session: True)

    monkeypatch.setattr(
        classify_intent,
        "_llm_classify",
        lambda *_args, **_kwargs: {
            "intent": "consulta", "intents": ["consulta"], "service": None,
            "priority": "baja", "status": None, "injection": False, "fields": {},
        },
    )


def test_approved_simulation_runs_two_real_brain_turns_without_delivery(
    monkeypatch, mock_openai_chat
):
    _stub_brain_models(monkeypatch)
    arguments = {"messages": ["Necesito revisar una caldera", "¿Cuánto cuesta?"]}

    with SessionLocal() as session:
        result = execute_tool(
            session,
            TOOL,
            arguments,
            approval=_approval(arguments),
            whitelist=set(load_assistant_config().tools_whitelist),
            role="admin",
        )

    assert result["status"] == "completed"
    assert result["read_only"] is False
    payload = result["result"]
    assert set(payload) == {"turns", "conversation_id", "delivered"}
    assert payload["delivered"] is False
    assert len(payload["turns"]) == 2
    assert [turn["text"] for turn in payload["turns"]] == arguments["messages"]
    assert all(turn["replies"] for turn in payload["turns"])
    assert all(turn["intent"] == "consulta" for turn in payload["turns"])
    assert all(isinstance(turn["events"], list) for turn in payload["turns"])


def test_simulation_writes_no_domain_event_or_active_conversation(monkeypatch, mock_openai_chat):
    _stub_brain_models(monkeypatch)
    arguments = {"messages": ["Necesito revisar una caldera"]}
    with SessionLocal() as session:
        result = execute_tool(
            session,
            TOOL,
            arguments,
            approval=_approval(arguments),
            whitelist=set(load_assistant_config().tools_whitelist),
            role="admin",
        )
        session.commit()

    conversation_id = result["result"]["conversation_id"]
    with SessionLocal() as session:
        conversation = session.get(Conversation, conversation_id)
        domain_events = session.scalars(
            select(DomainEvent).where(
                DomainEvent.entity_type == "conversation",
                DomainEvent.entity_id == str(conversation_id),
            )
        ).all()
        outbound = session.scalars(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.direction == MessageDirection.OUTBOUND,
            )
        ).all()
        assert conversation is not None
        assert conversation.last_message_at is None
        assert conversation.simulated is True
        assert domain_events == []
        # Replies are brain observations persisted in the conversation; they are
        # not channel deliveries. No outbox event or delivery request exists.
        assert outbound


def test_simulation_without_approval_creates_no_conversation():
    arguments = {"messages": ["Necesito revisar una caldera"]}
    # The tool derives its own reserved phone; this checks the public write gate
    # and proves refusal occurs before the handler can create any customer rows.
    with SessionLocal() as session:
        before_conversations = session.scalar(select(func.count(Conversation.id)))
        before_customers = session.scalar(select(func.count(Customer.id)))
        with pytest.raises(ToolValidationError, match="requires consumed exact approval"):
            execute_tool(
                session,
                TOOL,
                arguments,
                whitelist=set(load_assistant_config().tools_whitelist),
                role="admin",
            )
        assert session.scalar(select(func.count(Conversation.id))) == before_conversations
        assert session.scalar(select(func.count(Customer.id))) == before_customers


def test_simulation_refuses_by_default_as_a_normal_tool_error_without_writes():
    arguments = {"messages": ["Necesito revisar una caldera"]}
    with SessionLocal() as session:
        before_conversations = session.scalar(select(func.count(Conversation.id)))
        before_customers = session.scalar(select(func.count(Customer.id)))
        result = execute_tool(
            session, TOOL, arguments, approval=_approval(arguments),
            whitelist=set(load_assistant_config().tools_whitelist), role="admin",
        )
        assert result["status"] == "error"
        assert result["error"] == (
            "chatbot.simulate is disabled; enable setting "
            "'chatbot.simulation_enabled' to run simulations"
        )
        assert session.scalar(select(func.count(Conversation.id))) == before_conversations
        assert session.scalar(select(func.count(Customer.id))) == before_customers


def test_two_runs_share_one_synthetic_customer_and_open_fresh_conversations(
    monkeypatch, mock_openai_chat
):
    _stub_brain_models(monkeypatch)
    arguments = {"messages": ["Necesito revisar una caldera"]}
    with SessionLocal() as session:
        first = execute_tool(
            session, TOOL, arguments, approval=_approval(arguments),
            whitelist=set(load_assistant_config().tools_whitelist), role="admin",
        )
        second = execute_tool(
            session, TOOL, arguments, approval=_approval(arguments),
            whitelist=set(load_assistant_config().tools_whitelist), role="admin",
        )

    with SessionLocal() as session:
        synthetic = session.scalars(
            select(Customer).where(Customer.phone_e164 == "+56900000000")
        ).all()
        assert len(synthetic) == 1
        # A reused conversation would answer the second run with the first one's context.
        assert first["result"]["conversation_id"] != second["result"]["conversation_id"]
        assert session.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.customer_id == synthetic[0].id
            )
        ) == 2
