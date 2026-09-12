"""LangGraph runtime for panel assistant requests."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.chat.assistant.nodes import (
    assemble_context_node,
    collect_evidence,
    execute,
    guardrails,
    panel_cost_gate,
    plan_llm,
)
from app.chat.assistant.state import AssistantState


def _after_guardrails(state: AssistantState) -> str:
    if state.get("status") == "approval_pending":
        return END
    return "execute_tool" if state.get("plan", {}).get("kind") == "tool" else "respond_stream"


def _after_cost_gate(state: AssistantState) -> str:
    return "evidence" if state.get("cost_mode") == "blocked" else "plan_llm"


def build_assistant_graph():
    builder = StateGraph(AssistantState)
    builder.add_node("assemble_context", assemble_context_node)
    builder.add_node("panel_cost_gate", panel_cost_gate)
    builder.add_node("plan_llm", plan_llm)
    builder.add_node("guardrails", guardrails)
    builder.add_node("execute_tool", execute)
    builder.add_node("respond_stream", execute)
    builder.add_node("evidence", collect_evidence)
    builder.add_edge(START, "assemble_context")
    builder.add_edge("assemble_context", "panel_cost_gate")
    builder.add_conditional_edges("panel_cost_gate", _after_cost_gate, {"plan_llm": "plan_llm", "evidence": "evidence"})
    builder.add_edge("plan_llm", "guardrails")
    builder.add_conditional_edges("guardrails", _after_guardrails, {"execute_tool": "execute_tool", "respond_stream": "respond_stream", END: END})
    builder.add_edge("execute_tool", "evidence")
    builder.add_edge("respond_stream", "evidence")
    builder.add_edge("evidence", END)
    return builder.compile()


def run_assistant(*, thread_id: int, user_id: int, content: str, run_id: str, on_token=None, session=None, actor=None, attachments=None, context=None, compaction=None) -> AssistantState:
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
        "context_meta": (context or {}).get("meta", {}),
        "projection_evidence": (context or {}).get("meta", {}),
        "compaction": compaction or {},
    }
    return build_assistant_graph().invoke(state)
