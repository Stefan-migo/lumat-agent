"""Graph entry points (design: app/chat/graph.py).

The conversation graph is a LangGraph StateGraph over `ConversationState`,
built by `build_graph()` and invoked per message by `run_conversation()`
without a checkpointer (D2 — state is rebuilt from the DB each run).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.chat.nodes.classify_intent import classify_intent
from app.chat.nodes.receive import receive
from app.chat.nodes.route import route
from app.chat.state import ConversationState
from app.models import Message, MessageDirection, MessageStatus, MessageType

__all__ = ["build_graph", "run_conversation"]


def build_graph():
    """Build the compiled conversation graph.

    Batch 3 wiring: receive -> classify_intent -> route. The capture /
    kb_retrieve / respond / summary nodes land in T3.5 (conditional edges are
    added there). Emergency and handoff gates land in Batch 4 (T4.2/T4.4).
    """
    builder = StateGraph(ConversationState)
    builder.add_node("receive", receive)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("route", route)
    builder.add_edge(START, "receive")
    builder.add_edge("receive", "classify_intent")
    builder.add_edge("classify_intent", "route")
    builder.add_edge("route", END)
    return builder.compile()


def persist_replies(session: Session, state: ConversationState, replies: list[str]) -> None:
    """Persist bot replies as outbound messages (status processed).

    The actual Meta send (send.py) is wired in T3.6; until then replies are
    stored so the state window stays complete and delivery can be retried.
    """
    for text in replies:
        session.add(
            Message(
                conversation_id=state.conversation_id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.PROCESSED,
            )
        )
    session.flush()


def run_conversation(session: Session, message: Message) -> list[str]:
    """Run the graph for one persisted inbound message; returns bot replies.

    Rebuilds the state from the DB (D2), runs the graph, persists the replies
    as outbound messages, and returns them for sending (T3.6).
    """
    state = ConversationState.from_db(session, message.conversation_id)
    result = build_graph().invoke(state)
    replies = result.get("replies") or []
    persist_replies(session, state, replies)
    return replies
