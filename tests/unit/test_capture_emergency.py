"""Unit contract for capture's read of the case emergency flag."""

from contextlib import contextmanager

from app.chat.nodes import capture as capture_node
from app.chat.state import ConversationState


def test_capture_reads_conversation_case_emergency_flag_before_questionnaire(monkeypatch):
    looked_up = []
    session = object()

    @contextmanager
    def session_scope():
        yield session

    def is_emergency_case(actual_session, conversation_id):
        looked_up.append((actual_session, conversation_id))
        return True

    monkeypatch.setattr(capture_node, "session_scope", session_scope)
    monkeypatch.setattr(capture_node, "is_emergency_case", is_emergency_case)
    state = ConversationState(
        customer_id=10,
        conversation_id=25,
        phone="+56912345678",
        captured={"failure": "fuga de gas", "_pending": ["equipment"]},
        window=[{"text": "Podrías venir a ayudarnos?", "direction": "inbound"}],
    )

    result = capture_node.capture(state)

    assert looked_up == [(session, 25)]
    assert result["next_step"] == "handoff"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "emergency"
    assert result["captured"] == state.captured
