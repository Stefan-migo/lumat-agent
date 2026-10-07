"""Database-backed runtime coverage for the Cortex session contracts."""

from app.db import SessionLocal
from app.models import InternalChatThread, User
from app.services import agent_chat


def _active_cortex(slug: str = "runtime-review") -> dict:
    return {
        "slug": slug,
        "topic": "Runtime review",
        "status": "active",
        "opened_at": "2026-09-13T12:00:00Z",
        "closed_at": None,
        "report_key": None,
    }


def _thread_with_active_cortex() -> tuple[int, int]:
    with SessionLocal() as session:
        user = User(username="cortex-runtime-admin", password_hash="test", role="admin")
        session.add(user)
        session.flush()
        thread = InternalChatThread(
            user_id=user.id,
            assistant_state={"cortex_session": _active_cortex()},
        )
        session.add(thread)
        session.commit()
        return user.id, thread.id


def test_cortex_failure_preserves_active_session_after_thread_reload(monkeypatch):
    user_id, thread_id = _thread_with_active_cortex()

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.assistant_state = {
            **thread.assistant_state,
            "cortex_session": {
                **thread.assistant_state["cortex_session"],
                "slug": "failure-recovery",
            },
        }
        session.commit()

    def fail_run(**kwargs):
        raise RuntimeError("stream interrupted")

    monkeypatch.setattr(agent_chat, "run_assistant", fail_run)

    with SessionLocal() as session:
        user = session.get(User, user_id)
        thread = session.get(InternalChatThread, thread_id)
        message = agent_chat.submit_message(session, thread, user, "Continue planning")
        assert message.status == "failed"
        session.commit()

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        state = thread.assistant_state
        assert state["cortex_session"]["status"] == "active"
        assert state["stage"] == "failed"
        assert state["recoverable"] is True
        assert state["cortex_session"]["slug"] == "failure-recovery"
        assert set(state["cortex_session"]) == {
            "slug", "topic", "status", "opened_at", "closed_at", "report_key",
        }
