"""ownership_gate node (S7/S8, `odd/tasks/emergencia-turno-siguiente.md`).

The human boundary belongs to the brain, not only to the webhook. `app/webhook/ingest.py`
already refuses to run the graph for a conversation in `human` or `closed` state (HH-5);
keeping the rule only there meant the brain kept answering turns production discards, and
every other caller of `run_conversation` — `scripts/chat_harness.py`, `scripts/conv_eval.py`,
`scripts/kb_fidelity.py` — measured those answers as bot behaviour.

Placement is the design. This gate runs AFTER `emergency_gate`, so a strong emergency hit
has already been routed to the `emergency` node: ownership never blocks the safety protocol
(owner decision L5, «la emergencia gana siempre»). Everything else stops here — the clear
path, the weak hit, the cost gate, capture and respond.
"""

from __future__ import annotations

from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Conversation, ConversationState as ConversationStateEnum


def ownership_gate(state: ConversationState) -> dict:
    """Mute the turn when a human or a closure owns the conversation (S7)."""
    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        owned = conversation is not None and conversation.state in {
            ConversationStateEnum.HUMAN,
            ConversationStateEnum.CLOSED,
        }
    if not owned:
        return {}
    return {"channel_muted": True}
