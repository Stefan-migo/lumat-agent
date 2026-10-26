"""S4 derivation replies: the customer reads one approved text per reason.

Seven escalation reasons have their own wording; every other reason keeps the
generic `handoff` text. The selection is a pure function, so the mapping is
testable without a database, an LLM or a full conversation.
"""

import pytest

from app.chat.nodes.handoff import DERIVATION_REPLY_KEYS, derivation_reply
from app.services.settings import REPLY_TEXT_DEFAULTS

APPROVED = {
    "cobertura": (
        "Todavía no tenemos visitas técnicas en {{comuna}}, un asesor de Lumat se "
        "contactará contigo para ayudarte a la brevedad."
    ),
    "persona": (
        "Listo, te paso con una persona del equipo. En cuanto esté disponible te "
        "escribe por acá."
    ),
    "unknown_intent_thrice": (
        "No quiero seguir dándote vueltas con esto. Te dejo con una persona del "
        "equipo para que te ayude directamente."
    ),
    "campo_sin_respuesta": (
        "Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para "
        "terminar de coordinar los datos."
    ),
    "booking_unavailable": (
        "No encontré un horario que nos sirva en la agenda, así que no te voy a "
        "dejar esperando: un asesor de Lumat te contacta para coordinar la visita "
        "directamente."
    ),
    "consent_declined": (
        "De acuerdo, no guardaremos tus datos ni agendaremos una visita."
    ),
    "consent_unclear": (
        "Necesito que me confirmes si autorizas guardar tus datos. Responde sí o no."
    ),
}

GENERIC = "Un asesor revisará tu caso y te contactará a la brevedad."


def test_the_mapping_covers_exactly_the_customer_facing_cases():
    assert set(DERIVATION_REPLY_KEYS) == set(APPROVED)
    for key in DERIVATION_REPLY_KEYS.values():
        assert key in REPLY_TEXT_DEFAULTS


def test_the_five_reasons_ship_the_approved_wording():
    for reason, text in APPROVED.items():
        assert REPLY_TEXT_DEFAULTS[DERIVATION_REPLY_KEYS[reason]] == text


@pytest.mark.parametrize("reason", sorted(APPROVED))
def test_each_derivation_reason_renders_its_own_text(reason):
    expected = APPROVED[reason].replace("{{comuna}}", "Ñuñoa")

    assert derivation_reply(REPLY_TEXT_DEFAULTS, reason, {"comuna": "Ñuñoa"}) == expected


@pytest.mark.parametrize(
    "reason",
    [
        "handoff",
        "injection_detected",
        "emergency",
        "cost_conversation_limit",
        "kb_unavailable",
        "booking_unclear",
        "scope_always_escalate",
        "complaint",
    ],
)
def test_an_unmapped_reason_keeps_the_generic_handoff_text(reason):
    assert derivation_reply(REPLY_TEXT_DEFAULTS, reason, {}) == GENERIC


@pytest.mark.parametrize("captured", [{}, {"comuna": ""}, {"comuna": "unknown"}, None])
def test_a_coverage_derivation_without_a_comuna_falls_back_to_the_generic_text(captured):
    """The slot is strict: an unfilled `{{comuna}}` would reach the customer."""
    assert derivation_reply(REPLY_TEXT_DEFAULTS, "cobertura", captured) == GENERIC


def test_an_owner_text_without_the_slot_is_rendered_as_is():
    texts = {**REPLY_TEXT_DEFAULTS, "handoff_cobertura": "Cobertura en camino."}

    assert derivation_reply(texts, "cobertura", {}) == "Cobertura en camino."
