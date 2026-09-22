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
        "GRACIAS, CHAO",
        "gracias, chau",
        "hasta luego",
        "nos vemos",
        "muchas gracias",
        "ok gracias",
        "gracias",
        "ok",
        "listo",
        "bye",
        "chau!",
    ],
)
def test_closing_tokens_are_farewells(phrase):
    assert is_farewell(phrase)


def test_closing_vocabulary_is_flattened():
    assert {"chao", "gracias", "ok", "listo"}.issubset(CLOSING_TOKENS)


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


def test_farewell_detector_rejects_length_and_questions():
    assert not is_farewell("chau " + "a" * 36)
    assert not is_farewell("")
    assert not is_farewell("   \t\n")
