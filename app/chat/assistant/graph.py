"""LangGraph runtime for panel assistant requests."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.chat.assistant.nodes import approval_gate, collect_evidence, execute, plan
from app.chat.assistant.state import AssistantState


def _after_approval(state: AssistantState) -> str:
    return END if state.get("status") == "approval_pending" else "execute"


def build_assistant_graph():
    builder = StateGraph(AssistantState)
    builder.add_node("plan", plan)
    builder.add_node("approval", approval_gate)
    builder.add_node("execute", execute)
    builder.add_node("evidence", collect_evidence)
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "approval")
    builder.add_conditional_edges("approval", _after_approval, {"execute": "execute", END: END})
    builder.add_edge("execute", "evidence")
    builder.add_edge("evidence", END)
    return builder.compile()


def run_assistant(*, thread_id: int, user_id: int, content: str, run_id: str, on_token=None, session=None, actor=None, attachments=None, context=None) -> AssistantState:
    state: AssistantState = {
        "thread_id": thread_id,
        "user_id": user_id,
        "content": content,
        "run_id": run_id,
        "evidence": [],
        "on_token": on_token,
        "session": session,
        "actor": actor,
        "attachments": attachments or [],
        "context": context or {"items": [], "meta": {}},
    }
    return build_assistant_graph().invoke(state)
