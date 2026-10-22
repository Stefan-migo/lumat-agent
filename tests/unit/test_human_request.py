"""S2 (odd/tasks/chatbot-backlog.md): one deterministic human-request detector.

Measured on `main` before this slice, with the regexes as they were:

- the gate derived "¿cuánto cuesta **por persona**?" (`_PERSONA_PATTERN` was a
  bare `\\bpersona\\b`);
- the classifier derived "**No** quiero hablar con una persona" (no negation
  guard);
- both missed "quiero hablar con el **encargado**" (role list too short).

D5 of the decision dossier settles the four rules: a request needs a request
plus a role, a negation guard, a bare token only when it is the whole message,
and the wider role list. The gate and the classifier must answer the same, so
these tests assert both entry points on every case.
"""

import pytest

from app.chat.nodes.classify_intent import is_explicit_human_request
from app.chat.nodes.handoff_gate import handoff_gate
from app.chat.state import ConversationState


def _state(text: str) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        window=[{"id": 1, "direction": "inbound", "msg_type": "text", "text": text}],
    )


def _gate_derives(text: str) -> bool:
    return handoff_gate(_state(text)).get("handoff_reason") == "persona"


@pytest.mark.parametrize(
    "text",
    [
        # Already true before this slice.
        "quiero hablar con una persona",
        "necesito un humano",
        # Measured misses: the role list was too short.
        "quiero hablar con el encargado",
        "quiero hablar con un asesor",
        "me pasas con el ejecutivo",
        "quiero hablar con la jefa",
        "quiero hablar con el dueño",
        "quiero hablar con un técnico",
        "prefiero que me atienda una persona",
        "atención humana, por favor",
        "quiero hablar con alguien",
        "comuníquenme con una persona",
        # A menu label made of role words only: the old gate matched it as a
        # phrase and the detector must not lose that recall.
        "asesor humano",
    ],
)
def test_request_plus_role_derives_in_both_entry_points(text):
    assert _gate_derives(text) is True
    assert is_explicit_human_request(text) is True


@pytest.mark.parametrize(
    "text",
    [
        # Measured false positive: a benign noun, not a request for a person.
        "¿cuánto cuesta por persona?",
        # Measured false positive: the request is negated.
        "no quiero hablar con una persona",
        "no, gracias, no necesito hablar con nadie",
        # A role mentioned in passing is not a request.
        "el técnico vino ayer y no dejó informe",
        "una persona me atendió muy bien",
        "pésima atención, una persona me trató mal",
        # A service need is not a request for a human.
        "necesito una visita técnica",
        "hola, tengo un calefont que no calienta",
        "hola",
    ],
)
def test_no_request_derives_nothing(text):
    assert _gate_derives(text) is False
    assert is_explicit_human_request(text) is False


@pytest.mark.parametrize(
    "text", ["persona", "persona?", "humano", "encargado", "asesor", "asesor humano", "persona humana"]
)
def test_bare_role_token_is_a_menu_selection(text):
    assert _gate_derives(text) is True
    assert is_explicit_human_request(text) is True


@pytest.mark.parametrize("text", ["1 persona", "persona 1", "dos personas"])
def test_role_inside_a_longer_message_is_not_a_menu_selection(text):
    assert _gate_derives(text) is False
    assert is_explicit_human_request(text) is False
