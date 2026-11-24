"""The harness measures the bot with a configured window, not a feature off.

Measured 2026-11-23 (`odd/tasks/chatbot-conv-eval.md` L22): the evaluation database
held **zero settings rows**, so `hours.schedule` read its `[]` default. With no
window configured there is no deterministic availability answer at all — the turn
falls back to the model, the model takes the `kb_miss` path, and
`real-disponibilidad-dias` fails G6 with a sentence no version of the bot can fix.

These tests pin both halves of that: with no window the question has no
deterministic answer, and with the seeded window it has exactly the sentence the
gate is asking for. The values copied into the harness are production's, read from
`settings` on 2026-11-24, so the instrument stops measuring a capability that is
turned off.
"""

from app.db import session_scope
from app.services.settings import get_hours_schedule, get_hours_timezone, set_setting

WINDOW = [{"days": [1, 2, 3, 4, 5, 6, 7], "open": "00:00", "close": "23:59"}]
QUESTION = "¿Tienen hora disponible esta semana?"
NO_RESTRICTION_REPLY = "Las visitas se agendan según la disponibilidad de los técnicos."


def _conv_eval():
    """Import the script module without running it."""
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root / "scripts") not in sys.path:
        sys.path.insert(0, str(repo_root / "scripts"))
    import conv_eval

    return conv_eval


def _hours_reply() -> str | None:
    """The deterministic answer to the corpus question, straight from the graph seam."""
    from app.chat.nodes import configured_answers
    from app.chat.state import ConversationState

    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56900000000",
        turn=2,
        intent="consulta",
        window=[{"id": 1, "text": QUESTION}],
    )
    with session_scope() as session:
        return configured_answers.hours_reply(session, state)


def test_no_window_means_no_deterministic_answer():
    """The state the evaluation database was measured in, reproduced on purpose."""
    with session_scope() as session:
        set_setting(session, "hours.schedule", [])

    assert _hours_reply() is None


def test_the_harness_seeds_the_window_production_runs_with():
    module = _conv_eval()

    effective = module.seed_harness_settings()

    assert effective["hours.schedule"] == WINDOW
    with session_scope() as session:
        assert get_hours_schedule(session) == WINDOW
        assert get_hours_timezone(session) == "America/Santiago"


def test_the_seeded_window_answers_the_question_the_gate_asks():
    """`real-disponibilidad-dias` needs one of: horario, disponibilidad, sábado,
    semana. The configured answer carries `disponibilidad`, and that is the whole
    difference between a failing gate and a bot that answered."""
    module = _conv_eval()
    module.seed_harness_settings()

    reply = _hours_reply()

    assert reply == NO_RESTRICTION_REPLY
    assert "disponibilidad" in reply


def test_seeding_a_second_time_writes_no_second_audit_row():
    """The seed runs on every run, including the ones that share a database: a
    repeated write would make the tag's history unreadable."""
    from sqlalchemy import func, select

    from app.models import AuditLog

    module = _conv_eval()
    module.seed_harness_settings()

    def schedule_writes() -> int:
        with session_scope() as session:
            return session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.entity_id == "hours.schedule")
            )

    before = schedule_writes()
    module.seed_harness_settings()

    assert schedule_writes() == before
