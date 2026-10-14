"""Graph entry points (design: app/chat/graph.py).

The conversation graph is a LangGraph StateGraph over `ConversationState`,
built by `build_graph()` and invoked per message by `run_conversation()`
without a checkpointer (D2 — state is rebuilt from the DB each run).

Batch 3 flow:

    receive -> classify_intent -> route
        route:
          capture  -> capture (one field/turn) -> summary on completion
          kb_retrieve / respond -> respond (KB-grounded)
          escalate -> summary (escalation summary)

Batch 4 adds the deterministic gates before any LLM:

    emergency_gate -> emergency (strong hit; no LLM) | handoff (weak hit)
        emergency: strong -> safety protocol (EM-3), case flagged, state->human
        weak -> handoff node (EM-5: same human/escalate flow as T4.4)
        miss -> cost_gate (T4.5, SS-3)
    cost_gate -> handoff (blocked: no LLM + deterministic fallback) | handoff_gate
        conservative -> flow continues, respond answers briefly
    handoff_gate -> handoff (deterministic trigger; no LLM) | receive

Ordering: emergency (safety) > cost (budget) > handoff triggers > LLM.
`emergency_gate` runs before `cost_gate` so a strong emergency hit during a
budget block still delivers the safety protocol (the emergency path never
calls the LLM anyway); `cost_gate` runs before `handoff_gate` so a blocked
conversation labels the escalation with the cost reason.

Batch 4 (T4.4) adds the handoff node, which owns every escalation:

    handoff_gate (persona/media/complaint) -> handoff
    emergency_gate weak hit -> handoff
    classify_intent 2x unknown / SS-1 always_escalate -> route escalate -> handoff
    injection (SH-4) -> route escalate -> handoff
    respond KB miss -> handoff

The handoff node builds the HH-2 deriva bundle (case row), transitions the
conversation bot -> human (HH-1) and replies that a human will take over.
The gate runs before `receive` too, so a first-contact emergency never mixes
the greeting into the safety protocol (EM-2 full flow interrupt).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.chat.nodes.capture import capture
from app.chat.nodes.booking import booking
from app.chat.nodes.classify_intent import classify_intent
from app.chat.nodes.cost_gate import cost_gate
from app.chat.nodes.closure_gate import closure_gate
from app.chat.nodes.emergency import emergency
from app.chat.nodes.emergency_gate import emergency_gate
from app.chat.nodes.handoff import handoff
from app.chat.nodes.handoff_gate import handoff_gate
from app.chat.nodes.manage import manage
from app.chat.nodes.orchestrate import orchestrate
from app.chat.nodes.receive import is_greeting_only, receive
from app.chat.nodes.respond import respond
from app.chat.nodes.summary import summary
from app.chat.state import ConversationState
from app.chat.subgraphs.research_triage import build_research_triage_subgraph
from app.models import InternalChatThread, Message, MessageDirection, MessageStatus, MessageType
from app.services.memory import persist_memory_session
from app.services import llm

__all__ = ["build_graph", "run_conversation"]


PRIVILEGED_INTERNAL_ACTIONS = ("delete", "drop", "grant access", "reveal password", "send money")
INTERNAL_SYSTEM_PROMPT = (
    "You are Lumat's internal operations assistant for an owner or admin. "
    "Answer operational questions concisely using only the user's message. "
    "You have no tools, customer data, or ability to perform actions; never "
    "claim that you executed a change or accessed privileged information."
)
logger = logging.getLogger(__name__)


def run_internal_conversation(
    session: Session,
    thread: InternalChatThread,
    text: str,
    on_token: Callable[[str], None] | None = None,
) -> str:
    """Constrained internal boundary: answer or refuse, never execute tools.

    Internal chat deliberately has no customer conversation state, tools, or
    privileged side effects. It remains a graph-owned boundary so the service
    cannot accidentally grow a second agent runtime.
    """
    lowered = text.casefold()
    if any(action in lowered for action in PRIVILEGED_INTERNAL_ACTIONS):
        return "I cannot perform privileged actions from internal chat. Please use the approved operational workflow."
    try:
        request = {
            "model": llm.CHAT_MODEL,
            "messages": [
                {"role": "system", "content": INTERNAL_SYSTEM_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            "temperature": 0,
        }
        if on_token is None:
            response = llm.openai_client().chat.completions.create(**request)
            return response.choices[0].message.content or "I could not produce an answer. Please try again."

        response = llm.openai_client().chat.completions.create(**request, stream=True)
        if not hasattr(response, "__iter__"):
            return response.choices[0].message.content or "I could not produce an answer. Please try again."
        chunks: list[str] = []
        for chunk in response:
            token = chunk.choices[0].delta.content or ""
            if token:
                chunks.append(token)
                try:
                    on_token(token)
                except Exception:
                    logger.exception("Internal agent token callback failed")
        return "".join(chunks) or "I could not produce an answer. Please try again."
    except Exception:
        logger.exception("Internal agent chat model call failed")
        raise


def _flow_start(state: ConversationState) -> str:
    """Skip classification for a greeting-only first turn; otherwise classify."""
    if state.turn <= 1 and is_greeting_only(state):
        return END
    return "classify_intent"


def _after_emergency_gate(state: ConversationState) -> str:
    """Strong -> emergency protocol; weak -> handoff (EM-5); miss -> cost_gate."""
    if state.emergency_hit == "strong":
        return "emergency"
    if state.emergency_hit == "weak":
        return "handoff"
    return "cost_gate"


def _after_cost_gate(state: ConversationState) -> str:
    """Blocked (conversation or daily at 100%) -> handoff without LLM (SS-3);
    normal/conservative -> the deterministic handoff triggers."""
    return "handoff" if state.cost_mode == "blocked" else "handoff_gate"


def _after_handoff_gate(state: ConversationState) -> str:
    """Deterministic trigger -> handoff node; clear -> normal flow."""
    if state.handoff_reason:
        return "handoff"
    if "_booking_offer" in (state.captured or {}):
        return "booking"
    if "_manage_offer" in (state.captured or {}):
        return "manage"
    return "closure_gate"


def _after_closure_gate(state: ConversationState) -> str:
    """End when the closure gate produced a reply; otherwise continue normally."""
    return END if state.replies else "receive"


def _route_path(state: ConversationState) -> str:
    return getattr(state, "next_step", None) or "respond"


def _after_capture(state: ConversationState) -> str:
    step = getattr(state, "next_step", None)
    return step if step in {"booking", "summary"} else END


def _after_booking(state: ConversationState) -> str:
    step = getattr(state, "next_step", None)
    return step if step in {"summary", "handoff"} else END


def _after_manage(state: ConversationState) -> str:
    step = getattr(state, "next_step", None)
    return step if step in {"summary", "handoff"} else END


def _after_respond(state: ConversationState) -> str:
    # KB miss escalates -> handoff (deriva bundle); answers end the turn
    return "handoff" if state.escalate else END


def _after_research_triage(state: ConversationState) -> str:
    """Resume the capture agenda after a KB deviation was answered (CI-2).

    Only when a mid-capture deviation was routed here (capture_paused) and the
    sub-graph did not itself escalate/hand off. A KB miss sets `escalate` inside
    the sub-graph and must terminate, never resume.
    """
    return "capture" if state.capture_paused and not state.escalate else END


def _triage_node(subgraph):
    """Wrap the triage sub-graph so it does not re-add the parent's replies.

    `research_triage` is compiled over the same `ConversationState` as this graph
    (`app/chat/subgraphs/research_triage.py`), and `replies` carries an `add` reducer
    (`app/chat/state.py`). Added as a plain node, LangGraph hands the sub-graph the
    parent's `replies` — already holding the CM-1 greeting — and merging the sub-graph's
    final state back re-adds them, so the customer receives the greeting twice.

    Clearing the accumulator on the way in leaves the merge with exactly the sub-graph's
    own reply. A partial `input_schema` would also fix the duplication, and is rejected:
    the sub-graph reads 12 of `ConversationState`'s 21 fields, so a partial schema would
    make the rest invisible inside it — `memory_context` among them, which `respond`
    injects into the prompt for CM-7.

    `config` is forwarded so callbacks and tracing propagate the way they do for a
    sub-graph node.
    """

    def node(state: ConversationState, config: RunnableConfig) -> dict:
        return subgraph.invoke(replace(state, replies=[]), config)

    return node


def build_graph():
    """Build the compiled conversation graph (B3 flow + T4.2/T4.4 gates).

    H2 (PR 2): ``orchestrate`` replaces ``route`` after the deterministic gate
    prefix (AO-4). The gates stay the outer envelope; the orchestrator runs on
    the clear path (after ``handoff_gate``) and dispatches KB retrieval intents
    to the research_triage sub-graph, preserving capture/respond/handoff.
    """
    research_triage = build_research_triage_subgraph()
    builder = StateGraph(ConversationState)
    builder.add_node("emergency_gate", emergency_gate)
    builder.add_node("cost_gate", cost_gate)
    builder.add_node("handoff_gate", handoff_gate)
    builder.add_node("closure_gate", closure_gate)
    builder.add_node("receive", receive)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("orchestrate", orchestrate)
    builder.add_node("capture", capture)
    builder.add_node("booking", booking)
    builder.add_node("manage", manage)
    builder.add_node("respond", respond)
    builder.add_node("summary", summary)
    builder.add_node("emergency", emergency)
    builder.add_node("handoff", handoff)
    builder.add_node("research_triage", _triage_node(research_triage))

    builder.add_edge(START, "emergency_gate")
    builder.add_conditional_edges(
        "emergency_gate",
        _after_emergency_gate,
        {"emergency": "emergency", "handoff": "handoff", "cost_gate": "cost_gate"},
    )
    builder.add_conditional_edges(
        "cost_gate",
        _after_cost_gate,
        {"handoff": "handoff", "handoff_gate": "handoff_gate"},
    )
    builder.add_conditional_edges(
        "handoff_gate",
        _after_handoff_gate,
        {"handoff": "handoff", "booking": "booking", "manage": "manage", "closure_gate": "closure_gate"},
    )
    builder.add_conditional_edges(
        "closure_gate",
        _after_closure_gate,
        {END: END, "receive": "receive"},
    )
    builder.add_conditional_edges(
        "receive",
        _flow_start,
        {"classify_intent": "classify_intent", END: END},
    )
    builder.add_edge("classify_intent", "orchestrate")
    builder.add_conditional_edges(
        "orchestrate",
        _route_path,
        {
            "capture": "capture",
            "manage": "manage",
            "research": "research_triage",
            "respond": "respond",
            "handoff": "handoff",
        },
    )
    builder.add_conditional_edges("capture", _after_capture, {"booking": "booking", "summary": "summary", END: END})
    builder.add_conditional_edges("booking", _after_booking, {"summary": "summary", "handoff": "handoff", END: END})
    builder.add_conditional_edges("manage", _after_manage, {"summary": "summary", "handoff": "handoff", END: END})
    builder.add_conditional_edges("respond", _after_respond, {"handoff": "handoff", END: END})
    builder.add_conditional_edges(
        "research_triage",
        _after_research_triage,
        {"capture": "capture", END: END},
    )
    builder.add_edge("handoff", END)
    builder.add_edge("emergency", END)
    builder.add_edge("summary", END)
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
    as outbound messages, and returns them for sending (T3.6). On the first turn
    the greeting chosen by `receive` is fused with the turn's answer into a
    single message (CM-1), so the customer never receives a greeting and an
    answer as two separate messages.
    """
    state = ConversationState.from_db(
        session, message.conversation_id, through_message_id=message.id
    )
    result = build_graph().invoke(state)
    replies = result.get("replies") or []
    greeting = result.get("first_turn_greeting") or ""
    if greeting:
        replies = [f"{greeting}\n\n{replies[0]}", *replies[1:]] if replies else [greeting]
    persist_replies(session, state, replies)
    # CM-8: flush any memory written during the turn before END so the next
    # turn's from_db sees it (per-turn session memory).
    persist_memory_session(session, state)
    return replies
