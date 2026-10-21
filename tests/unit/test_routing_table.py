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

`consulta` is in RETRIEVAL_INTENTS: a question *about* an appliance is answered from the
KB, while a reported problem with one keeps starting the visit capture. The appliance
intents and `solicitar_visita` are unchanged. See
`odd/tasks/classify-question-vs-problem.md`.

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


@pytest.mark.parametrize("intent", ["valores", "postventa", "consulta"])
def test_retrieval_intents_route_to_research(intent):
    result = _dispatch(intent)
    assert result["next_step"] == "research"
    assert result.get("active_sub_agent") == "research_triage"


def test_consulta_does_not_route_to_capture():
    """A question about an appliance must not start the visit-capture flow.

    The measured cost of the coarse vocabulary (odd/tasks/kb-answer-fidelity.md, F4):
    14 of 30 answerable queries started capture, and the plainly informational ones
    got "¿Cuál es tu nombre?" instead of the answer the KB already held.
    """
    result = _dispatch("consulta")
    assert result["next_step"] != "capture"


# --- picked preset -> respond (pre-empts the retrieval answer path, T5) ------
# The classifier picks a preset per turn; if one was picked it must answer the
# turn directly so a KB miss cannot hand it off. Capture/manage flows are NOT
# pre-empted.


@pytest.mark.parametrize("intent", ["valores", "postventa", "consulta"])
def test_retrieval_intent_with_picked_template_answers_directly(intent):
    assert _dispatch(intent, template_id="horarios") == {"next_step": "respond"}


def test_retrieval_without_template_still_researches():
    assert _dispatch("consulta", template_id=None) == {
        "next_step": "research", "active_sub_agent": "research_triage"
    }


def test_capture_intent_with_template_keeps_capturing():
    assert _dispatch("calefont", template_id="horarios") == {"next_step": "capture"}


def test_manage_intent_with_template_keeps_managing():
    assert _dispatch("cancelar_visita", template_id="horarios")["next_step"] == "manage"


def test_mid_capture_retrieval_with_template_stays_in_capture_flow():
    assert _dispatch("consulta", mid_capture=True, template_id="x") == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


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


@pytest.mark.parametrize("intent", ["valores", "consulta", "postventa"])
def test_mid_capture_retrieval_intents_answer_then_resume(intent):
    assert _dispatch(intent, mid_capture=True) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


@pytest.mark.parametrize("intent", ["unknown", "calefont", "cancelar_visita", "reagendar_visita"])
def test_mid_capture_non_retrieval_is_pending_field_answer(intent):
    assert _dispatch(intent, mid_capture=True) == {"next_step": "capture"}


def test_mid_capture_persona_still_escalates():
    result = _dispatch("persona", mid_capture=True)
    assert result["next_step"] == "handoff"
    assert result["escalate"] is True


def test_non_mid_capture_dispatch_is_unchanged():
    assert _dispatch("valores") == {
        "next_step": "research", "active_sub_agent": "research_triage"
    }
    assert _dispatch("unknown") == {"next_step": "respond"}


@pytest.mark.parametrize("intent", ["calefont", "caldera", "calefaccion", "unknown"])
def test_mid_capture_question_shape_answers_then_resumes(intent):
    """S16: a question with a capture intent is answered, never stored as the field.

    '¿qué calefont me recomiendan?' classifies as `calefont`, which is a capture
    intent: without the question flag it would be written as the pending field.
    """
    assert _dispatch(intent, mid_capture=True, question=True) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_a_statement_with_a_capture_intent_stays_a_field_answer():
    assert _dispatch("calefont", mid_capture=True, question=False) == {"next_step": "capture"}
