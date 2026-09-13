"""LangGraph runtime for panel assistant requests."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.chat.assistant.nodes import (
    assemble_context_node,
    collect_evidence,
    cortex_session_gate,
    cortex_session_turn,
    execute,
    guardrails,
    panel_cost_gate,
    plan_llm,
    sdb_approve,
    sdb_clarify,
    sdb_deliver,
    sdb_execute,
    sdb_plan,
    sdb_spec,
    sdb_verify,
)
from app.chat.assistant.state import AssistantState, normalize_sdb_trigger


def sdb_trigger_gate(state: AssistantState) -> AssistantState:
    """Select SDB only from validated planner or authenticated admin signals."""
    planner = state.get("planner") or state.get("plan") or {}
    signal = {
        "classification": planner.get("classification", "normal"),
        "sdb_requested": state.get("sdb_requested"),
        "actor_role": state.get("actor_role") or state.get("actor"),
    }
    normalized = normalize_sdb_trigger(signal)
    if normalized["route"] == "sdb":
        return {
            "sdb_route": "sdb",
            "sdb_trigger": normalized["trigger"],
            "sdb_phase": normalized["phase"],
            "sdb_rejection": None,
            "status": "sdb_clarify",
        }
    return {
        "sdb_route": "normal",
        "sdb_trigger": None,
        "sdb_rejection": normalized.get("reason"),
    }


def _after_sdb_trigger_gate(state: AssistantState) -> str:
    return "sdb_clarify" if state.get("sdb_route") == "sdb" else "guardrails"


def _after_cortex_gate(state: AssistantState) -> str:
    return "cortex_turn" if state.get("cortex_route") == "cortex" else "sdb_trigger_gate"


def _after_guardrails(state: AssistantState) -> str:
    if state.get("status") == "approval_pending":
        return END
    return "execute_tool" if state.get("plan", {}).get("kind") == "tool" else "respond_stream"


def _after_cost_gate(state: AssistantState) -> str:
    return "evidence" if state.get("cost_mode") == "blocked" else "plan_llm"


def _after_sdb_approve(state: AssistantState) -> str:
    return "sdb_execute" if (state.get("approval") or {}).get("status") == "consumed" else END


def build_assistant_graph():
    builder = StateGraph(AssistantState)
    builder.add_node("assemble_context", assemble_context_node)
    builder.add_node("panel_cost_gate", panel_cost_gate)
    builder.add_node("plan_llm", plan_llm)
    builder.add_node("cortex_session_gate", cortex_session_gate)
    builder.add_node("cortex_turn", cortex_session_turn)
    builder.add_node("sdb_trigger_gate", sdb_trigger_gate)
    builder.add_node("sdb_clarify", sdb_clarify)
    builder.add_node("sdb_spec", sdb_spec)
    builder.add_node("sdb_plan", sdb_plan)
    builder.add_node("sdb_approve", sdb_approve)
    builder.add_node("sdb_execute", sdb_execute)
    builder.add_node("sdb_verify", sdb_verify)
    builder.add_node("sdb_deliver", sdb_deliver)
    builder.add_node("guardrails", guardrails)
    builder.add_node("execute_tool", execute)
    builder.add_node("respond_stream", execute)
    builder.add_node("evidence", collect_evidence)
    builder.add_edge(START, "assemble_context")
    builder.add_edge("assemble_context", "panel_cost_gate")
    builder.add_conditional_edges("panel_cost_gate", _after_cost_gate, {"plan_llm": "plan_llm", "evidence": "evidence"})
    builder.add_edge("plan_llm", "cortex_session_gate")
    builder.add_conditional_edges(
        "cortex_session_gate", _after_cortex_gate,
        {"cortex_turn": "cortex_turn", "sdb_trigger_gate": "sdb_trigger_gate"},
    )
    builder.add_edge("cortex_turn", "evidence")
    builder.add_conditional_edges(
        "sdb_trigger_gate", _after_sdb_trigger_gate,
        {"guardrails": "guardrails", "sdb_clarify": "sdb_clarify"},
    )
    builder.add_edge("sdb_clarify", "sdb_spec")
    builder.add_edge("sdb_spec", "sdb_plan")
    builder.add_edge("sdb_plan", "sdb_approve")
    builder.add_conditional_edges("sdb_approve", _after_sdb_approve, {"sdb_execute": "sdb_execute", END: END})
    builder.add_edge("sdb_execute", "sdb_verify")
    builder.add_edge("sdb_verify", "sdb_deliver")
    builder.add_edge("sdb_deliver", "evidence")
    builder.add_conditional_edges("guardrails", _after_guardrails, {"execute_tool": "execute_tool", "respond_stream": "respond_stream", END: END})
    builder.add_edge("execute_tool", "evidence")
    builder.add_edge("respond_stream", "evidence")
    builder.add_edge("evidence", END)
    return builder.compile()


def run_assistant(*, thread_id: int, user_id: int, content: str, run_id: str, request_message_id: int | None = None, on_token=None, session=None, actor=None, actor_role=None, sdb_requested=None, attachments=None, context=None, compaction=None, project_authorization=None, cortex_session=None) -> AssistantState:
    if project_authorization is not None:
        from app.services.projects import _ProjectAuthorization
        if not isinstance(project_authorization, _ProjectAuthorization):
            raise ValueError("SDB project selection requires an authorized project capability")
    state: AssistantState = {
        "thread_id": thread_id,
        "user_id": user_id,
        "content": content,
        "run_id": run_id,
        "request_message_id": request_message_id,
        "evidence": [],
        "on_token": on_token,
        "session": session,
        "actor": actor,
        "actor_role": actor_role,
        "sdb_requested": sdb_requested,
        "project_authorization": project_authorization,
        "attachments": attachments or [],
        "context": context or {"items": [], "meta": {}},
        "context_meta": (context or {}).get("meta", {}),
        "projection_evidence": (context or {}).get("meta", {}),
        "compaction": compaction or {},
        "cortex_session": cortex_session,
    }
    return build_assistant_graph().invoke(state)
