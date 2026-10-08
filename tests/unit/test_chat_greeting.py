import pytest

from app.chat.graph import END, _flow_start
from app.chat.state import ConversationState


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
