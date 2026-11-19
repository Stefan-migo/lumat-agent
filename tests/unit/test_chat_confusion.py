"""S4 of `odd/tasks/saludo-informal.md`: the customer's confusion is not a failure.

Production #40: the bot answered a greeting with "Ya te ayudo con eso" and the
customer replied "No te entendí". The graph classified that as `unknown_intent`
and answered "Perdón. No entendí tu mensaje." — the customer said they did not
understand the bot, and the bot said it did not understand the customer.

The rule under test is a detector, not a text: `is_confusion_only` must see the
repair request, and must not see a real complaint that happens to open with the
same words.
"""

import pytest

from app.chat.nodes.receive import is_confusion_only
from app.chat.state import ConversationState


def _state(text: str, *, turn: int = 2, captured: dict | None = None) -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=turn,
        window=[{"direction": "inbound", "text": text}],
        captured=captured or {},
    )


@pytest.mark.parametrize(
    "text",
    [
        # The measured production string.
        "No te entendí",
        "no entendí",
        "no entendí nada",
        "no te entiendo",
        "no te entendí, disculpa",
        "perdón no te entendí",
        "No te entendí jaja",
        "no comprendo",
        "no comprendí bien",
        "no me entendiste",
        "no entiendo nada de esto",
        "noo te entendii",
    ],
)
def test_customer_not_understanding_the_bot_is_a_repair_request(text):
    assert is_confusion_only(_state(text)) is True


@pytest.mark.parametrize(
    "text",
    [
        # A complaint that opens with the same words is content, not a repair.
        "no entiendo por qué me cobraron eso",
        "no entiendo por qué no funciona mi calefont",
        "no entiendo nada de lo que pasa con el gas",
        # Ordinary turns.
        "hola",
        "no tengo visitas próximas para cancelar",
        "no te puedo dar mi correo",
    ],
)
def test_content_that_mentions_not_understanding_is_not_a_repair(text):
    assert is_confusion_only(_state(text)) is False


def test_first_turn_confusion_has_no_bot_message_to_repair():
    assert is_confusion_only(_state("no te entendí", turn=1)) is False


def test_confusion_during_capture_keeps_the_pending_question():
    """Mid-capture the repair is the field question, not a text (S4 boundary)."""
    state = _state("no te entendí", captured={"_pending": ["address"], "name": "Ana"})

    assert is_confusion_only(state) is False
