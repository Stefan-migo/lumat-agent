from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.users import hash_password


def _thread(session, username, *, updated_at, status="open", proyecto="default"):
    owner = User(username=username, password_hash=hash_password("pass"), role="admin")
    session.add(owner)
    session.flush()
    thread = InternalChatThread(
        user_id=owner.id, proyecto=proyecto, status=status, updated_at=updated_at
    )
    session.add(thread)
    session.flush()
    session.add_all([
        InternalChatMessage(thread_id=thread.id, author="admin", content="Necesitamos una estrategia"),
        InternalChatMessage(thread_id=thread.id, author="agent", content="Podemos priorizar el seguimiento"),
    ])
    session.flush()
    return thread


def test_sweep_captures_idle_thread_once_and_checkpoint_makes_second_tick_noop(monkeypatch):
    from app.chat.assistant import memory_capture
    from app.services import tukulpan

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        thread = _thread(session, "capture-sweep-once", updated_at=now - timedelta(minutes=121))
        thread_id = thread.id
        checkpoints = {}
        writes = []
        extraction_payloads = []
        monkeypatch.setattr(tukulpan, "get_by_key", lambda _session, **kw: checkpoints.get(kw["topic_key"]))
        monkeypatch.setattr(tukulpan, "upsert", lambda _session, **kw: checkpoints.setdefault(kw["topic_key"], kw))
        monkeypatch.setattr(memory_capture, "extract_thread_candidates", lambda *, state, payload: extraction_payloads.append(payload) or [{"topic_key": "agent:seguimiento", "titulo": "Seguimiento", "contenido": "Priorizar el seguimiento semanal con el equipo.", "tipo": "pattern"}])
        monkeypatch.setattr("app.chat.assistant.tools.registry.execute_tool", lambda *args, **kwargs: writes.append((args, kwargs)) or {"status": "completed", "result": {"written": True}})
        monkeypatch.setattr("app.chat.assistant.nodes._cost_snapshot", lambda *_args: {"mode": "normal"})

        assert memory_capture.sweep_idle_threads(session, now=now) == 1
        assert memory_capture.sweep_idle_threads(session, now=now) == 0
        assert len(writes) == 1
        args, kwargs = writes[0]
        assert args[1:3] == ("memory.write", {"topic_key": "agent:seguimiento", "titulo": "Seguimiento", "contenido": "Priorizar el seguimiento semanal con el equipo.", "tipo": "pattern"})
        assert kwargs == {"whitelist": {"memory.write"}, "cost_allowed": True, "role": "admin", "trusted_thread_id": thread_id, "owner_id": thread.user_id, "proyecto": "default"}
        assert extraction_payloads[0] == {"thread_tail": [{"author": "admin", "content": "Necesitamos una estrategia"}, {"author": "agent", "content": "Podemos priorizar el seguimiento"}]}
        checkpoint = next(iter(checkpoints.values()))
        assert checkpoint["scope"] == "panel"
        assert checkpoint["entity_id"] == f"thread:{thread_id}"
        assert checkpoint["topic_key"] == f"assistant-capture:{thread_id}:{max(message.id for message in session.query(InternalChatMessage).filter_by(thread_id=thread_id))}"
        assert checkpoint["origin_thread_id"] == str(thread_id)
        assert checkpoint["proyecto"] == "default"
        session.rollback()


def test_sweep_ignores_recently_updated_threads(monkeypatch):
    from app.chat.assistant import memory_capture

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _thread(session, "capture-sweep-recent", updated_at=now - timedelta(minutes=119))
        monkeypatch.setattr(memory_capture, "extract_thread_candidates", lambda **_: (_ for _ in ()).throw(AssertionError("extraction must not run")))
        assert memory_capture.sweep_idle_threads(session, now=now) == 0
        session.rollback()


def test_sweep_does_not_extract_when_cost_budget_is_blocked(monkeypatch):
    from app.chat.assistant import memory_capture

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        _thread(session, "capture-sweep-blocked", updated_at=now - timedelta(minutes=121))
        monkeypatch.setattr("app.chat.assistant.nodes._cost_snapshot", lambda *_args: {"mode": "blocked"})
        monkeypatch.setattr(memory_capture, "extract_thread_candidates", lambda **_: (_ for _ in ()).throw(AssertionError("blocked budget must not extract")))
        assert memory_capture.sweep_idle_threads(session, now=now) == 0
        session.rollback()


def test_sweep_checkpoints_thread_even_when_no_candidate_is_durable(monkeypatch):
    from app.chat.assistant import memory_capture
    from app.services import tukulpan

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        thread = _thread(session, "capture-sweep-empty", updated_at=now - timedelta(minutes=121))
        checkpoints = {}
        calls = []
        monkeypatch.setattr(tukulpan, "get_by_key", lambda _session, **kw: checkpoints.get(kw["topic_key"]))
        monkeypatch.setattr(tukulpan, "upsert", lambda _session, **kw: checkpoints.setdefault(kw["topic_key"], kw))
        monkeypatch.setattr(memory_capture, "extract_thread_candidates", lambda **_: calls.append("extract") or [])
        monkeypatch.setattr("app.chat.assistant.nodes._cost_snapshot", lambda *_args: {"mode": "normal"})

        assert memory_capture.sweep_idle_threads(session, now=now) == 1
        assert memory_capture.sweep_idle_threads(session, now=now) == 0
        assert calls == ["extract"]
        assert len(checkpoints) == 1
        session.rollback()


def test_idle_thread_extractor_uses_idle_mode_and_shared_strict_validation(monkeypatch):
    from app.chat.assistant import memory_capture

    seen = []
    monkeypatch.setattr(
        memory_capture,
        "_planner_call",
        lambda messages, state, key: seen.append((messages, state, key)) or (
            '{"memories":[{"topic_key":"agent:seguimiento","titulo":"Seguimiento","contenido":"Priorizar el seguimiento semanal con el equipo.","tipo":"pattern"},{"topic_key":"bad","titulo":"Inválido","contenido":"x","tipo":"summary"}]}',
            None,
            None,
        ),
    )
    result = memory_capture.extract_thread_candidates(
        state={"thread_id": 7},
        payload={"thread_tail": [{"author": "admin", "content": "Necesitamos una estrategia"}]},
    )
    assert len(result) == 1
    assert result[0]["topic_key"] == "agent:seguimiento"
    assert seen[0][0][1]["content"] == '{"mode": "idle_thread", "thread_tail": [{"author": "admin", "content": "Necesitamos una estrategia"}]}'
    assert seen[0][2] == "memory_capture"


def test_worker_calls_idle_sweep_once_and_sweep_failure_is_nonfatal(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from app.ops import worker

    calls = []
    monkeypatch.setattr(worker, "session_scope", lambda: nullcontext(SimpleNamespace(flush=lambda: None)))
    monkeypatch.setattr(worker, "evaluate_time_triggers", lambda *_: None)
    monkeypatch.setattr(worker, "_claim", lambda *_: [])
    monkeypatch.setattr(
        "app.chat.assistant.memory_capture.sweep_idle_threads",
        lambda *_args, **_kwargs: calls.append("swept") or (_ for _ in ()).throw(RuntimeError("capture issue")),
    )
    assert worker.run_cycle() == 0
    assert calls == ["swept"]
