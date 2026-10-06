"""LangGraph runtime for panel assistant requests."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.chat.assistant.nodes import (
    assemble_context_node,
    collect_evidence,
    delegation_node,
    execute,
    guardrails,
    panel_cost_gate,
    plan_llm,
    retrieve_kb,
    sdb_approve,
    sdb_clarify,
    sdb_deliver,
    sdb_execute,
    sdb_plan,
    sdb_spec,
    sdb_verify,
    tool_loop_head,
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


# Stages where the model's own output was unusable. A provider or instrumentation failure is not a plan:
# it keeps its existing path, where the responder is attempted and a second failure leaves the turn
# recoverable instead of quietly answering with a summary.
_PLAN_FAILURE_STAGES = frozenset({"extraction", "completion", "parse", "guardrails"})


def _is_terminal_plan_failure(state: AssistantState) -> bool:
    """True when the turn was degraded by an unusable plan rather than by infrastructure failing."""
    if (state.get("guardrails") or {}).get("decision") != "fallback":
        return False
    stage = ((state.get("planner") or {}).get("failure") or {}).get("stage")
    return stage in _PLAN_FAILURE_STAGES


def _after_guardrails(state: AssistantState) -> str:
    if state.get("status") == "approval_pending":
        return END
    # A fallback plan is not a plan: it carries `kind: "respond"` only so the turn can end with the
    # bounded summary. Handing it to the responder would dress the failure as a normal answer.
    if _is_terminal_plan_failure(state):
        return END
    decision = (state.get("guardrails") or {}).get("decision")
    if decision in {"grounding_refusal", "loop_write_refused", "delegate_refused"}:
        return END
    if decision == "delegate":
        return "delegation_span"
    if decision == "retrieve_kb":
        return "retrieve_kb"
    return "execute_tool" if state.get("plan", {}).get("kind") == "tool" else "respond_stream"


def _after_retrieve_kb(state: AssistantState) -> str:
    return END if (state.get("guardrails") or {}).get("decision") in {"grounding_refusal", "kb_unavailable"} else "respond_stream"


def _after_execute(state: AssistantState) -> str:
    return "tool_loop_head" if state.get("status") in {"completed", "degraded"} else END


def _after_tool_loop(state: AssistantState) -> str:
    return "plan_llm" if state.get("status") == "planned" else "respond_stream"


def _after_plan(state: AssistantState) -> str:
    return "guardrails"


def _after_cost_gate(state: AssistantState) -> str:
    return "evidence" if state.get("cost_mode") == "blocked" else "plan_llm"


def _after_sdb_approve(state: AssistantState) -> str:
    return "sdb_execute" if (state.get("approval") or {}).get("status") == "consumed" else END


def build_assistant_graph():
    builder = StateGraph(AssistantState)
    builder.add_node("assemble_context", assemble_context_node)
    builder.add_node("panel_cost_gate", panel_cost_gate)
    builder.add_node("plan_llm", plan_llm)
    builder.add_node("sdb_trigger_gate", sdb_trigger_gate)
    builder.add_node("sdb_clarify", sdb_clarify)
    builder.add_node("sdb_spec", sdb_spec)
    builder.add_node("sdb_plan", sdb_plan)
    builder.add_node("sdb_approve", sdb_approve)
    builder.add_node("sdb_execute", sdb_execute)
    builder.add_node("sdb_verify", sdb_verify)
    builder.add_node("sdb_deliver", sdb_deliver)
    builder.add_node("guardrails", guardrails)
    builder.add_node("delegation_span", delegation_node)
    builder.add_node("retrieve_kb", retrieve_kb)
    builder.add_node("execute_tool", execute)
    builder.add_node("tool_loop_head", tool_loop_head)
    builder.add_node("respond_stream", execute)
    builder.add_node("evidence", collect_evidence)
    builder.add_edge(START, "assemble_context")
    builder.add_edge("assemble_context", "panel_cost_gate")
    builder.add_conditional_edges("panel_cost_gate", _after_cost_gate, {"plan_llm": "plan_llm", "evidence": "evidence"})
    builder.add_conditional_edges(
        "plan_llm", _after_plan,
        {"guardrails": "guardrails"},
    )
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
    builder.add_conditional_edges("guardrails", _after_guardrails, {"execute_tool": "execute_tool", "delegation_span": "delegation_span", "retrieve_kb": "retrieve_kb", "respond_stream": "respond_stream", END: END})
    builder.add_edge("delegation_span", "respond_stream")
    builder.add_conditional_edges("retrieve_kb", _after_retrieve_kb, {"respond_stream": "respond_stream", END: END})
    builder.add_conditional_edges("execute_tool", _after_execute, {"tool_loop_head": "tool_loop_head", END: END})
    builder.add_conditional_edges("tool_loop_head", _after_tool_loop, {"plan_llm": "plan_llm", "respond_stream": "respond_stream"})
    builder.add_edge("respond_stream", "evidence")
    builder.add_edge("evidence", END)
    return builder.compile()


def run_assistant(*, thread_id: int, user_id: int, content: str, run_id: str, request_message_id: int | None = None, on_token=None, on_stage=None, session=None, actor=None, actor_role=None, sdb_requested=None, attachments=None, context=None, compaction=None, project_authorization=None, cortex_session=None) -> AssistantState:
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
        "tool_results": [],
        "tool_steps": 0,
    }
    graph = build_assistant_graph()
    if on_stage is None:
        return graph.invoke(state)
    last_state = None
    stage_nodes = {
        "assemble_context": "planning", "panel_cost_gate": "planning", "plan_llm": "planning",
        "guardrails": "planning", "sdb_trigger_gate": "planning",
        "sdb_clarify": "planning", "sdb_spec": "planning",
        "sdb_plan": "planning", "sdb_approve": "planning", "sdb_execute": "executing",
        "sdb_verify": "executing", "sdb_deliver": "responding", "execute_tool": "executing",
        "respond_stream": "streaming",
        "tool_loop_head": "planning",
    }
    for mode, chunk in graph.stream(state, stream_mode=["values", "updates"]):
        if mode == "values":
            last_state = chunk
        else:
            for node in chunk:
                stage = stage_nodes.get(node)
                if stage:
                    on_stage(stage)
    return last_state
