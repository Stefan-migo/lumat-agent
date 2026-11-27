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

from app.chat.nodes.orchestrate import _dispatch, is_tool_whitelisted, orchestrate
from app.chat.state import ConversationState


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


@pytest.mark.parametrize("intent", ["unknown", "calefont"])
def test_mid_capture_non_retrieval_is_pending_field_answer(intent):
    assert _dispatch(intent, mid_capture=True) == {"next_step": "capture"}


@pytest.mark.parametrize("intent", ["cancelar_visita", "reagendar_visita"])
def test_mid_capture_visit_management_is_not_a_field_answer(intent):
    """S12: production #23 turn 289 asked "¿Quiero reagendar la visita es posible?" and
    got "¿En qué comuna te encuentras?" back, because CI-2 treated the request as an
    answer to the pending field."""
    assert _dispatch(intent, mid_capture=True) == {"next_step": "manage"}


# --- S1/S2 (agenda-respeta-horario): the question beats a visit change -------


def test_capture_intent_question_routes_to_research_with_or_without_pending_batch():
    expected_pending = {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }
    expected_no_pending = {
        "next_step": "research",
        "active_sub_agent": "research_triage",
    }
    assert _dispatch("solicitar_visita", mid_capture=True, question=True) == expected_pending
    assert _dispatch("solicitar_visita", mid_capture=False, question=True) == expected_no_pending


def test_question_routing_preserves_escalation_change_and_quote_precedence():
    assert _dispatch("persona", question=True)["next_step"] == "handoff"
    assert _dispatch("emergencia", question=True)["next_step"] == "handoff"
    assert _dispatch("injection", question=True)["next_step"] == "handoff"
    assert _dispatch(
        "reagendar_visita", mid_capture=True, question=True, change_request=True
    )["next_step"] == "manage"
    assert _dispatch("caldera", question=True, quote_question=True) == {
        "next_step": "respond"
    }


def test_pendingless_question_does_not_claim_capture_is_paused():
    from app.chat.graph import _after_research_triage

    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        captured={},
        replies=["La atención es de lunes a sábado."],
    )
    assert _after_research_triage(state) == "__end__"
    state.capture_paused = True
    assert _after_research_triage(state) == "capture"


def test_mid_capture_schedule_question_beats_a_visit_change():
    """S1: measured `real-dato-mas-pregunta` and `real-reagenda-familiar`.

    The classifier labels both turns `reagendar_visita`:
    "Yo creo qje no alcanza, y mañana?" and
    "Es factible que vengas un dia pero a las.9 am".  The old dispatch sent them
    to `manage`, which has no visit to move, so it handed off with
    `booking_unavailable` and left the conversation owned by a human: the next
    customer turns got no reply at all.
    """
    assert _dispatch("reagendar_visita", mid_capture=True, question=True) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_mid_capture_explicit_change_request_still_manages():
    """S2: production #23, turn 289 — "Quiero reagendar la visita es posible?".

    S12 closed that defect and it must survive S1: asking to move the visit is a
    request, not a question, even though its surface is interrogative.
    """
    assert (
        _dispatch("reagendar_visita", mid_capture=True, question=True, change_request=True)
        == {"next_step": "manage"}
    )


def test_orchestrate_answers_a_schedule_question_while_capturing():
    """S1 end to end from the text: a KB question interrupting a capture answers.

    The intent here is a capture one, not a reschedule: `reagendar_visita` with no
    upcoming visit is a visit request and lands in capture on purpose (S4).
    """
    state = _capture_state(
        "dime altiro si atienden sabado, eso es lo que necesito saber",
        intent="calefont",
    )

    assert orchestrate(state) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


@pytest.mark.parametrize(
    "text",
    [
        "Favor cambiar la fecha de la manutención para el próximo martes por favor",
        "Favor cambiar el día de la mantención para el próximo martes. Por temas laborales no estaré en casa hoy pm",
        "Favor cambiar la mantención para el próximo martes, y además tengo una consulta",
    ],
)
def test_explicit_change_of_date_or_maintenance_leaves_pending_capture(text):
    state = _capture_state(text, intent="reagendar_visita")

    assert orchestrate(state) == {"next_step": "manage"}


def test_date_or_maintenance_noun_without_change_verb_is_not_a_change_request():
    from app.chat.nodes.orchestrate import asks_for_change

    assert asks_for_change("la fecha de la mantención es el próximo martes") is False


def test_orchestrate_still_manages_an_explicit_reschedule_while_capturing():
    """S2 end to end: the measured #23 sentence keeps routing to manage."""
    state = _capture_state("Quiero reagendar la visita es posible?", intent="reagendar_visita")

    assert orchestrate(state) == {"next_step": "manage"}


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


# --- S4/T4: a schedule question without "?" is answered, then capture resumes ----


def test_schedule_question_vocabulary_is_accent_normalised_and_word_bounded():
    from app.chat.nodes.respond import asks_about_schedule

    assert asks_about_schedule("¿Qué días tienen disponibles?") is True
    assert asks_about_schedule("¿Tienen hora disponible esta semana?") is True
    assert asks_about_schedule("¿Qué agenda tienen disponible?") is True
    assert asks_about_schedule("¿atienden los sábados?") is True
    assert asks_about_schedule("tengo la caldera mala y no sé si el jueves") is False
    assert asks_about_schedule("La caldera está fallando, ¿hay hora disponible?") is False
    assert asks_about_schedule("estoy en providencia") is False


def _capture_state(text, *, pending=("name",), extracted=None, intent="solicitar_visita"):
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        intent=intent,
        captured={"_pending": list(pending), "_asked": {pending[0]: 1}} if pending else {},
        extracted=extracted or {},
        window=[{"id": 1, "text": text}],
    )


def test_a_schedule_question_without_a_question_mark_is_answered_and_resumes():
    """Measured on `simple-horario-sabado`: no "?", and the name was extracted.

    The old `_is_question` required both a "?" and an empty extraction, so the
    sentence was stored as the name and the Saturday question went unanswered.
    """
    state = _capture_state(
        "carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber",
        extracted={"name": "carlos"},
    )

    assert orchestrate(state) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_question_mark_with_extracted_field_answers_then_resumes():
    state = _capture_state(
        "es factible que pases tipo 14 horas?",
        extracted={"availability": "14 horas"},
    )

    assert orchestrate(state) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_inverted_question_with_extracted_field_answers_then_resumes():
    state = _capture_state(
        "¿A las 14 puede ser?",
        extracted={"availability": "14 horas"},
    )

    assert orchestrate(state) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_explicit_interrogative_marker_without_punctuation_answers_then_resumes():
    state = _capture_state("¿me pueden confirmar el horario")

    assert orchestrate(state) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_s4_reschedule_without_upcoming_visit_routes_to_capture_even_with_a_question():
    """S4: no visit to move means a visit request, question or not.

    `agenda-house-2` measured both rows: the same preference sent to the
    answering path came back as a kb_miss offer ("No tengo ese dato. ¿Prefieres
    que te tome los datos…?"), because the customer KB holds no answer about a
    time preference, while capture named it back correctly.
    """
    assert _dispatch("reagendar_visita", has_upcoming_visit=False, question=True) == {
        "next_step": "capture"
    }
    assert _dispatch(
        "reagendar_visita", has_upcoming_visit=False, quote_question=True
    ) == {"next_step": "capture"}


def test_s4_reschedule_without_upcoming_visit_and_without_question_routes_to_capture():
    assert _dispatch("reagendar_visita", has_upcoming_visit=False) == {
        "next_step": "capture"
    }


def test_s4_reschedule_with_upcoming_visit_routes_to_manage():
    assert _dispatch(
        "reagendar_visita", has_upcoming_visit=True, question=True
    ) == {"next_step": "manage"}


def test_s4_cancel_routes_to_manage_without_upcoming_visit():
    assert _dispatch(
        "cancelar_visita", has_upcoming_visit=False, question=True
    ) == {"next_step": "manage"}


def test_s4_mid_capture_dispatch_default_preserves_s12():
    assert _dispatch("reagendar_visita", mid_capture=True) == {
        "next_step": "manage"
    }


def test_interrogative_marker_requires_word_boundary():
    assert orchestrate(_capture_state("los clientespueden revisar el equipo")) == {
        "next_step": "capture"
    }


def test_a_location_statement_mid_capture_stays_a_field_answer():
    """T5/T5a: `estoy en providencia` answers the commune, it does not ask."""
    assert orchestrate(_capture_state("no era calefont, es una caldera, y estoy en providencia")) == {
        "next_step": "capture"
    }


def test_a_plain_answer_mid_capture_stays_a_field_answer():
    assert orchestrate(_capture_state("carlos")) == {"next_step": "capture"}


def test_a_greeting_mid_capture_is_not_a_schedule_question():
    assert orchestrate(_capture_state("hola, buenas")) == {"next_step": "capture"}


def test_a_first_turn_capture_intent_with_coverage_and_price_answers_first():
    state = _capture_state(
        "hola, necesito mantener mi calefont, vivo en ñuñoa",
        pending=(),
        intent="calefont",
    )

    assert orchestrate(state) == {
        "next_step": "research",
        "active_sub_agent": "research_triage",
        "capture_paused": True,
    }


def test_a_location_statement_mid_capture_still_answers_the_field():
    assert orchestrate(_capture_state("vivo en ñuñoa")) == {"next_step": "capture"}


def test_first_turn_answer_then_resume_asks_after_the_answer():
    from app.chat.graph import _after_research_triage

    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        captured={"comuna": "Ñuñoa"},
        capture_paused=True,
        replies=["Atendemos normalmente en Ñuñoa."],
    )
    assert _after_research_triage(state) == "capture"

    state.replies = ["Atendemos normalmente en Ñuñoa. ¿Qué equipo es?"]
    assert _after_research_triage(state) == "__end__"


def test_a_price_question_about_an_unpriced_work_is_answered_not_diagnosed():
    """S2/D8: "cuanto cuesta cambiar la caldera" is measured, and answered.

    The classifier returns `caldera` for it, so `CAPTURE_INTENTS` sent the turn to
    capture and production answered "cuéntame qué pasa con el equipo": the price
    question was never answered and the quote step in `respond` was unreachable.
    """
    state = _capture_state(
        "cuanto cuesta cambiar la caldera", pending=(), intent="caldera"
    )

    assert orchestrate(state) == {"next_step": "respond"}


def test_a_device_report_about_the_same_device_still_starts_the_capture():
    """PRESERVE: the same intent, without a price question, is a fault to capture."""
    state = _capture_state("la caldera no calienta la casa", pending=(), intent="caldera")

    assert orchestrate(state) == {"next_step": "capture"}


def test_a_published_service_price_question_is_not_a_quote_question():
    """The quote step must not pre-empt the tariff: that path answers the figure."""
    from app.chat.nodes.orchestrate import _is_quote_question

    state = _capture_state(
        "cuanto cuesta la mantencion de caldera", pending=(), intent="caldera"
    )

    assert _is_quote_question(state) is False


def test_a_question_about_the_booked_visit_is_answered_not_managed():
    """Measured conversation 50: the customer asks about the visit she holds.

    The classifier returns `consulta`, `reagendar_visita` or `solicitar_visita`
    for that sentence depending on the run, and every one of them ended in a
    different wrong path (free slots, a reschedule menu, the questionnaire). The
    destination is `respond`, where the deterministic status answer reads the
    appointment rows.
    """
    assert _dispatch("consulta", booked_visit_question=True) == {"next_step": "respond"}
    assert _dispatch("reagendar_visita", booked_visit_question=True) == {
        "next_step": "respond"
    }
    assert _dispatch("solicitar_visita", booked_visit_question=True) == {
        "next_step": "respond"
    }


def test_a_booked_visit_question_outranks_the_day_selection_shape():
    """The turn names a weekday and is not a question mark; it is still not a field."""
    assert _dispatch(
        "solicitar_visita", booked_visit_question=True, day_selection=True
    ) == {"next_step": "respond"}


def test_a_change_request_keeps_its_manage_path():
    """S5 (6): asking to move the visit is not asking about the visit."""
    assert _dispatch("reagendar_visita", change_request=True) == {"next_step": "manage"}
    assert _dispatch(
        "reagendar_visita", change_request=True, booked_visit_question=False
    ) == {"next_step": "manage"}


def test_an_emergency_about_a_booked_visit_still_escalates():
    assert _dispatch("emergencia", emergency=True, booked_visit_question=True) == {
        "next_step": "handoff",
        "escalate": True,
        "escalate_reason": "emergencia",
        "emergency": True,
    }


@pytest.mark.parametrize(
    "text, intent",
    [
        ("Tengo una visita para el lunes, puedes confirmarme que tecnico va?", "consulta"),
        ("Tengo una hora agendada para el lunes", "reagendar_visita"),
    ],
)
def test_the_measured_turns_reach_the_answer_path(text, intent):
    """End to end through `orchestrate`, with no conversation row (no DB read)."""
    state = ConversationState(
        customer_id=None,
        conversation_id=None,
        phone="+56912345678",
        intent=intent,
        captured={},
        window=[{"id": 1, "text": text}],
    )

    assert orchestrate(state) == {"next_step": "respond"}
