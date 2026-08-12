"""Receive node — first-contact greeting + menu, resume on repeat (CM-1).

Deterministic (no LLM): the very first inbound message of a conversation gets
the Lumat assistant greeting + the 8-category menu; any later message resumes
from the stored state — the flow never restarts from scratch.
"""

from __future__ import annotations

from app.chat.state import RESUME_REPLY, ConversationState, greeting_with_menu


def receive(state: ConversationState) -> dict:
    """Handle the incoming message at the start of the graph run.

    `state.turn` counts inbound messages (1 = first contact). On repeat, the
    bot acknowledges and the next nodes (intent/route, T3.4/T3.5) drive the
    reply from the resumed state.
    """
    if state.turn <= 1:
        return {"replies": [greeting_with_menu()]}
    return {"replies": [RESUME_REPLY]}
