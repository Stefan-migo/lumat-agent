"""Database-backed runtime coverage for the Cortex session contracts."""

from sqlalchemy import select

from app.chat.assistant.nodes import cortex_session_gate
from app.db import SessionLocal
from app.models import InternalChatThread, Memory, User
from app.services import agent_chat


def _active_cortex(slug: str = "runtime-review") -> dict:
    return {
        "slug": slug,
        "topic": "Runtime review",
        "status": "active",
        "opened_at": "2026-09-13T12:00:00Z",
        "closed_at": None,
        "turn_index": 0,
        "next_decision": None,
        "last_class": None,
        "decision_keys": [],
        "report_key": None,
        "handoff": {"status": "none", "sdb_phase": None},
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


def test_two_cortex_decisions_survive_thread_reload(monkeypatch):
    user_id, thread_id = _thread_with_active_cortex()

    def run_cortex_turn(**kwargs):
        from app.chat.assistant.nodes import cortex_session_turn

        return cortex_session_turn({
            "thread_id": kwargs["thread_id"],
            "content": kwargs["content"],
            "session": kwargs["session"],
            "cortex_session": kwargs["cortex_session"],
        })

    monkeypatch.setattr(agent_chat, "run_assistant", run_cortex_turn)

    with SessionLocal() as session:
        user = session.get(User, user_id)
        thread = session.get(InternalChatThread, thread_id)
        first = agent_chat.submit_message(session, thread, user, "We will use provider A")
        assert first.status == "processed"
        second = agent_chat.submit_message(session, thread, user, "We will keep the existing contract")
        assert second.status == "processed"
        session.commit()

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        assert thread.assistant_state["cortex_session"]["turn_index"] == 2
        keys = {
            "cortex-session/runtime-review:decision:1",
            "cortex-session/runtime-review:decision:2",
        }
        memories = list(
            session.scalars(
                select(Memory).where(
                    Memory.entity_id == f"thread:{thread_id}",
                    Memory.topic_key.in_(keys),
                )
            )
        )

        assert {memory.topic_key for memory in memories} == keys
        assert thread.assistant_state["cortex_session"]["decision_keys"] == [
            "cortex-session/runtime-review:decision:1",
            "cortex-session/runtime-review:decision:2",
        ]
        assert thread.assistant_state["cortex_session"]["turn_index"] == 2


def test_cortex_failure_preserves_active_session_after_thread_reload(monkeypatch):
    user_id, thread_id = _thread_with_active_cortex()

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        thread.assistant_state = {
            **thread.assistant_state,
            "cortex_session": {
                **thread.assistant_state["cortex_session"],
                "slug": "failure-recovery",
                "decision_keys": ["cortex-session/failure-recovery:decision:1"],
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
        assert state["cortex_session"]["decision_keys"] == [
            "cortex-session/failure-recovery:decision:1"
        ]


def test_missing_cortex_flag_reaches_gate_and_routes_normal():
    result = cortex_session_gate({"content": "continue planning"})

    assert result == {
        "cortex_route": "normal",
        "cortex_rejection": "invalid-session",
    }
