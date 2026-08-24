"""Routing table coverage for the orchestrator dispatch (h2-router, PR 2).

AO-3: the orchestrator selects a destination via a pure ``(intent, flags)``
function with NO LLM. Every row of the design.md dispatch table is tested
here 1:1:

| Intent / condition   | Flags                            | Dispatch            |
|----------------------|----------------------------------|---------------------|
| any (post-gates)     | escalate=True                    | handoff (escalation)|
| persona              | —                                | handoff (persona)   |
| emergencia           | emergency=True                   | handoff (emergencia)|
| injection            | escalate=True                    | handoff (injection) |
| CAPTURE_INTENTS      | —                                | capture             |
| RETRIEVAL_INTENTS    | —                                | research_triage     |
| unknown (1st, no esc)| —                                | respond             |
| anything else        | —                                | respond             |

RED-first: ``app.chat.nodes.orchestrate._dispatch`` does not exist until task
2.4 creates the node module, so every assertion fails on import until then.
"""

from __future__ import annotations

import pytest

from app.chat.nodes.orchestrate import _dispatch, is_tool_whitelisted


# --- escalate flag -> handoff (escalation), reason preserved -----------------


def test_any_intent_with_escalate_flag_routes_to_handoff():
    # 2x unknown / injection / SS-1 always_escalate set escalate=True in
    # classify_intent; the orchestrator must forward that to handoff without
    # re-evaluating the intent (design row "any (post-gates)").
    result = _dispatch("valores", escalate=True, escalate_reason="unknown_intent_twice")
    assert result["next_step"] == "handoff"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "unknown_intent_twice"


def test_capture_intent_with_escalate_flag_still_handoffs():
    # Escalation outranks even a capture intent (escalate wins over category).
    result = _dispatch("calefont", escalate=True, escalate_reason="scope_always_escalate")
    assert result["next_step"] == "handoff"
    assert result["escalate_reason"] == "scope_always_escalate"


# --- persona / emergencia / injection -> handoff (by intent) -----------------


def test_persona_routes_to_handoff_with_reason():
    result = _dispatch("persona")
    assert result["next_step"] == "handoff"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "persona"


def test_emergencia_routes_to_handoff_with_emergency_flag():
    result = _dispatch("emergencia", emergency=True)
    assert result["next_step"] == "handoff"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "emergencia"
    assert result["emergency"] is True


def test_injection_routes_to_handoff_with_reason():
    # classify_intent already set escalate + reason (injection_detected); the
    # orchestrator forwards it unchanged (design row "injection | escalate").
    result = _dispatch(
        "injection", escalate=True, escalate_reason="injection_detected"
    )
    assert result["next_step"] == "handoff"
    assert result["escalate"] is True
    assert result["escalate_reason"] == "injection_detected"


# --- CAPTURE_INTENTS -> capture ----------------------------------------------


@pytest.mark.parametrize("intent", ["calefont", "caldera", "calefaccion", "solicitar_visita"])
def test_capture_intents_route_to_capture(intent):
    result = _dispatch(intent)
    assert result["next_step"] == "capture"


# --- RETRIEVAL_INTENTS -> research_triage ------------------------------------


@pytest.mark.parametrize("intent", ["valores", "postventa"])
def test_retrieval_intents_route_to_research(intent):
    result = _dispatch(intent)
    assert result["next_step"] == "research"
    assert result.get("active_sub_agent") == "research_triage"


# --- unknown (no escalate) -> respond (clarification) ------------------------


def test_unknown_without_escalate_routes_to_respond():
    result = _dispatch("unknown")
    assert result["next_step"] == "respond"


# --- anything else -> respond (linear) ---------------------------------------


def test_other_intents_route_to_respond():
    result = _dispatch("exotico")
    assert result["next_step"] == "respond"


# --- AO-6 tools whitelist thin boundary --------------------------------------


def test_whitelisted_tool_allowed():
    # research_triage whitelist declares kb.retrieve -> the call proceeds.
    assert is_tool_whitelisted(("kb.retrieve",), "kb.retrieve") is True


def test_non_whitelisted_tool_denied():
    # A sub-agent must not call a service outside its whitelist.
    assert is_tool_whitelisted(("kb.retrieve",), "kb.query") is False


def test_empty_whitelist_denies_everything():
    # No whitelist (None or empty) -> every tool call is blocked.
    assert is_tool_whitelisted((), "kb.retrieve") is False
    assert is_tool_whitelisted(None, "kb.retrieve") is False
