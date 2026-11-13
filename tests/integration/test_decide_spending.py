from uuid import uuid4

from sqlalchemy import select

from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    ConversationEvent,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.case_ficha import SPENDING_QUESTION_REPLY
from app.services.customers import get_or_create_customer


def _phone() -> str:
    return f"+569{uuid4().int % 100_000_000:08d}"


def _conversation(decide_spending="si"):
    phone = _phone()
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        customer.decide_spending = decide_spending
        conversation = get_or_create_conversation(session, customer, phone)
        session.commit()
        return conversation.id, customer.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
    from app.chat.graph import run_conversation

    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message).where(Message.conversation_id == conv_id, Message.wamid == wamid)
        ).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _seed_kb_doc(text: str) -> None:
    from app.models import DocumentFormat, KbVisibility
    from app.services import kb as kb_service

    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual de prueba",
            fmt=DocumentFormat.MD,
            content=text.encode(),
            visibility=KbVisibility.CUSTOMER,
        )
        session.commit()


def _respond_prompt(captured: list[dict]) -> str:
    for body in reversed(captured):
        content = body["messages"][-1]["content"]
        if "<kb>" in content:
            return content
    raise AssertionError("no respond LLM call was made")


def test_turn_evidence_persists_non_decider_value(mock_openai_chat):
    conv_id, customer_id = _conversation()
    _turn(conv_id, "soy arrendatario, consulto con el dueño", f"wamid.{uuid4().hex}")

    with SessionLocal() as session:
        assert session.get(Customer, customer_id).decide_spending == "no"


def test_duda_customer_gets_one_deterministic_question_without_response_llm(mock_openai_chat):
    conv_id, _ = _conversation(decide_spending="duda")
    replies = _turn(conv_id, "¿cuánto cuesta?", f"wamid.{uuid4().hex}")

    assert replies[-1].endswith(SPENDING_QUESTION_REPLY)
    # The classifier may call the LLM, but respond must not make a KB answer call.
    assert not any("<kb>" in body["messages"][-1]["content"] for body in mock_openai_chat)
    with SessionLocal() as session:
        event = session.scalar(
            select(ConversationEvent.id)
            .where(
                ConversationEvent.conversation_id == conv_id,
                ConversationEvent.event == "spending_question",
            )
            .limit(1)
        )
        assert event is not None


def test_spending_question_is_not_repeated_in_the_same_conversation(mock_openai_chat):
    conv_id, _ = _conversation(decide_spending="duda")
    first = _turn(conv_id, "¿cuánto cuesta?", f"wamid.{uuid4().hex}")
    second = _turn(conv_id, "¿y el precio?", f"wamid.{uuid4().hex}")

    assert first[-1].endswith(SPENDING_QUESTION_REPLY)
    assert SPENDING_QUESTION_REPLY not in second


def test_si_customer_is_not_asked_about_spending(mock_openai_chat):
    conv_id, _ = _conversation(decide_spending="si")
    replies = _turn(conv_id, "¿cuánto cuesta?", f"wamid.{uuid4().hex}")

    assert SPENDING_QUESTION_REPLY not in replies
    with SessionLocal() as session:
        event = session.scalar(
            select(ConversationEvent.id)
            .where(
                ConversationEvent.conversation_id == conv_id,
                ConversationEvent.event == "spending_question",
            )
            .limit(1)
        )
        assert event is None


def test_decide_spending_value_reaches_the_respond_ficha(mock_openai_chat):
    _seed_kb_doc("cuanto cuesta la revision anual 15000")
    conv_id, _ = _conversation(decide_spending="no")
    _turn(conv_id, "¿cuánto cuesta la revisión anual?", f"wamid.{uuid4().hex}")

    assert "Decide el gasto: no" in _respond_prompt(mock_openai_chat)


def test_no_question_when_no_money_is_at_stake(mock_openai_chat):
    """S8: "sólo cuando hay plata en juego" — a broken heater is not a price."""
    conv_id, _ = _conversation(decide_spending="duda")
    replies = _turn(conv_id, "la caldera no calienta la casa", f"wamid.{uuid4().hex}")

    assert SPENDING_QUESTION_REPLY not in replies
    with SessionLocal() as session:
        event = session.scalar(
            select(ConversationEvent.id)
            .where(
                ConversationEvent.conversation_id == conv_id,
                ConversationEvent.event == "spending_question",
            )
            .limit(1)
        )
        assert event is None
