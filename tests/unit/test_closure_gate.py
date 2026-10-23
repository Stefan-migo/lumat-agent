import pytest

from app.chat.nodes.closure_gate import CLOSING_TOKENS, is_farewell


@pytest.mark.parametrize(
    "phrase",
    [
        "chau",
        "chao",
        "adiós",
        "adios",
        "¡Adiós!",
        "hasta luego",
        "nos vemos",
        "bye",
        "chau!",
        "eso fue todo",
    ],
)
def test_closing_tokens_are_farewells(phrase):
    assert is_farewell(phrase)


@pytest.mark.parametrize(
    "phrase",
    ["gracias", "muchas gracias", "ok", "listo", "perfecto", "dale", "ok gracias"],
)
def test_acknowledgements_are_not_farewells(phrase):
    """S3 (chatbot-experiencia): courtesy belongs to the classifier, not the gate.

    These used to close the conversation with a goodbye. Now the classifier
    names them `smalltalk` and the bot answers with the courtesy reply, so the
    gate must not swallow them first.
    """
    assert not is_farewell(phrase)


def test_closing_vocabulary_is_flat_and_explicit():
    assert {"chao", "adios", "hasta", "luego", "bye"}.issubset(CLOSING_TOKENS)
    assert CLOSING_TOKENS.isdisjoint({"gracias", "ok", "listo", "perfecto", "dale"})


@pytest.mark.parametrize(
    "phrase",
    [
        "gracias, ¿cuánto sale la revisión anual?",
        "chau, pero antes dime los valores",
        "hola, necesito una visita",
        "¿cuánto cuesta?",
    ],
)
def test_non_closing_tokens_or_questions_are_not_farewells(phrase):
    assert not is_farewell(phrase)


def test_question_containing_thanks_is_not_a_farewell():
    assert not is_farewell("gracias, ¿puedes coordinar una visita?")


def test_booking_request_is_not_a_farewell():
    assert not is_farewell("ya agende una visita")


def test_farewell_detector_rejects_length_and_questions():
    assert not is_farewell("chau " + "a" * 36)
    assert not is_farewell("")
    assert not is_farewell("   \t\n")
