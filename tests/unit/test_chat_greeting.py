import pytest

from app.chat.graph import END, _flow_start
from app.chat.nodes.receive import _resume_topic, has_content, is_social_only
from app.chat.state import ConversationState
from app.services.settings import MESSAGE_DEFAULTS


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
        "Holaa",
        "holaaa",
        "buenaaas",
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
    ["hola", "BUENAS", "hola buenas", "buenos días", "hey!", None, "", "Holaa"],
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


def _thread_state(text: str, *, booking=None, captured=None) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=3,
        window=[{"direction": "inbound", "text": text}],
        captured=captured or {},
        booking=booking,
    )


# S1 (odd/tasks/saludo-retorno.md): a bare greeting mid-thread is not a first
# contact. Measured in `real-solo-sabados` turn 2 — a customer who had already
# given the building, the topic and her Saturday question said only `Buen dia`
# and the bot asked her name again.
def test_the_resume_greeting_never_reintroduces_the_bot():
    for key in ("greeting_resume", "greeting_resume_topic"):
        text = MESSAGE_DEFAULTS[key]
        assert "soy Max" not in text, key
        assert "Con quién tengo el gusto" not in text, key


# S2: name a topic only when the state proves one. A booked service outranks the
# captured equipment because it is what the conversation already promised, and a
# thread that holds neither gets no topic at all.
@pytest.mark.parametrize(
    "booking, captured, expected",
    [
        (
            {"service": "mantención de caldera"},
            {"equipment": "caldera"},
            "mantención de caldera",
        ),
        (None, {"equipment": "calefont"}, "calefont"),
        ({"service": "  "}, {"equipment": "calefont"}, "calefont"),
        (None, {}, ""),
        (None, None, ""),
        (None, {"comuna": "Ñuñoa"}, ""),
    ],
)
def test_the_resume_topic_names_only_what_the_state_holds(booking, captured, expected):
    state = _thread_state("Buen día", booking=booking, captured=captured)
    assert _resume_topic(state) == expected


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


# S1 (odd/tasks/saludo-informal.md): production #40 wrote "Holaa" and the exact
# word list read it as stated content, so the first-contact reply promised help
# with something nobody had asked for. WhatsApp writes a greeting with one letter
# repeated more often than without.
@pytest.mark.parametrize(
    "text",
    [
        "Holaa",
        "holaaa",
        "HOLAAA",
        "buenaaas",
        "aloo?",
        "Holaa, buenas tardes",
        "holaaa como va?",
    ],
)
def test_informal_greeting_spelling_is_a_greeting(text):
    assert _flow_start(_turn_state(text, 1)) == END
    assert _flow_start(_turn_state(text, 3)) == END
    assert has_content(_first_turn_state(text)) is False


# S2: the measured burst. Two inbound before the first answer are one turn
# (`collapse_trailing_burst`), so the greeting the customer wrote informally and
# the social question that follows it arrive as one text.
@pytest.mark.parametrize(
    "text",
    [
        "Holaa\nCómo estás?",
        "holaaa\nCómo estás?",
        "Holaa, ¿cómo estás?",
        "Holaaa, todo bien?",
    ],
)
def test_informal_greeting_plus_social_question_is_not_content(text):
    state = _first_turn_state(text)

    assert _flow_start(_turn_state(text, 1)) == END
    assert has_content(state) is False
    assert is_social_only(state) is True


# S3: the guard that matters more than the fix. Reducing repeated letters must
# never turn content into a greeting: swallowing a stated need costs the customer
# more than the redundant greeting it replaces.
@pytest.mark.parametrize(
    "text",
    [
        "holaa necesito una visita",
        "holanda",
        "chocolate",
        "hola, tengo un calefont que no calienta",
        "aaaa",
        "hola " + "o" * 40,
    ],
)
def test_reduction_never_swallows_content(text):
    assert _flow_start(_turn_state(text, 1)) == "classify_intent"
    assert has_content(_first_turn_state(text)) is True
