"""Regression coverage for Saturday availability and selected-day continuity.

The historical configuration is seeded synthetically and the clock is frozen
on Wednesday 2026-11-25, so all date examples remain literal and isolated. Each
technician's 09:00-12:00 daily block mirrors the three days production named;
the preview's one-slot-per-day horizon is a separate, unfixed limitation.
"""

from datetime import date, datetime, time, timezone

import psycopg
import pytest
from app.chat.graph import run_conversation
from app.chat.slot_window import resolve_window
from app.chat.state import get_or_create_conversation
from app.db import SessionLocal
from app.models import (
    Appointment,
    Conversation,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    TechnicianWeeklySchedule,
    User,
    UserRole,
)
from app.services import technician_schedule
from app.services.customers import get_or_create_customer
from app.services.settings import set_setting
from _testdb import admin_database_url

# Wednesday 2026-11-25, 19:00 in America/Santiago.
MOMENT = datetime(2026, 11, 25, 22, 0, tzinfo=timezone.utc)


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return MOMENT.astimezone(tz) if tz is not None else MOMENT.replace(tzinfo=None)


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return MOMENT.astimezone(_SANTIAGO).date()


from zoneinfo import ZoneInfo  # noqa: E402

_SANTIAGO = ZoneInfo("America/Santiago")


@pytest.fixture(autouse=True)
def clean_continuity_db(migrated_db):
    with psycopg.connect(admin_database_url(), autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customers, users RESTART IDENTITY CASCADE"
        )


def _freeze(monkeypatch):
    """Pin every clock the chat path reads, so the dates are literal."""
    from app.chat import state as state_module
    from app.chat.nodes import (
        booking,
        capture,
        closure_gate,
        configured_answers,
        handoff_gate,
        manage,
        orchestrate,
    )

    for module in (
        configured_answers, capture, booking, orchestrate,
        handoff_gate, closure_gate, manage, state_module,
    ):
        monkeypatch.setattr(module, "datetime", _FrozenDateTime, raising=False)
    monkeypatch.setattr(capture, "date", _FrozenDate, raising=False)
    monkeypatch.setattr(orchestrate, "date", _FrozenDate, raising=False)


def _seed(monkeypatch, *, saturday_open=True, window=None):
    _freeze(monkeypatch)
    with SessionLocal() as session:
        set_setting(session, "hours.timezone", "America/Santiago")
        set_setting(
            session,
            "hours.schedule",
            window
            or [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}],
        )
        weekdays = [1, 2, 3, 4, 5, 6] if saturday_open else [1, 2, 3, 4, 5]
        for index in range(2):
            technician = User(
                username=f"saturday-technician-{index}",
                password_hash="test",
                role=UserRole.TECNICO,
            )
            session.add(technician)
            session.flush()
            session.add_all(
                TechnicianWeeklySchedule(
                    technician_id=technician.id,
                    weekday=weekday,
                    opens_at=time(9, 0),
                    closes_at=time(12, 0),
                )
                for weekday in weekdays
            )
            session.flush()
            technician_schedule.materialize(session, technician.id, MOMENT)
        customer = get_or_create_customer(session, "+56912345678")
        conversation = get_or_create_conversation(session, customer, customer.phone_e164)
        conversation.turn_count = 1
        session.add(
            Message(
                wamid="wamid.continuity.seed",
                conversation_id=conversation.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="hola, necesito una mantención",
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        return conversation.id


def _turn(conversation_id, text, wamid):
    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conversation_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.query(Message).filter_by(wamid=wamid).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _captured(conversation_id):
    with SessionLocal() as session:
        return session.get(Conversation, conversation_id).captured_data


def _appointment_count():
    with SessionLocal() as session:
        return session.query(Appointment).count()


def _extract_day_selection(monkeypatch):
    """Have the classifier double return the same captured preference as production."""
    import sys

    modules = [
        module for module in sys.modules.values()
        if str(getattr(module, "__file__", "")).endswith("tests/integration/conftest.py")
    ]
    assert modules
    for module in modules:
        classify = module.classify_result_for

        def classify_with_availability(text, classify=classify):
            result = classify(text)
            if resolve_window(text, today=date(2026, 11, 25)) is not None:
                return {**result, "fields": {"availability": text}}
            return result

        monkeypatch.setattr(module, "classify_result_for", classify_with_availability)


def _reported_preview(conversation_id):
    return _turn(
        conversation_id,
        "Hola, ¿tienen disponibilidad para revisar el calefont?",
        "wamid.continuity.preview",
    )


def _accept_saturday(conversation_id):
    return _turn(
        conversation_id,
        "Perfecto! El sábado 28 anda súper bien",
        "wamid.continuity.accept",
    )


def test_reported_acceptance_is_captured_without_booking(mock_openai_chat, monkeypatch):
    conversation_id = _seed(monkeypatch)
    _extract_day_selection(monkeypatch)

    preview = _reported_preview(conversation_id)
    assert len(preview) == 1
    assert all(day in preview[0] for day in ("jueves 26", "viernes 27", "sábado 28")), preview

    acceptance = _accept_saturday(conversation_id)
    assert _captured(conversation_id).get("availability"), _captured(conversation_id)

    assert any("sábado 28" in reply.lower() for reply in acceptance), (acceptance, _captured(conversation_id))
    assert not any("Las visitas se agendan según" in reply for reply in acceptance)
    selected = _captured(conversation_id)["availability"]
    window = resolve_window(selected, today=date(2026, 11, 25))
    assert window is not None and window.day == date(2026, 11, 28), selected
    assert _appointment_count() == 0


def test_direct_saturday_question_uses_actual_availability(mock_openai_chat, monkeypatch):
    conversation_id = _seed(monkeypatch)

    replies = _turn(conversation_id, "¿Pueden el sábado?", "wamid.continuity.direct")

    assert len(replies) == 1
    assert "Las visitas se agendan según" not in replies[0]
    assert "sábado 28" in replies[0].lower()
    assert any(clock in replies[0] for clock in ("09:00", "09:30", "10:00"))


def test_selection_survives_capture_until_numbered_offer(mock_openai_chat, monkeypatch):
    conversation_id = _seed(monkeypatch)
    _extract_day_selection(monkeypatch)
    _reported_preview(conversation_id)
    acceptance = _accept_saturday(conversation_id)
    assert any("sábado 28" in reply.lower() for reply in acceptance), (acceptance, _captured(conversation_id))

    steps = [
        ("Calefont Bosch", "equipment"),
        ("Ñuñoa", "comuna"),
        ("Ana Pérez", "name"),
        ("ana@example.com", "email"),
        ("Avenida Irarrázaval 40", "address"),
    ]
    for index, (answer, field) in enumerate(steps):
        replies = _turn(conversation_id, answer, f"wamid.continuity.capture.{index}")
        assert replies, f"no reply after {field}"

    # Consent is its own required step; it may not book before the numbered choice.
    consent = _turn(conversation_id, "Sí, autorizo", "wamid.continuity.consent")
    assert any("1." in reply for reply in consent), consent
    captured = _captured(conversation_id)
    selected = resolve_window(captured["availability"], today=date(2026, 11, 25))
    assert selected is not None and selected.day == date(2026, 11, 28)
    offer = "\n".join(consent)
    assert "Sábado 28/11" in offer
    assert all(day not in offer for day in ("Jueves 26/11", "Viernes 27/11"))
    assert _appointment_count() == 0


def test_unavailable_saturday_is_truthful_and_offers_continuation(mock_openai_chat, monkeypatch):
    conversation_id = _seed(monkeypatch, saturday_open=False)

    replies = _turn(conversation_id, "¿Pueden el sábado?", "wamid.continuity.no-saturday")

    assert len(replies) == 1
    assert "sábado" in replies[0].lower()
    assert "no me quedan horarios" in replies[0].lower()
    assert "Si te sirve otro día" in replies[0]
    assert not any(clock in replies[0] for clock in ("09:00", "09:30", "10:00"))


def test_genuine_business_hours_question_keeps_configured_window(mock_openai_chat, monkeypatch):
    conversation_id = _seed(monkeypatch)

    replies = _turn(conversation_id, "¿Cuál es su horario?", "wamid.continuity.hours")

    assert replies == ["Las visitas se agendan según la disponibilidad de los técnicos."]


@pytest.mark.parametrize(
    "question",
    [
        "¿trabajan en domingo?",
        "¿abren el domingo?",
        "¿Hasta qué hora abren el sábado?",
    ],
)
def test_a_business_hours_question_that_names_a_day_keeps_the_window(
    mock_openai_chat, monkeypatch, question
):
    """S4.5: a day word must not turn a closing-time question into a menu.

    Independent verifier finding on the first candidate: with a Monday-Saturday
    09:00-18:00 window, "¿Hasta qué hora abren el sábado?" was answered with the
    Saturday slot times, because the weekday resolved to a window. The configured
    window is the answer to a question about the week, and the agenda only answers
    questions about appointment availability.
    """
    conversation_id = _seed(
        monkeypatch,
        window=[{"days": [1, 2, 3, 4, 5, 6], "open": "09:00", "close": "18:00"}],
    )
    replies = _turn(
        conversation_id, question, f"wamid.continuity.hours.{abs(hash(question))}"
    )

    assert replies == ["Las visitas se agendan de lunes a sábado, de 09:00 a 18:00."]


@pytest.mark.parametrize(
    "question",
    [
        "¿Tienen hora el sábado?",
        "¿Tienen hora para el sábado?",
        "¿Hay hora el sábado?",
        "¿Me pueden dar una hora el sábado?",
        "¿A qué hora puedo ir el sábado?",
    ],
)
def test_a_slot_question_phrased_with_hora_uses_the_agenda(
    mock_openai_chat, monkeypatch, question
):
    """S4.4: "tener hora" is Chilean for an appointment slot, not for the week.

    Independent verifier finding on the second candidate: an opening/closing
    vocabulary that included "hora" swallowed all five phrasings and answered the
    generic policy sentence, which is the sentence this fix exists to remove.
    """
    conversation_id = _seed(monkeypatch)
    replies = _turn(
        conversation_id, question, f"wamid.continuity.hora.{abs(hash(question))}"
    )

    assert "sábado 28" in replies[0]
    assert "09:00" in replies[0]
    assert "disponibilidad de los técnicos" not in replies[0]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "¿Pueden el sábado?",
            "Para el sábado 28/11 no me quedan horarios. Si te sirve otro día, dime "
            "cuál y te tomo los datos para reservarlo.",
        ),
        (
            "¿Hay disponibilidad el sábado?",
            "Para el sábado 28/11 no me quedan horarios. Si te sirve otro día, dime "
            "cuál y te tomo los datos para reservarlo.",
        ),
        ("¿trabajan el sábado?", "Las visitas se agendan de lunes a viernes, de 09:00 a 18:00."),
        ("¿abren el sábado?", "Las visitas se agendan de lunes a viernes, de 09:00 a 18:00."),
    ],
)
def test_a_visit_question_on_a_closed_day_keeps_the_truthful_continuation(
    mock_openai_chat, monkeypatch, question, expected
):
    """S4.6: a visit question on a closed day answers availability, not the week.

    Independent verifier finding on the second candidate: a Monday-Friday week
    answered "¿Pueden el sábado?" with the configured window, which drops the
    existing continuation. The week answers *"¿trabajan el sábado?"*; the agenda
    answers whether a visit fits.
    """
    conversation_id = _seed(
        monkeypatch,
        saturday_open=False,
        window=[{"days": [1, 2, 3, 4, 5], "open": "09:00", "close": "18:00"}],
    )
    replies = _turn(
        conversation_id, question, f"wamid.continuity.closed.{abs(hash(question))}"
    )

    assert replies == [expected]
