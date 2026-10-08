"""Receive node — first-contact open greeting (CM-1).

Deterministic (no LLM): the first inbound message gets the Lumat greeting;
media-only turns receive an acknowledgement that the file was saved as evidence.
Other turns leave the answer to downstream nodes (capture/respond/summary), so
the flow resumes from stored state, never from scratch (CM-1 repeat).
"""

from __future__ import annotations

from app.chat.nodes.handoff_gate import is_media_evidence
from app.chat.state import ConversationState, greeting
from app.db import session_scope
from app.services.settings import get_message

EVIDENCE_ACK = "Recibí tu archivo, lo guardé para el técnico."


def receive(state: ConversationState) -> dict:
    """Handle the incoming message at the start of the graph run.

    `state.turn` counts inbound messages (1 = first contact). Media receives an
    evidence acknowledgement while normal turns continue to downstream nodes.
    """
    replies: list[str] = []
    if state.turn <= 1:
        with session_scope() as session:
            header = get_message(session, "greeting")
        replies.append(greeting(header))
    message = state.window[-1] if state.window else None
    if is_media_evidence(message):
        replies.append(EVIDENCE_ACK)
    return {"replies": replies} if replies else {}
