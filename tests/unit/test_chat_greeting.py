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


def _turn_state(text: str, turn: int) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=turn,
        window=[{"direction": "inbound", "text": text}],
    )


@pytest.mark.parametrize(
    "text",
    [
        # S1: the exact string measured on `main` as `intent=unknown`.
        "Hola buenas tardes",
        "hola, buenas noches",
        "hola buenas",
        "hola como va?",
        "hola cómo va?",
        "Hola!!",
        "hola??",
        "  HOLA  ",
        "Alo?",
        "aló",
        "buen día",
        "holi",
    ],
)
def test_greeting_variant_first_turn_skips_classification(text):
    assert _flow_start(_turn_state(text, 1)) == END


@pytest.mark.parametrize("text", ["Hola", "hola buenas tardes", "hola como va?"])
def test_greeting_variant_mid_conversation_skips_classification(text):
    """S1: a greeting never counts as a comprehension failure, at any turn."""
    assert _flow_start(_turn_state(text, 3)) == END


@pytest.mark.parametrize(
    "text, turn",
    [
        ("hola, tengo un calefont que no calienta", 1),
        ("buenas necesito una visita", 1),
        ("hola mundo", 1),
        ("hola, ¿ya está agendada mi visita?", 3),
        ("hola " + "a" * 40, 1),
    ],
)
def test_greeting_variant_never_swallows_content(text, turn):
    assert _flow_start(_turn_state(text, turn)) == "classify_intent"


@pytest.mark.parametrize(
    "text", ["hola buenas tardes", "hola como va", "alo", "buen día", "holi"]
)
def test_greeting_variants_have_no_content(text):
    assert has_content(_first_turn_state(text)) is False
