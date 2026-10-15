"""LangGraph runtime for panel assistant requests."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.chat.assistant.nodes import (
    assemble_context_node,
    collect_evidence,
    delegation_node,
    execute,
    guardrails,
    memory_bootstrap,
    panel_cost_gate,
    plan_llm,
    retrieve_kb,
    tool_loop_head,
    verify_effects,
)
from app.chat.assistant.state import AssistantState


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
    if decision in {"grounding_refusal", "delegate_refused"}:
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
    return "plan_llm" if state.get("status") == "planned" else "verify_effects"


def _after_plan(state: AssistantState) -> str:
    return "guardrails"


def _after_memory_bootstrap(state: AssistantState) -> str:
    # A resumed approval carries the exact plan it was approved for. Re-planning would
    # break the binding (the token is hashed against those arguments), so the stored
    # plan goes straight to guardrails and executes, then the loop continues normally.
    return "guardrails" if state.get("resume") else "plan_llm"


def _after_cost_gate(state: AssistantState) -> str:
    return "evidence" if state.get("cost_mode") == "blocked" else "memory_bootstrap"


def build_assistant_graph():
    builder = StateGraph(AssistantState)
    builder.add_node("assemble_context", assemble_context_node)
    builder.add_node("panel_cost_gate", panel_cost_gate)
    builder.add_node("memory_bootstrap", memory_bootstrap)
    builder.add_node("plan_llm", plan_llm)
    builder.add_node("guardrails", guardrails)
    builder.add_node("delegation_span", delegation_node)
    builder.add_node("retrieve_kb", retrieve_kb)
    builder.add_node("execute_tool", execute)
    builder.add_node("tool_loop_head", tool_loop_head)
    builder.add_node("verify_effects", verify_effects)
    builder.add_node("respond_stream", execute)
    builder.add_node("evidence", collect_evidence)
    builder.add_edge(START, "assemble_context")
    builder.add_edge("assemble_context", "panel_cost_gate")
    builder.add_conditional_edges("panel_cost_gate", _after_cost_gate, {"memory_bootstrap": "memory_bootstrap", "evidence": "evidence"})
    builder.add_conditional_edges("memory_bootstrap", _after_memory_bootstrap, {"plan_llm": "plan_llm", "guardrails": "guardrails"})
    builder.add_conditional_edges(
        "plan_llm", _after_plan,
        {"guardrails": "guardrails"},
    )
    builder.add_conditional_edges("guardrails", _after_guardrails, {"execute_tool": "execute_tool", "delegation_span": "delegation_span", "retrieve_kb": "retrieve_kb", "respond_stream": "respond_stream", END: END})
    builder.add_edge("delegation_span", "respond_stream")
    builder.add_conditional_edges("retrieve_kb", _after_retrieve_kb, {"respond_stream": "respond_stream", END: END})
    builder.add_conditional_edges("execute_tool", _after_execute, {"tool_loop_head": "tool_loop_head", END: END})
    builder.add_conditional_edges("tool_loop_head", _after_tool_loop, {"plan_llm": "plan_llm", "verify_effects": "verify_effects"})
    builder.add_edge("verify_effects", "respond_stream")
    builder.add_edge("respond_stream", "evidence")
    builder.add_edge("evidence", END)
    return builder.compile()


def run_assistant(*, thread_id: int, user_id: int, content: str, run_id: str, request_message_id: int | None = None, on_token=None, on_stage=None, session=None, actor=None, actor_role=None, sdb_requested=None, attachments=None, context=None, compaction=None, project_authorization=None, cortex_session=None, resume_plan: dict | None = None, resume_approval: dict | None = None, resume_tool_results: list[dict] | None = None, resume_tool_steps: int | None = None) -> AssistantState:
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
    if resume_plan is not None:
        # Re-entry after an approved write: the stored plan and its consumed approval go
        # into the graph so the write executes in place and the loop continues from it.
        # A persisted plan may predate `kind` (the pre-planner approval fallback), so derive
        # it instead of trusting a missing key to route the turn.
        plan = dict(resume_plan)
        plan.setdefault("kind", "tool" if plan.get("tool") else "respond")
        state["plan"] = plan
        state["approval"] = resume_approval
        state["planner"] = {"valid": True}
        state["status"] = "planned"
        state["resume"] = True
        # A chain that paused on its second write resumes with the evidence the earlier
        # steps produced: that evidence is what the continuation step plans from.
        state["tool_results"] = list(resume_tool_results or [])
        state["tool_steps"] = resume_tool_steps or 0
    graph = build_assistant_graph()
    if on_stage is None:
        return graph.invoke(state)
    last_state = None
    stage_nodes = {
        "assemble_context": "planning", "panel_cost_gate": "planning", "plan_llm": "planning",
        "guardrails": "planning", "execute_tool": "executing",
        "respond_stream": "streaming",
        "tool_loop_head": "planning",
        "verify_effects": "verifying",
    }
    current_stage = "planning"
    for mode, chunk in graph.stream(state, stream_mode=["values", "updates"]):
        if mode == "values":
            last_state = chunk
        else:
            for node in chunk:
                current_stage = stage_nodes.get(node, current_stage)
                on_stage(current_stage)
    return last_state
