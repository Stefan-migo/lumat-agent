"""The address retry reuses the existing capture question wording."""

from app.chat.nodes import capture as capture_node


def test_second_address_ask_adds_location_pin_without_another_reply_key():
    question = "¿Cuál es tu dirección?"

    reply = capture_node._address_reask_question(question, offer_pin=True)

    assert "Cuál es tu dirección" in reply
    assert reply.count("¿") == reply.count("?") == 1
    assert "ubicación" in reply.lower() or "pin" in reply.lower()
