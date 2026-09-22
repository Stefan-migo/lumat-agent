"""Receive node — first-contact greeting + menu (CM-1).

Deterministic (no LLM): the very first inbound message of a conversation gets
the Lumat assistant greeting + the 8-category menu. Any later message yields
no reply here — the downstream nodes (capture/respond/summary) own the answer
so the flow resumes from the stored state, never from scratch (CM-1 repeat).
"""

from __future__ import annotations

from app.chat.state import ConversationState, greeting_with_menu
from app.db import session_scope
from app.services.settings import get_message


def receive(state: ConversationState) -> dict:
    """Handle the incoming message at the start of the graph run.

    `state.turn` counts inbound messages (1 = first contact). On repeat, no
    reply is produced here; intent/route/capture/respond drive the answer.
    """
    if state.turn <= 1:
        with session_scope() as session:
            header = get_message(session, "greeting")
        return {"replies": [greeting_with_menu(header)]}
    return {}
