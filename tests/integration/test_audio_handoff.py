from uuid import uuid4

from app.chat.nodes.handoff_gate import handoff_gate, is_media_evidence
from app.chat.nodes.receive import EVIDENCE_ACK, receive
from app.chat.state import ConversationState, get_or_create_conversation
from app.db import SessionLocal
from app.models import Conversation, Customer, Message, MessageDirection, MessageType
from app.services.customers import get_or_create_customer


def _state_for_audio(*, transcript=None):
    phone = f"+569{uuid4().int % 100_000_000:08d}"
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conversation = get_or_create_conversation(session, customer, phone)
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            msg_type=MessageType.AUDIO,
            text=None,
            transcript=transcript,
        )
        session.add(message)
        session.commit()
        ids = (customer.id, conversation.id, message.id)
        state = ConversationState.from_db(session, conversation.id)
        # Avoid first-turn greeting work in receive: this probe is about the media
        # evidence guard, not the greeting branch.
        state.turn = 2

    return state, ids


def _delete_audio_rows(ids):
    customer_id, conversation_id, message_id = ids
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        conversation = session.get(Conversation, conversation_id)
        customer = session.get(Customer, customer_id)
        if message is not None:
            session.delete(message)
            session.flush()
        if conversation is not None:
            session.delete(conversation)
        if customer is not None:
            session.delete(customer)
        session.commit()


def test_audio_without_transcript_keeps_media_evidence_behavior():
    state, ids = _state_for_audio()
    try:
        current = state.window[-1]

        assert current["msg_type"] == "audio"
        assert current["text"] is None
        assert is_media_evidence(current) is True
        assert handoff_gate(state) == {"handoff_reason": None}
        assert receive(state)["replies"] == [EVIDENCE_ACK]
    finally:
        _delete_audio_rows(ids)


def test_audio_with_transcript_uses_text_and_is_not_media_evidence():
    transcript = "necesito coordinar una visita tecnica"
    state, ids = _state_for_audio(transcript=transcript)
    try:
        current = state.window[-1]

        assert current["msg_type"] == "audio"
        assert current["text"] == transcript
        assert is_media_evidence(current) is False
        assert handoff_gate(state) == {"handoff_reason": None}
        assert receive(state).get("replies") is None
        with SessionLocal() as session:
            message = session.get(Message, ids[2])
            assert message.text is None
            assert message.transcript == transcript
    finally:
        _delete_audio_rows(ids)
