"""research_triage sub-graph (H2 router, slice-1; AO-5/AO-8).

Thin sub-graph wrapping the vetted KB nodes for KB retail intents
(valores/postventa, RETRIEVAL_INTENTS). Entered by the parent graph after the
``orchestrate`` node dispatches ``next_step == research``; the parent's
``classify_intent`` already ran, so this sub-graph consumes its output (AO-5:
wrap, don't re-implement — re-running classification here would waste an LLM
call per turn, AO-10).

Flow:

    START -> kb_check
        kb_check: kb.retrieve
            hit    -> respond  (reused, unchanged)
            miss   -> retry(<=1, triage_retry) -> kb_check # AO-8 bounded
            miss++ -> handoff (reused, unchanged)

Reuse contract:
- ``respond`` and ``handoff`` are the EXISTING nodes, invoked unchanged.
- AO-6 whitelist: before the service call the sub-agent's ``tools_whitelist``
  is checked for ``kb.retrieve`` (assert-in-dispatch); a non-whitelisted call
  is logged and handed off.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.agent_registry import RegistryError, get_registry
from app.chat.nodes import respond as respond_node
from app.chat.nodes.handoff import handoff
from app.chat.nodes.orchestrate import RESEARCH_TRIAGE, is_tool_whitelisted
from app.chat.state import ConversationState
from app.db import session_scope
from app.services.realtime import record_activity

logger = logging.getLogger(__name__)

# The only service call the research sub-graph makes (AO-6).
_RETRIEVE_TOOL = "kb.retrieve"

# One allowed retry before handoff (AO-8, design D7).
MAX_TRIAGE_RETRIES = 1


def _current_text(state: ConversationState) -> str:
    return state.window[-1]["text"] if state.window else ""


def _kb_check(state: ConversationState) -> dict:
    """Retrieval guard: hit -> respond; miss -> bounded retry -> handoff.

    Also enforces the AO-6 whitelist before the service call: ``kb.retrieve``
    must be within the sub-agent's ``tools_whitelist``, else log + handoff.
    """
    whitelist = _sub_whitelist()
    if not is_tool_whitelisted(whitelist, _RETRIEVE_TOOL):
        logger.warning(
            "research_triage whitelist blocks %s; handing off conversation %s",
            _RETRIEVE_TOOL,
            state.conversation_id,
        )
        return {
            "next_step": "handoff",
            "escalate": True,
            "escalate_reason": "tool_not_whitelisted",
        }

    text = _current_text(state)
    if not text:
        return {"next_step": "respond"}

    with session_scope() as session:
        # The shared helper (app/chat/nodes/respond.py) tries the customer text
        # first and falls back to the classified `service` on a miss, so a
        # wording problem cannot derive a conversation the KB can answer.
        chunks = respond_node.retrieve_chunks(session, state)
        if chunks:
            record_activity(
                session,
                state.conversation_id,
                "kb_retrieved",
                cause=f"chunks:{len(chunks)}",
                actor="bot",
            )
    if chunks:
        # Scoped hit — delegate the grounded answer to the reused respond node.
        return {"next_step": "respond"}

    # Scoped miss. Bounded retry (AO-8): one more attempt, then handoff.
    if state.triage_retry >= MAX_TRIAGE_RETRIES:
        # Preserve CM-6: log the unresolved question before handing off (the
        # research miss never reaches respond's own log_unresolved).
        message_id = state.window[-1]["id"] if state.window else None
        if message_id is not None:
            with session_scope() as session:
                respond_node.log_unresolved(
                    session, message_id=message_id, context=f"intent={state.intent}"
                )
        return {
            "next_step": "handoff",
            "escalate": True,
            "escalate_reason": "kb_miss",
        }
    return {"next_step": "retry", "triage_retry": state.triage_retry + 1}


def _sub_whitelist() -> tuple[str, ...] | None:
    try:
        sub = get_registry().sub_agents.get(RESEARCH_TRIAGE)
    except RegistryError:
        return None
    return sub.tools_whitelist if sub is not None else None


def _after_kb_check(state: ConversationState) -> str:
    return state.next_step


def _after_respond_in_subgraph(state: ConversationState) -> str:
    # respond may escalate its own KB miss (CM-4); converge on the sub-graph's
    # handoff node so the turn terminates with the deriva bundle.
    return "handoff" if state.escalate else END


def build_research_triage_subgraph():
    """Compile the research_triage sub-graph over ConversationState."""
    builder = StateGraph(ConversationState)
    builder.add_node("kb_check", _kb_check)
    builder.add_node("respond", respond_node.respond)
    builder.add_node("handoff", handoff)
    builder.add_edge(START, "kb_check")
    builder.add_conditional_edges(
        "kb_check",
        _after_kb_check,
        {"respond": "respond", "retry": "kb_check", "handoff": "handoff"},
    )
    builder.add_conditional_edges(
        "respond",
        _after_respond_in_subgraph,
        {"handoff": "handoff", END: END},
    )
    builder.add_edge("handoff", END)
    return builder.compile()
