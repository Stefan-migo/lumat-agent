"""Configuration answers coverage, schedule and duration questions (S4-S6).

The same value used to live twice: in `settings` (the source the engine obeys)
and in customer-facing KB prose (the source the model reads). The two drifted,
and the customer got a prose answer that contradicted the configured one. These
answers read the configuration directly, so the KB keeps only the policy.
"""

from types import SimpleNamespace

import pytest

from app.chat.nodes import configured_answers
from app.chat.state import ConversationState
from app.services.settings import DEFAULT_COVERAGE_COMMUNES


def _state(text: str, *, intent: str = "consulta") -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent=intent,
        window=[{"id": 1, "text": text}],
    )


SESSION = SimpleNamespace()


def _coverage(monkeypatch, communes):
    monkeypatch.setattr(
        configured_answers, "get_coverage_communes", lambda _session: communes
    )


# --- S4: coverage from configuration -------------------------------------


def test_a_coverage_question_lists_the_configured_communes(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    reply = configured_answers.coverage_reply(
        SESSION, _state("que comunas cubren?")
    )

    assert reply == (
        "Atendemos normalmente en Las Condes, Ñuñoa, Lo Barnechea, La Reina, "
        "Peñalolén, Colina y Huechuraba."
    )


def test_the_list_follows_the_configuration_not_a_constant(monkeypatch):
    """The reply is the configured list, so changing the setting changes the answer."""
    _coverage(monkeypatch, ["Providencia", "Vitacura"])

    reply = configured_answers.coverage_reply(
        SESSION, _state("atienden en Vitacura?")
    )

    assert reply == "Atendemos normalmente en Providencia y Vitacura."


def test_one_commune_reads_as_a_single_sentence(monkeypatch):
    _coverage(monkeypatch, ["Colina"])

    reply = configured_answers.coverage_reply(SESSION, _state("cual es la cobertura?"))

    assert reply == "Atendemos normalmente en Colina."


@pytest.mark.parametrize(
    "question",
    [
        "atienden en ñuñoa?",
        "¿ATIENDEN EN NUNOA?",
        "ustedes llegan a Peñalolén?",
        "trabajan en Las Condes",
    ],
)
def test_a_question_naming_a_covered_commune_is_answered(question, monkeypatch):
    """Detection folds case and accents, like the commune lookup itself."""
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    assert configured_answers.coverage_reply(SESSION, _state(question)) is not None


@pytest.mark.parametrize(
    "question",
    [
        "atienden en Providencia?",
        "vivo en Maipu, trabajan alla?",
        "llegan a Rancagua?",
    ],
)
def test_a_commune_outside_the_list_keeps_the_existing_derivation_path(
    question, monkeypatch
):
    """S4 keeps the out-of-coverage derivation: no list is invented here.

    The KB keeps the policy for a commune outside coverage, so this answer steps
    aside instead of claiming coverage the configuration does not have.
    """
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    assert configured_answers.coverage_reply(SESSION, _state(question)) is None


def test_a_question_without_a_coverage_term_is_left_alone(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    assert (
        configured_answers.coverage_reply(
            SESSION, _state("cuanto sale el lavado de red?")
        )
        is None
    )


def test_an_empty_configuration_answers_nothing(monkeypatch):
    """No configured communes means no list to publish (no invention)."""
    _coverage(monkeypatch, [])

    assert (
        configured_answers.coverage_reply(SESSION, _state("que comunas cubren?"))
        is None
    )


def test_respond_answers_a_coverage_question_before_retrieval(monkeypatch):
    """The answer runs ahead of the KB path, so no embed is paid for it."""
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    reply = configured_answers.configuration_reply(
        SESSION, _state("que comunas cubren?")
    )

    assert reply is not None and reply.startswith("Atendemos normalmente en ")


# --- S5: opening hours from configuration --------------------------------


def _schedule(monkeypatch, schedule):
    monkeypatch.setattr(
        configured_answers, "get_hours_schedule", lambda _session: schedule
    )


WEEK = [{"days": [1, 2, 3, 4, 5, 6], "open": "09:00", "close": "18:00"}]


def test_an_hours_question_names_the_configured_days_and_range(monkeypatch):
    _schedule(monkeypatch, WEEK)

    reply = configured_answers.hours_reply(
        SESSION, _state("que horario tienen?")
    )

    assert reply == "Las visitas se agendan de lunes a sábado, de 09:00 a 18:00."


def test_the_range_follows_the_configuration(monkeypatch):
    _schedule(
        monkeypatch, [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "10:00", "close": "16:00"}]
    )

    reply = configured_answers.hours_reply(SESSION, _state("hasta que hora atienden?"))

    assert reply == "Las visitas se agendan de lunes a domingo, de 10:00 a 16:00."


def test_several_windows_are_all_named(monkeypatch):
    _schedule(
        monkeypatch,
        [
            {"days": [1, 2, 3, 4, 5], "open": "09:00", "close": "14:00"},
            {"days": [6], "open": "10:00", "close": "13:00"},
        ],
    )

    reply = configured_answers.hours_reply(SESSION, _state("cual es el horario?"))

    assert reply == (
        "Las visitas se agendan de lunes a viernes, de 09:00 a 14:00 "
        "y sábado, de 10:00 a 13:00."
    )


def test_days_that_are_not_consecutive_are_listed(monkeypatch):
    _schedule(
        monkeypatch, [{"days": [1, 3, 5], "open": "09:00", "close": "18:00"}]
    )

    reply = configured_answers.hours_reply(SESSION, _state("que dias atienden?"))

    assert reply == "Las visitas se agendan lunes, miércoles y viernes, de 09:00 a 18:00."


def test_an_empty_window_invents_no_schedule(monkeypatch):
    """S5: an empty window keeps the existing path instead of inventing hours."""
    _schedule(monkeypatch, [])

    assert configured_answers.hours_reply(SESSION, _state("que horario tienen?")) is None


def test_a_place_question_does_not_receive_the_schedule(monkeypatch):
    """The out-of-coverage policy belongs to the KB, not to an hours answer."""
    _schedule(monkeypatch, WEEK)

    assert (
        configured_answers.hours_reply(SESSION, _state("atienden en Providencia?"))
        is None
    )


def test_an_hours_question_is_reached_when_no_commune_is_named(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    _schedule(monkeypatch, WEEK)

    assert configured_answers.configuration_reply(
        SESSION, _state("hasta que hora atienden?")
    ) == "Las visitas se agendan de lunes a sábado, de 09:00 a 18:00."


def test_the_precedence_is_the_documented_one(monkeypatch):
    """A turn naming a covered commune AND an hour is a coverage question.

    Pinned so the order stays a decision: duration → coverage → hours, the first
    answer that recognises the turn owns it.
    """
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    _schedule(monkeypatch, WEEK)

    assert configured_answers.configuration_reply(
        SESSION, _state("atienden en Ñuñoa los sábados?")
    ).startswith("Atendemos normalmente en ")
