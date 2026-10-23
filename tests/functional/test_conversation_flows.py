"""T6.2 functional tests — conversation-manager flows over the webhook (CM-1..6).

End-to-end through the REAL pipeline (signature gate -> persist -> background
sweep -> LangGraph run -> outbound persist + Meta send mocked): first contact
menu, repeat-contact resume, capture skip, 3-failure escalation, KB miss ->
unresolved log. The B3/B4 graph behavior was unit-tested at node level in
tests/integration/; these prove the same scenarios through the customer-facing
entry point (TestClient + seeded DB).

Scenarios mapped 1:1 from openspec/specs/conversation-manager/spec.md:

- CM-1 "First contact": greeting + 8-category menu
- CM-1 "Repeat contact on same conversation": resumes, never restarts
- CM-2 "Customer skips a field": field marked unknown, flow continues
- CM-2 "Complete capture" + CR-6: captured fields + consent land on the ficha
- HH-3 "Two failed comprehension attempts": 2x unknown -> human
- CM-4/CM-6 "No reliable answer": KB miss -> cannot-answer + unresolved log
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.chat.nodes.handoff import HANDOFF_REPLY  # noqa: E402
from app.chat.nodes.respond import CANNOT_ANSWER_REPLY  # noqa: E402
from app.services.settings import MESSAGE_DEFAULTS  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationEvent,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
)
from tests.webhook_helpers import post_message


def _last_outbound(session) -> Message:
    return session.scalars(
        select(Message)
        .where(Message.direction == MessageDirection.OUTBOUND)
        .order_by(Message.id.desc())
        .limit(1)
    ).one()


def _outbound_texts(session) -> list[str]:
    return [
        m.text or ""
        for m in session.scalars(
            select(Message)
            .where(Message.direction == MessageDirection.OUTBOUND)
            .order_by(Message.id)
        )
    ]


def _conversation(session, customer: Customer) -> Conversation:
    return session.scalars(
        select(Conversation)
        .where(Conversation.customer_id == customer.id)
        .order_by(Conversation.id.desc())
        .limit(1)
    ).one()


# ---------------------------------------------------------------------------
# CM-1 — first contact open greeting + repeat resume
# ---------------------------------------------------------------------------


@pytest.mark.spec("CM-1")
def test_cm1_first_contact_sends_only_open_greeting(
    client, mock_openai_chat, mock_meta_send
):
    post_message(client, "wamid.cm1.1", "hola")

    with SessionLocal() as session:
        replies = _outbound_texts(session)
        customer = session.scalars(select(Customer)).one()
        assert customer.state.value == "nuevo"  # auto-ficha (CR-1)
        conversation = _conversation(session, customer)
        assert conversation.state == ConversationState.BOT
        unknowns = session.scalar(
            select(func.count(ConversationEvent.id)).where(
                ConversationEvent.conversation_id == conversation.id,
                ConversationEvent.event == "unknown_intent",
            )
        )

    assert len(replies) == 1
    assert replies[0] == MESSAGE_DEFAULTS["greeting"]
    assert "Elige una opción" not in replies[0]
    assert "1." not in replies[0]
    assert unknowns == 0


@pytest.mark.spec("CM-1")
def test_first_greeting_with_service_content_still_classifies_and_routes(
    client, mock_openai_chat, mock_meta_send
):
    post_message(client, "wamid.cm1.content", "hola, tengo un calefont que no calienta")

    with SessionLocal() as session:
        replies = _outbound_texts(session)
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)

    assert len(replies) == 1  # CM-1: greeting + answer fused into ONE message
    assert replies[0].startswith(MESSAGE_DEFAULTS["greeting_short"] + "\n\n")
    assert "¿En qué te puedo ayudar?" not in replies[0]  # the need is already stated
    assert "Qué equipo es" in replies[0]  # V4 A3: one diagnostic question, not a form
    assert mock_openai_chat
    assert conversation.captured_data["_pending"] == ["equipment"]  # failure extracted from the message


@pytest.mark.spec("CM-1")
def test_cm1_repeat_contact_resumes_not_restarts(
    client, mock_openai_chat, mock_meta_send
):
    """Turn 2 must continue the flow (capture question), not greet again."""
    post_message(client, "wamid.cm1.2a", "hola")
    post_message(client, "wamid.cm1.2b", "quiero ver mi calefont")

    with SessionLocal() as session:
        replies = _outbound_texts(session)
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)
        captured = conversation.captured_data or {}

    assert len(replies) == 2
    assert "asistente virtual" in replies[0]  # greeting only on turn 1
    assert "Cuéntame qué pasa con el equipo" in replies[1]  # capture resumed (CM-2 field 1)
    assert "asistente virtual" not in replies[1]  # NOT restarted from scratch
    assert captured["_pending"] == ["failure"]  # state persisted (D2 rebuild)


# ---------------------------------------------------------------------------
# CM-2 — progressive capture: skip + complete-with-consent
# ---------------------------------------------------------------------------


@pytest.mark.spec("CM-2")
def test_cm2_skip_marks_unknown_and_continues(client, mock_openai_chat, mock_meta_send):
    post_message(client, "wamid.cm2.1", "hola")
    post_message(client, "wamid.cm2.2", "calefont")
    post_message(client, "wamid.cm2.3", "no sé")

    with SessionLocal() as session:
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)
        captured = conversation.captured_data or {}
        last_reply = _last_outbound(session).text

    # the skipped field is stored as unknown, NOT blocking the flow (CM-2)
    assert captured.get("failure") == "unknown"
    assert captured["_pending"] == ["equipment"]  # advanced to the next field
    assert "equipo" in (last_reply or "").lower()


@pytest.mark.spec("CM-2")
@pytest.mark.spec("CR-6")
def test_cm2_complete_capture_persists_consent_and_ficha(
    client, mock_openai_chat, mock_meta_send
):
    """Full capture: mandatory answers, optional evidence skipped, consent -> ficha."""
    turns = [
        ("wamid.cm2c.1", "hola"),                      # greeting
        ("wamid.cm2c.2", "calefont"),                  # menu choice -> capture
        ("wamid.cm2c.3", "no enciende desde ayer"),    # failure
        ("wamid.cm2c.4", "Marca X modelo Y, 5 años"),  # equipment
        ("wamid.cm2c.5", "Ñuñoa"),               # comuna
        ("wamid.cm2c.6", "lunes o martes en la tarde"),  # availability
        ("wamid.cm2c.7", "Juan Perez"),                # name
        ("wamid.cm2c.8", "juan@mail.cl"),              # email
        ("wamid.cm2c.9", "Av. Siempre Viva 123"),      # address
        ("wamid.cm2c.10", "sí"),                       # consent -> completion
    ]
    for wamid, text in turns:
        post_message(client, wamid, text)

    with SessionLocal() as session:
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)
        captured = conversation.captured_data or {}
        replies = _outbound_texts(session)

    # CR-6: captured identification/location + consent on the ficha
    assert customer.name == "Juan Perez"
    assert customer.email == "juan@mail.cl"
    assert customer.comuna == "Ñuñoa"
    assert customer.address == "Av. Siempre Viva 123"
    assert customer.consent_status is True
    assert customer.consent_at is not None

    # CM-2: mandatory answers are stored; optional evidence is not a field.
    assert captured["name"] == "Juan Perez"
    assert captured["email"] == "juan@mail.cl"
    assert captured["comuna"] == "Ñuñoa"
    assert captured["equipment"] == "Marca X modelo Y, 5 años"
    assert captured["failure"] == "no enciende desde ayer"
    assert "evidence" not in captured
    assert "_pending" not in captured  # flow completed

    # No technician availability is configured: do not promise a confirmed visit.
    assert any("asesor" in r.lower() for r in replies)
    # CM-5: handoff summary remains attached.
    assert conversation.summary is not None


# ---------------------------------------------------------------------------
# D17 — third failed comprehension attempt escalates to a human
# ---------------------------------------------------------------------------


@pytest.mark.spec("HH-3")
def test_hh3_three_failures_escalate(client, mock_openai_chat, mock_meta_send):
    """Greeting-only is not classified; failures 1-3 clarify, offer, then derive."""
    post_message(client, "wamid.hh3.1", "hola")
    post_message(client, "wamid.hh3.2", "asdfghjkl")
    post_message(client, "wamid.hh3.3", "qwertyuiop")  # failure 2 -> offer

    with SessionLocal() as session:
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)
        second_failure_replies = _outbound_texts(session)

    assert conversation.state == ConversationState.BOT  # D17: offer without leaving the bot
    assert len(second_failure_replies) == 3
    assert any("coordinar una visita" in r.lower() and "persona" in r.lower() for r in second_failure_replies)

    post_message(client, "wamid.hh3.4", "zxcvbnm")  # failure 3 -> derive

    with SessionLocal() as session:
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)
        replies = _outbound_texts(session)
        cases = session.scalars(select(Case)).all()

    assert len(replies) == 4
    assert "Hola, soy el asistente virtual de Lumat." in replies[0]
    assert "asesor revisará tu caso" in replies[-1]  # handoff reply
    assert conversation.state == ConversationState.HUMAN  # HH-1 bot->human
    assert len(cases) == 1  # deriva bundle created (HH-2)
    assert cases[0].conversation_id == conversation.id
    assert cases[0].bundle["escalate_reason"] == "unknown_intent_thrice"


# ---------------------------------------------------------------------------
# CM-4 / CM-6 — KB miss: cannot-answer + unresolved log + escalation
# ---------------------------------------------------------------------------


@pytest.mark.spec("CM-4")
@pytest.mark.spec("CM-6")
def test_cm6_kb_miss_logs_unresolved_and_escalates(
    client, mock_openai_chat, fake_embedder, mock_meta_send
):
    """Empty KB -> scoped research_triage miss -> handoff (H2/AO-8: a sub-agent
    that cannot resolve hands off rather than loop), the question is logged
    unresolved (CM-6), and the conversation escalates by default."""
    post_message(client, "wamid.cm6.1", "hola")
    post_message(client, "wamid.cm6.2", "cuanto cuesta la revision anual")

    with SessionLocal() as session:
        customer = session.scalars(select(Customer)).one()
        conversation = _conversation(session, customer)
        replies = _outbound_texts(session)
        inbound = session.scalars(
            select(Message)
            .where(
                Message.direction == MessageDirection.INBOUND,
                Message.text == "cuanto cuesta la revision anual",
            )
        ).one()

    # H2 (PR 2, AO-8): the scoped research miss hands off directly (the reply
    # is the handoff message, not respond's canned cannot-answer).
    assert replies[1] == HANDOFF_REPLY
    assert conversation.state == ConversationState.HUMAN  # default escalation
    # CM-6: question + context logged on the inbound message payload
    assert (inbound.payload or {}).get("unresolved") is True
    assert (inbound.payload or {}).get("unresolved_context") == "intent=valores"
