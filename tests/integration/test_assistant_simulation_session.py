"""The chatbot simulation must not run on the assistant turn's session.

`chatbot.simulate` drives the real chatbot graph — provider calls, potentially for minutes —
through whatever session it is given. On the turn's session that wait held the assistant's
transaction, and the database's idle guard killed the turn (production, 2026-11-27).
"""

from app.db import SessionLocal
from app.models import InternalChatThread, User, UserRole
from app.services.chat_simulation import simulate
from app.services.users import hash_password


def test_simulation_does_not_commit_the_assistant_turn_session(migrated_db, monkeypatch):
    from app.chat import graph

    monkeypatch.setattr(graph, "run_conversation", lambda _session, _message: [])
    with SessionLocal() as turn_session:
        user = User(
            username="simulation-session-isolation", password_hash=hash_password("pass"),
            role=UserRole.ADMIN,
        )
        turn_session.add(user)
        turn_session.flush()
        thread = InternalChatThread(user_id=user.id)
        turn_session.add(thread)
        turn_session.flush()
        thread_id = thread.id

        simulate(turn_session, ["consulta"])

        # The turn's work stays uncommitted: nothing it staged is visible to another connection.
        with SessionLocal() as observer:
            assert observer.get(InternalChatThread, thread_id) is None
        assert turn_session.in_transaction()
        turn_session.rollback()


def test_simulate_runs_the_conversation_on_its_own_session(migrated_db, monkeypatch):
    from app.chat import graph

    seen: list = []

    def record_session(session, _message):
        seen.append(session)
        return []

    monkeypatch.setattr(graph, "run_conversation", record_session)
    with SessionLocal() as turn_session:
        turn_session.add(User(
            username="simulation-own-session", password_hash=hash_password("pass"),
            role=UserRole.ADMIN,
        ))
        simulate(turn_session, ["consulta"])

    assert len(seen) == 1
    assert seen[0] is not turn_session
