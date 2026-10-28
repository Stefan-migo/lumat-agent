"""A coverage question is answered by `respond` from the configuration (S4).

End-to-end half of the rule: the turn never reaches the KB path, so the answer is
the configured list and not a grounded sentence built from prose.
"""

from app.chat.nodes.respond import respond
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.services.settings import COVERAGE_COMMUNES_KEY, set_setting


def _state(text: str, *, intent: str = "consulta") -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent=intent,
        window=[{"id": 1, "text": text}],
    )


def test_respond_answers_a_coverage_question_from_the_configuration():
    with SessionLocal() as session:
        set_setting(session, COVERAGE_COMMUNES_KEY, ["Providencia", "Vitacura"])
        session.commit()

    result = respond(_state("que comunas cubren?"))

    assert result["replies"] == [
        "Atendemos normalmente en Providencia y Vitacura."
    ]
    assert result.get("escalate") is not True


def test_the_answer_does_not_depend_on_the_classified_intent():
    """The question is answered the same way whether the classifier said
    `consulta` or `valores`, because the detector is not the classifier."""
    for intent in ("consulta", "valores"):
        result = respond(_state("que comunas cubren?", intent=intent))

        assert result["replies"][0].startswith("Atendemos normalmente en ")


def test_respond_answers_an_hours_question_from_the_configuration():
    with SessionLocal() as session:
        set_setting(
            session,
            "hours.schedule",
            [{"days": [1, 2, 3, 4, 5, 6], "open": "09:00", "close": "18:00"}],
        )
        session.commit()

    result = respond(_state("que horario tienen?"))

    assert result["replies"] == [
        "Las visitas se agendan de lunes a sábado, de 09:00 a 18:00."
    ]


def test_respond_answers_a_duration_question_from_the_configuration():
    with SessionLocal() as session:
        set_setting(session, "booking.service_durations", {"Calefont": 60})
        session.commit()

    result = respond(_state("cuanto dura un calefont?"))

    assert result["replies"] == ["Calefont dura 1 hora."]
