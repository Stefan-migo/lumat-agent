"""CI-5 customer-facing golden threads through the WhatsApp webhook."""

import pytest
from sqlalchemy import select

from app.chat.nodes.handoff import HANDOFF_REPLY
from app.db import SessionLocal
from app.models import (
    Appointment, Conversation, ConversationState, Customer, Message,
    MessageDirection,
)
from app.services.settings import MESSAGE_DEFAULTS
from tests.webhook_helpers import post_message


def _outbound_texts(session):
    return [
        message.text or ""
        for message in session.scalars(
            select(Message)
            .where(Message.direction == MessageDirection.OUTBOUND)
            .order_by(Message.id)
        )
    ]


def _customer_conversation(session):
    customer = session.scalars(select(Customer)).one()
    conversation = session.scalars(
        select(Conversation)
        .where(Conversation.customer_id == customer.id)
        .order_by(Conversation.id.desc())
        .limit(1)
    ).one()
    return customer, conversation


@pytest.mark.functional
def test_booking_thread_interrupts_for_price_then_resumes_capture(
    client, mock_openai_chat, mock_meta_send, seed_customer_kb,
    seed_booking_availability,
):
    seed_customer_kb(
        "Juan Pérez, Los Leones 1234. ¿Cuánto cuesta la visita? "
        "La visita de diagnóstico tiene un valor referencial de prueba de $15.000."
    )
    technician_id = seed_booking_availability()

    post_message(client, "wamid.ci5.book.1", "hola")
    with SessionLocal() as session:
        replies = _outbound_texts(session)
    assert replies == [MESSAGE_DEFAULTS["greeting"]]
    assert "menú" not in replies[0].lower()

    post_message(client, "wamid.ci5.book.2", "tengo un problema con el calefont, no calienta")
    # Golden-thread turn 4: name + address + a price pivot in ONE message. The
    # price must be answered AND the agenda must resume asking only the
    # still-missing fields — name/address are extracted from this same message.
    post_message(
        client, "wamid.ci5.book.3",
        "Juan Pérez, Los Leones 1234. ¿Cuánto cuesta la visita?",
    )
    with SessionLocal() as session:
        replies = _outbound_texts(session)
        customer, conversation = _customer_conversation(session)
        captured = conversation.captured_data or {}
    assert any("Segun el manual de Lumat" in reply for reply in replies)
    assert HANDOFF_REPLY not in replies
    pivot_reply = replies[-1]
    assert any(k in pivot_reply.lower() for k in ("equipo", "horario", "comuna"))
    assert captured.get("name") == "Juan Pérez"
    assert captured.get("address") == "Los Leones 1234"
    assert "¿Cuál es tu nombre?" not in pivot_reply
    assert "¿Cuál es tu dirección?" not in pivot_reply

    # V4 A3/A7 order: equipment, commune, availability, identity. Drive until
    # the flow asks for consent instead of assuming how many fields the
    # extractor already filled from the price-pivot message.
    for index, answer in enumerate(
        ["Junkers 2019", "Providencia", "mañana en la tarde", "juan@mail.cl"], start=4
    ):
        post_message(client, f"wamid.ci5.book.{index}", answer)
        with SessionLocal() as session:
            last_reply = _outbound_texts(session)[-1]
        if "autorizas" in last_reply.lower():
            break

    assert "autorizas" in last_reply.lower()
    with SessionLocal() as session:
        customer, conversation = _customer_conversation(session)
        captured = conversation.captured_data or {}
    assert captured.get("_pending") == "consent"
    assert "consent" not in captured

    post_message(client, "wamid.ci5.book.90", "sí")
    with SessionLocal() as session:
        slot_offer = _outbound_texts(session)[-1]
        customer, conversation = _customer_conversation(session)
        assert customer.consent_status is True
        assert session.query(Appointment).count() == 0
    assert "1." in slot_offer

    post_message(client, "wamid.ci5.book.91", "1")
    with SessionLocal() as session:
        confirmation = _outbound_texts(session)[-1]
        appointment = session.scalars(select(Appointment)).one()
    assert "confirm" in confirmation.lower()
    assert appointment.technician_id == technician_id


@pytest.mark.functional
def test_kb_thread_answers_prices_and_postventa_without_handoff(
    client, mock_openai_chat, mock_meta_send, seed_customer_kb,
):
    # Short docs: the trigram embedder dilutes a long document's cosine, so each
    # query needs a document that closely mirrors it (min_sim=0.50).
    seed_customer_kb("¿Cuánto sale revisar un calefont? La revisión cuesta $15.000.")
    seed_customer_kb(
        "Me instalaron hace 2 meses y tengo una fuga de agua. "
        "Los trabajos tienen 60 días de garantía."
    )
    post_message(client, "wamid.ci5.kb.1", "hola")
    post_message(client, "wamid.ci5.kb.2", "¿cuánto sale revisar un calefont?")
    post_message(
        client, "wamid.ci5.kb.3",
        "me instalaron hace 2 meses y tengo una fuga de agua",
    )
    with SessionLocal() as session:
        replies = _outbound_texts(session)
        _, conversation = _customer_conversation(session)
    # greeting + one grounded answer per question
    assert len(replies) == 3
    assert all("Segun el manual de Lumat" in reply for reply in replies[1:])
    assert HANDOFF_REPLY not in replies
    assert conversation.state is ConversationState.BOT


@pytest.mark.functional
def test_a_bare_leak_phrasing_is_an_emergency_not_a_postventa_thread(
    client, mock_openai_chat, mock_meta_send,
):
    """Documents the golden-thread wording conflict.

    The task doc's postventa example says 'quedó con una fuga'. A bare 'fuga'
    (no benign qualifier) is a strong emergency keyword by design
    (app/services/emergency.py) and the emergency gate runs before
    classification, so it preempts KB/postventa. The postventa thread above
    uses 'fuga de agua' — the benign qualifier Lumat's gasfitería work expects.
    """
    post_message(
        client, "wamid.ci5.leak.1",
        "me instalaron hace 2 meses y quedó con una fuga",
    )
    with SessionLocal() as session:
        replies = _outbound_texts(session)
        _, conversation = _customer_conversation(session)
    assert conversation.state is ConversationState.HUMAN
    assert not any("Segun el manual de Lumat" in reply for reply in replies)


@pytest.mark.functional
def test_escalation_thread_keeps_emergency_deterministic_and_person_request_human(
    client, mock_openai_chat, mock_meta_send,
):
    post_message(client, "wamid.ci5.escalate.1", "huelo a gas")
    with SessionLocal() as session:
        safety_replies = _outbound_texts(session)
        assert _customer_conversation(session)[1].state is ConversationState.HUMAN
    assert any("INSTRUCCIONES DE SEGURIDAD" in reply for reply in safety_replies)
    assert any("No enciendas" in reply for reply in safety_replies)
    assert not any("Segun el manual de Lumat" in reply for reply in safety_replies)
    assert len(mock_openai_chat) == 0

    # A separate sender gives this escalation an independent BOT conversation.
    post_message(
        client, "wamid.ci5.escalate.2", "quiero hablar con alguien",
        sender="56922223333",
    )
    with SessionLocal() as session:
        assert _outbound_texts(session)[-1] == HANDOFF_REPLY
        conversation = session.scalars(
            select(Conversation).join(Customer).where(Customer.phone_e164 == "+56922223333")
        ).one()
    assert conversation.state is ConversationState.HUMAN


@pytest.mark.functional
def test_hidden_menu_thread_answers_consulta_and_manages_existing_visits(
    client, mock_openai_chat, mock_meta_send, seed_customer_kb,
    seed_future_appointment,
):
    seed_customer_kb("Lumat atiende en La Florida y cubre esa comuna.")
    appointment_ids = seed_future_appointment()

    post_message(client, "wamid.ci5.hidden.1", "¿atienden en La Florida?")
    with SessionLocal() as session:
        consulta_reply = _outbound_texts(session)[-1]
    assert "Segun el manual de Lumat" in consulta_reply
    assert HANDOFF_REPLY not in consulta_reply

    post_message(client, "wamid.ci5.hidden.2", "quiero cancelar mi visita")
    with SessionLocal() as session:
        first_offer = _outbound_texts(session)[-1]
    assert "1." in first_offer
    post_message(client, "wamid.ci5.hidden.3", "1")
    with SessionLocal() as session:
        cancel_confirmation = _outbound_texts(session)[-1]
    assert "visita" in cancel_confirmation.lower()
    post_message(client, "wamid.ci5.hidden.4", "sí")

    post_message(client, "wamid.ci5.hidden.5", "necesito cambiar la hora de la visita")
    with SessionLocal() as session:
        reschedule_offer = _outbound_texts(session)[-1]
        _, conversation = _customer_conversation(session)
        offer = conversation.captured_data["_manage_offer"]
        appointment = session.get(Appointment, appointment_ids[1])
    assert "horarios" in reschedule_offer.lower()
    assert "1." in reschedule_offer
    assert offer["appointment_id"] == appointment.id
