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


@pytest.mark.parametrize(
    "phrase",
    ["eso era todo", "Eso era todo", "eso es todo", "nada más", "eso sería todo"],
)
def test_closings_with_era_are_farewells(phrase):
    """T3/S3: the customer closes and the bot asks another sales question.

    The judge reported it verbatim: «Respondio la despedida («eso era todo») con
    una nueva pregunta comercial». `_CLOSING_PHRASES` only knew "eso fue todo",
    and `era` must not become a closing token: it is an ordinary verb, so a token
    match would also close "el calefont era viejo".
    """
    assert is_farewell(phrase)


@pytest.mark.parametrize(
    "phrase",
    [
        "el calefont era viejo y hace ruido",
        "eso era lo que necesitaba saber del precio",
        "todo bien, pero el agua sale fria",
    ],
)
def test_a_statement_that_only_contains_those_words_does_not_close(phrase):
    """The closing must be the whole message, not a fragment of a sentence."""
    assert not is_farewell(phrase)


@pytest.mark.parametrize(
    "phrase",
    [
        "dale, muchas gracias, eso era todo",
        "ok gracias, eso era todo",
        "muchas gracias, nada más",
    ],
)
def test_a_closing_phrase_surrounded_by_courtesy_still_closes(phrase):
    """T3/S3: the real message wraps the closing in courtesy.

    The measured transcript was "dale, muchas gracias, eso era todo" and the bot
    answered "¿En qué más te puedo ayudar?". The phrase matched, but `is_farewell`
    required every remaining token to be a closing token, and acknowledgements
    were deliberately removed from that set (S3: courtesy belongs to the
    classifier). Courtesy around an explicit closing must not cancel it.
    """
    assert is_farewell(phrase)


@pytest.mark.parametrize(
    "phrase",
    ["eso era todo lo que necesitaba saber del precio", "gracias"],
)
def test_courtesy_alone_or_around_content_does_not_close(phrase):
    """The courtesy allowance only applies when a closing phrase matched."""
    assert not is_farewell(phrase)


@pytest.mark.parametrize(
    "phrase",
    [
        "eso seria todo muchas gracias! que tengas buen dia",
        "eso seria todo. gracias nuevament",
    ],
)
def test_long_closing_with_courtesy_is_still_a_farewell(phrase):
    assert is_farewell(phrase)
