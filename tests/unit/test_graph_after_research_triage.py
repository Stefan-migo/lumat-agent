"""S13: after a KB deviation the capture agenda resumes — with one question per turn.

Production conversation #23, turns 287 and 288, arrived as two messages in the same
second:

    Entendido, Stefan: mantención de caldera… Tienes una visita agendada para el
    28/10 a las 10:00. ¿Quieres que esa misma visita se use para la mantención?
    ¿En qué comuna te encuentras?

`chat.conduct.max_preguntas_por_mensaje` is 1, and the customer was left holding two
different questions plus an offer nothing could honour. The capture question is not
wrong; it just belongs to the next turn when the KB answer already asked something.
"""

from langgraph.graph import END

from app.chat.graph import _after_research_triage
from app.chat.state import ConversationState


def _after_deviation(*replies: str, escalate: bool = False) -> str:
    state = ConversationState(
        customer_id=1,
        conversation_id=2,
        phone="+56912345678",
        capture_paused=True,
        replies=list(replies),
        escalate=escalate,
    )
    return _after_research_triage(state)


def test_capture_resumes_when_the_kb_answer_did_not_ask_anything():
    assert _after_deviation("Según el manual de Lumat: 15000 pesos.") == "capture"


def test_capture_waits_a_turn_when_the_kb_answer_already_asked():
    assert _after_deviation(
        "Entendido. ¿Quieres que esa misma visita se use para la mantención?"
    ) == END


def test_a_trailing_question_mark_with_whitespace_also_waits():
    assert _after_deviation("¿Te sirve el martes?   ") == END


def test_an_escalating_deviation_never_resumes_capture():
    assert _after_deviation("No tengo ese dato.", escalate=True) == END
