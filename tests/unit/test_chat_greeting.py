import pytest

from app.chat.graph import END, _flow_start
from app.chat.nodes.receive import has_content
from app.chat.state import ConversationState


def _first_turn_state(text: str | None) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=1,
        window=[{"direction": "inbound", "text": text}],
    )


@pytest.mark.parametrize(
    "text",
    [
        "hola",
        "BUENAS",
        "hola buenas",
        "hola, buenas",
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "hey!",
    ],
)
def test_greeting_only_first_turn_skips_classification(text):
    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=1,
        window=[{"direction": "inbound", "text": text}],
    )

    assert _flow_start(state) == END


@pytest.mark.parametrize(
    "text",
    ["hola, tengo un calefont que no calienta", "buenas necesito una visita"],
)
def test_greeting_with_content_still_classifies(text):
    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=1,
        window=[{"direction": "inbound", "text": text}],
    )

    assert _flow_start(state) == "classify_intent"


@pytest.mark.parametrize(
    "text",
    ["hola", "BUENAS", "hola buenas", "buenos días", "hey!", None, ""],
)
def test_bare_greeting_or_empty_first_turn_has_no_content(text):
    """A bare greeting (or no text at all) must not be treated as stated content."""
    assert has_content(_first_turn_state(text)) is False


@pytest.mark.parametrize(
    "text",
    [
        "hola, tengo un calefont que no calienta",
        "hola necesito reagendar una visita que hice ayer",
        "necesito reagendar una visita",
        "mi calefont no enciende",
    ],
)
def test_first_turn_with_a_need_has_content(text):
    """Anything beyond a bare greeting is the customer stating their need."""
    assert has_content(_first_turn_state(text)) is True
