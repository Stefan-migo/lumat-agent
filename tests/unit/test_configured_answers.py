"""Configuration answers coverage, schedule and duration questions (S4-S6).

The same value used to live twice: in `settings` (the source the engine obeys)
and in customer-facing KB prose (the source the model reads). The two drifted,
and the customer got a prose answer that contradicted the configured one. These
answers read the configuration directly, so the KB keeps only the policy.
"""

from datetime import date, time
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


SESSION = SimpleNamespace(scalar=lambda _statement: None)


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


def test_place_mentioned_in_customer_kb_keeps_the_kb_answer_path(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    monkeypatch.setattr(SESSION, "scalar", lambda _statement: 1)
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {
            "coverage_out_of_area": "No tenemos cobertura habitual en {{comuna}}."
        },
    )

    assert configured_answers.coverage_reply(
        SESSION, _state("¿atienden en La Florida?")
    ) is None


def test_kb_place_deferral_requires_coverage_language_in_the_same_chunk(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    captured = {}

    def scalar(statement):
        captured["sql"] = str(statement.compile(compile_kwargs={"literal_binds": True}))
        return 1

    monkeypatch.setattr(SESSION, "scalar", scalar)
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {"coverage_out_of_area": "No hay cobertura para {{comuna}}."},
    )

    reply = configured_answers.coverage_reply(SESSION, _state("¿atienden en La Florida?"))

    assert all(
        term in captured["sql"] for term in ("%cobertura%", "%cubr%", "%atend%")
    )
    assert reply is None


def test_out_of_area_text_without_comuna_slot_still_answers(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    monkeypatch.setattr(SESSION, "scalar", lambda _statement: None)
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {"coverage_out_of_area": "Un asesor coordinará tu visita."},
    )

    assert configured_answers.coverage_reply(SESSION, _state("¿atienden en Maipú?")) == (
        "Un asesor coordinará tu visita."
    )


@pytest.mark.parametrize(
    ("question", "schedule_answer"),
    [
        ("¿trabajan en domingo?", True),
        ("¿ustedes trabajan en sábado?", True),
        ("¿atienden en horario de oficina?", True),
        ("¿llegan a revisar el calefont?", False),
        ("¿van a cobrar por la visita?", False),
    ],
)
def test_non_place_complements_do_not_become_coverage_answers(
    question, schedule_answer, monkeypatch
):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    monkeypatch.setattr(
        configured_answers,
        "get_hours_schedule",
        lambda _session: [{"days": [1, 2, 3, 4, 5, 6], "open": "09:00", "close": "18:00"}],
    )
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {"coverage_out_of_area": "No coverage for {{comuna}}."},
    )

    reply = configured_answers.configuration_reply(SESSION, _state(question))

    if schedule_answer:
        assert reply == "Las visitas se agendan de lunes a sábado, de 09:00 a 18:00."
    else:
        assert reply is None


@pytest.mark.parametrize(
    ("question", "place"),
    [
        ("atienden en Providencia?", "Providencia"),
        ("vivo en Maipu, trabajan alla?", "Maipu"),
        ("llegan a Lo Prado?", "Lo Prado"),
    ],
)
def test_a_named_out_of_area_place_gets_the_advisor_policy(question, place, monkeypatch):
    """The named place gets policy, without checking it against a commune master."""
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {
            "coverage_out_of_area": (
                "No tenemos cobertura habitual en {{comuna}}, pero igual podemos "
                "ayudarte: un asesor coordina la visita según disponibilidad."
            )
        },
    )

    assert configured_answers.coverage_reply(SESSION, _state(question)) == (
        "No tenemos cobertura habitual en "
        f"{place}, pero igual podemos ayudarte: un asesor coordina la visita según disponibilidad."
    )


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


def test_rm_commune_data_is_complete_for_configured_and_named_communes():
    communes = configured_answers._load_rm_communes()
    folded = {configured_answers._fold(commune) for commune in communes}

    assert len(communes) == 52
    assert {configured_answers._fold(name) for name in DEFAULT_COVERAGE_COMMUNES} <= folded
    assert {"maipu", "lo prado", "padre hurtado"} <= folded


@pytest.mark.parametrize(
    ("question", "place"),
    [
        ("¿trabajan en Lo Prado?", "Lo Prado"),
        ("¿atienden en Padre Hurtado?", "Padre Hurtado"),
    ],
)
def test_named_unconfigured_rm_commune_gets_advisor_policy(question, place, monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    monkeypatch.setattr(SESSION, "scalar", lambda _statement: None)
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {"coverage_out_of_area": "No tenemos cobertura habitual en {{comuna}}."},
    )

    assert configured_answers.coverage_reply(SESSION, _state(question)) == (
        f"No tenemos cobertura habitual en {place}."
    )


@pytest.mark.parametrize(
    "question",
    [
        "¿trabajan en mi casa?",
        "¿trabajan en la Región Metropolitana?",
        "¿atienden en festivos?",
        "¿atienden en feriados?",
        "¿trabajan en regiones?",
        "¿llegan al centro?",
        "¿trabajan en la playa?",
        "¿trabajan en el sur?",
        "¿trabajan en el campo?",
        "¿atienden en edificios?",
        "¿atienden en departamentos?",
        "¿trabajan en vacaciones?",
        "¿llegan al extranjero?",
        "¿atienden en altura?",
        "¿trabajan en el verano?",
        "¿atienden en San Fernando?",
        "¿atienden en Viña del Mar?",
        "¿llegan a Frutillar?",
    ],
)
def test_unlisted_places_and_non_places_are_left_to_the_model(question, monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    monkeypatch.setattr(SESSION, "scalar", lambda _statement: None)
    monkeypatch.setattr(
        configured_answers,
        "get_reply_texts",
        lambda _session: {"coverage_out_of_area": "No coverage for {{comuna}}."},
    )

    assert configured_answers.coverage_reply(SESSION, _state(question)) is None


def test_covered_commune_with_weekday_qualifier_keeps_coverage_precedence(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)
    _schedule(monkeypatch, WEEK)

    assert configured_answers.configuration_reply(
        SESSION, _state("¿atienden en Ñuñoa el sábado?")
    ) == (
        "Atendemos normalmente en Las Condes, Ñuñoa, Lo Barnechea, La Reina, "
        "Peñalolén, Colina y Huechuraba."
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


def test_availability_question_renders_real_slots_without_persisting_an_offer(monkeypatch):
    monkeypatch.setattr(configured_answers, "get_coverage_communes", lambda _session: [])
    monkeypatch.setattr(configured_answers, "get_booking_lead_minutes", lambda _session: 120)
    monkeypatch.setattr(
        configured_answers, "get_hours_timezone", lambda _session: "America/Santiago"
    )
    calls = []

    def available_slots(session, **kwargs):
        calls.append(kwargs)
        return [(1, date(2026, 11, 26), time(10, 0)), (1, date(2026, 11, 28), time(11, 0))]

    monkeypatch.setattr(configured_answers, "open_slots_for_assignment", available_slots)
    monkeypatch.setattr(configured_answers, "get_reply_texts", lambda _session: {
        "availability_preview": "Tengo estos horarios disponibles: {{opciones}}. Si quieres, te tomo los datos y te la reservo."
    })
    state = _state("¿Tienen disponibilidad para agendar?")
    state.captured = {"_booking_offer": {"keep": "untouched"}}

    reply = configured_answers.configuration_reply(SESSION, state)

    assert reply == (
        "Tengo estos horarios disponibles: jueves 26 a las 10:00 y sábado 28 a las 11:00. "
        "Si quieres, te tomo los datos y te la reservo."
    )
    assert state.captured["_booking_offer"] == {"keep": "untouched"}
    assert calls[0]["days"] == 7
    assert calls[0]["duration_minutes"] == configured_answers.DEFAULT_DURATION_MINUTES
    # No day was named, so the answer keeps one slot per day out of a wide slice.
    assert calls[0]["limit"] == configured_answers._PREVIEW_UNIVERSE
    assert calls[0]["window"] is None
    assert calls[0]["lead_minutes"] == 120
    assert calls[0]["now"].tzinfo is not None and calls[0]["now"].utcoffset().total_seconds() == 0


def test_availability_question_uses_three_slot_spanish_list(monkeypatch):
    monkeypatch.setattr(configured_answers, "get_coverage_communes", lambda _session: [])
    monkeypatch.setattr(configured_answers, "get_booking_lead_minutes", lambda _session: 0)
    monkeypatch.setattr(
        configured_answers, "get_hours_timezone", lambda _session: "America/Santiago"
    )
    monkeypatch.setattr(
        configured_answers,
        "open_slots_for_assignment",
        lambda _session, **kwargs: [
            (1, date(2026, 11, 26), time(10, 0)),
            (1, date(2026, 11, 27), time(11, 30)),
            (1, date(2026, 11, 28), time(12, 0)),
        ],
    )
    monkeypatch.setattr(configured_answers, "get_reply_texts", lambda _session: {
        "availability_preview": "Horarios: {{opciones}}."
    })

    assert configured_answers.configuration_reply(SESSION, _state("¿Hay cupos disponibles?")) == (
        "Horarios: jueves 26 a las 10:00, viernes 27 a las 11:30 y sábado 28 a las 12:00."
    )


@pytest.mark.parametrize(
    "question",
    ["¿hasta qué hora atienden?", "¿cuál es el horario?", "¿qué días atienden?"],
)
def test_window_questions_still_use_the_existing_hours_answer(question, monkeypatch):
    _coverage(monkeypatch, [])
    _schedule(monkeypatch, WEEK)
    monkeypatch.setattr(
        configured_answers,
        "open_slots_for_assignment",
        lambda *_args, **_kwargs: pytest.fail("window question must not query availability"),
    )

    assert configured_answers.configuration_reply(SESSION, _state(question)) == (
        "Las visitas se agendan de lunes a sábado, de 09:00 a 18:00."
    )


def test_availability_question_without_slots_falls_back_to_policy_sentence(monkeypatch):
    _coverage(monkeypatch, [])
    _schedule(monkeypatch, [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}])
    monkeypatch.setattr(configured_answers, "get_booking_lead_minutes", lambda _session: 120)
    monkeypatch.setattr(
        configured_answers, "get_hours_timezone", lambda _session: "America/Santiago"
    )
    monkeypatch.setattr(configured_answers, "open_slots_for_assignment", lambda *_args, **_kwargs: [])

    assert configured_answers.configuration_reply(
        SESSION, _state("¿Tienen hora disponible para reservar?")
    ) == "Las visitas se agendan según la disponibilidad de los técnicos."


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


# --- S6: service durations from configuration ----------------------------


def _durations(monkeypatch, durations):
    monkeypatch.setattr(
        configured_answers, "get_service_durations", lambda _session: durations
    )


@pytest.mark.parametrize(
    ("minutes", "text"),
    [(45, "45 minutos"), (60, "1 hora"), (90, "1 hora y 30 minutos"), (180, "3 horas")],
)
def test_the_duration_is_rendered_from_the_configured_minutes(minutes, text, monkeypatch):
    _durations(monkeypatch, {"Calefont": minutes})

    assert (
        configured_answers.duration_reply(SESSION, _state("cuanto dura un calefont?"))
        == f"Calefont dura {text}."
    )


def test_a_configured_phrase_matches_the_customer_wording(monkeypatch):
    _durations(monkeypatch, {"Mantención de calefont": 60})

    assert (
        configured_answers.duration_reply(
            SESSION, _state("cuanto dura la mantención de calefont?")
        )
        == "Mantención de calefont dura 1 hora."
    )


def test_a_service_without_a_configured_duration_keeps_the_kb_path(monkeypatch):
    """S6: no duration is invented for a service the configuration does not hold."""
    _durations(monkeypatch, {"Calefont": 60})

    assert (
        configured_answers.duration_reply(SESSION, _state("cuanto dura la caldera?"))
        is None
    )


def test_a_configured_service_without_a_duration_question_is_left_alone(monkeypatch):
    _durations(monkeypatch, {"Calefont": 60})

    assert (
        configured_answers.duration_reply(SESSION, _state("cuanto sale un calefont?"))
        is None
    )


def test_an_empty_duration_map_answers_nothing(monkeypatch):
    _durations(monkeypatch, {})

    assert (
        configured_answers.duration_reply(SESSION, _state("cuanto dura un calefont?"))
        is None
    )


def test_a_verb_that_means_cover_is_not_a_coverage_question(monkeypatch):
    """`cubre` is also how a guarantee question is asked, and it names no commune.

    Measured: `la garantia cubre algo?` (postventa) was answered with the commune
    list instead of reaching the KB, because the verb alone matched the detector.
    """
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    assert (
        configured_answers.coverage_reply(
            SESSION, _state("la garantia cubre algo?", intent="postventa")
        )
        is None
    )


def test_a_cover_verb_with_a_covered_commune_is_a_coverage_question(monkeypatch):
    _coverage(monkeypatch, DEFAULT_COVERAGE_COMMUNES)

    assert configured_answers.coverage_reply(
        SESSION, _state("cubren en Ñuñoa?")
    ) == (
        "Atendemos normalmente en Las Condes, Ñuñoa, Lo Barnechea, La Reina, "
        "Peñalolén, Colina y Huechuraba."
    )


def test_a_window_covering_every_day_and_hour_is_not_announced_as_hours(monkeypatch):
    """A no-restriction window means technician availability decides, not a clock.

    Measured in production: the configured window is every day 00:00-23:59, so
    rendering it literally would tell a customer the business takes visits at any
    hour, when what actually bounds the calendar is the technicians' agenda.
    """
    _schedule(
        monkeypatch, [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}]
    )

    reply = configured_answers.hours_reply(SESSION, _state("cual es el horario?"))

    assert reply == "Las visitas se agendan según la disponibilidad de los técnicos."


def test_a_configured_name_with_stray_whitespace_still_matches(monkeypatch):
    """Measured in production: "Mantención de  calefont" (double space) answered
    nothing, because the name is matched as a phrase. A typo in a panel field must
    not silence a customer answer.
    """
    _durations(monkeypatch, {"Mantención de  calefont": 60})

    assert (
        configured_answers.duration_reply(
            SESSION, _state("cuanto dura la mantención de calefont?")
        )
        == "Mantención de  calefont dura 1 hora."
    )
