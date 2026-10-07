from types import SimpleNamespace

import pytest

from app.models import InternalChatThread, User
from app.services import agent_chat


def test_create_thread_persists_validated_project_and_audits_namespace(monkeypatch):
    audit = {}

    def agent_context(session, proyecto, *, owner_id=None):
        assert proyecto == "My Project"
        assert owner_id == 3
        return SimpleNamespace(slug="my-project")

    monkeypatch.setattr(agent_chat.projects, "agent_context", agent_context)
    monkeypatch.setattr(
        agent_chat,
        "record_audit",
        lambda session, **kwargs: audit.update(kwargs),
    )

    class Session:
        def add(self, thread):
            thread.id = 7

        def flush(self):
            pass

    thread = agent_chat.create_thread(Session(), SimpleNamespace(id=3, username="admin"), proyecto="My Project")

    assert thread.proyecto == "my-project"
    assert audit["after"] == {"proyecto": "my-project"}


def test_thread_project_authorization_uses_thread_column(monkeypatch):
    authorization = object()
    calls = []

    def agent_context(session, proyecto, *, owner_id=None):
        calls.append((proyecto, owner_id))
        return authorization

    monkeypatch.setattr(agent_chat.projects, "agent_context", agent_context)
    thread = InternalChatThread(
        user_id=1,
        proyecto="bound-project",
        assistant_state={"legacy_project": "legacy-other"},
    )

    assert agent_chat._thread_project_authorization(object(), thread) is authorization
    assert calls == [("bound-project", 1)]


def test_create_thread_defaults_to_default_without_project_validation(monkeypatch):
    calls = []
    monkeypatch.setattr(
        agent_chat.projects,
        "agent_context",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr(agent_chat, "record_audit", lambda *args, **kwargs: None)

    class Session:
        def add(self, thread):
            thread.id = 7

        def flush(self):
            pass

    session = Session()
    admin = SimpleNamespace(id=3, username="admin", role=SimpleNamespace(value="admin"))
    implicit = agent_chat.create_thread(session, admin)
    explicit = agent_chat.create_thread(
        session, admin, proyecto="default"
    )

    assert implicit.proyecto == "default"
    assert explicit.proyecto == "default"
    assert calls == []


def test_create_thread_rejects_default_for_tecnico_before_persistence(monkeypatch):
    class Session:
        def __init__(self):
            self.added = []

        def add(self, thread):
            self.added.append(thread)

    session = Session()
    user = SimpleNamespace(id=3, username="tecnico", role=SimpleNamespace(value="tecnico"))
    with pytest.raises(ValueError, match="business-shared"):
        agent_chat.create_thread(session, user, proyecto="default")
    assert session.added == []


def test_create_thread_rejects_unknown_project_before_persistence(monkeypatch):
    audit_calls = []

    def reject_project(session, proyecto, *, owner_id=None):
        raise ValueError(f"project {proyecto!r} is not active")

    monkeypatch.setattr(agent_chat.projects, "agent_context", reject_project)
    monkeypatch.setattr(
        agent_chat,
        "record_audit",
        lambda *args, **kwargs: audit_calls.append((args, kwargs)),
    )

    class Session:
        def __init__(self):
            self.added = []

        def add(self, thread):
            self.added.append(thread)

        def flush(self):
            pass

    session = Session()
    with pytest.raises(ValueError, match="not active"):
        agent_chat.create_thread(session, SimpleNamespace(id=3, username="admin"), proyecto="unknown")

    assert session.added == []
    assert audit_calls == []


def test_thread_project_authorization_rejects_project_that_no_longer_resolves(monkeypatch):
    def reject_project(session, proyecto, *, owner_id=None):
        raise ValueError(f"project {proyecto!r} is not active")

    monkeypatch.setattr(agent_chat.projects, "agent_context", reject_project)
    thread = InternalChatThread(user_id=1, proyecto="archived-project")

    with pytest.raises(ValueError, match="not active"):
        agent_chat._thread_project_authorization(object(), thread)


def test_agent_turn_authorization_failure_uses_turn_failure_path_and_publishes(monkeypatch):
    thread = SimpleNamespace(
        id=1,
        proyecto="archived-project",
        assistant_state={},
        current_plan=None,
        active_run_id=None,
    )
    user = SimpleNamespace(id=2, username="admin", role=SimpleNamespace(value="admin"))
    message = SimpleNamespace(
        id=3,
        thread_id=1,
        content="hello",
        status="received",
        error=None,
        completed_at=None,
        assistant_metadata={"run_id": "run-1"},
    )

    class Session:
        def get(self, model, identifier):
            return {InternalChatThread: thread, User: user}.get(model)

        def scalar(self, _query):
            return message

        def flush(self):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    publishes = []
    monkeypatch.setattr(agent_chat, "_session_factory", lambda: (lambda: Session()))
    monkeypatch.setattr(
        agent_chat,
        "_thread_project_authorization",
        lambda *_args: (_ for _ in ()).throw(ValueError("project is not active")),
    )
    monkeypatch.setattr(agent_chat, "publish_live", lambda *args, **kwargs: publishes.append((args, kwargs)))
    monkeypatch.setattr(agent_chat, "record_audit", lambda *args, **kwargs: None)

    agent_chat.run_agent_turn(
        thread_id=thread.id,
        run_id="run-1",
        user_id=user.id,
        attachment_ids=[],
        sdb_requested=None,
    )

    assert message.status == "failed"
    assert message.error == "El agente no pudo procesar este mensaje. Reinténtalo."
    assert thread.assistant_state["stage"] == "failed"
    assert thread.assistant_state["execution_status"] == "failed"
    assert thread.assistant_state["live"]["status"] == "failed"
    assert publishes[-1][1] == {"status": "failed", "preview": None}


def test_agent_turn_derives_project_authorization_from_thread(monkeypatch):
    authorization = object()
    captured = {}
    monkeypatch.setattr(agent_chat, "_thread_project_authorization", lambda session, thread: authorization)
    monkeypatch.setattr(agent_chat, "assemble_context", lambda *args, **kwargs: {"meta": {}})
    monkeypatch.setattr(agent_chat, "compact_session", lambda *args, **kwargs: {})
    monkeypatch.setattr(agent_chat, "publish_live", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_chat, "_generate_thread_title", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_chat, "stage_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_chat, "record_audit", lambda *args, **kwargs: None)

    def run_assistant(**kwargs):
        captured["project_authorization"] = kwargs["project_authorization"]
        return {"status": "completed", "response": "ok"}

    monkeypatch.setattr(agent_chat, "run_assistant", run_assistant)

    class Session:
        def scalars(self, query):
            return []

        def add(self, value):
            pass

        def flush(self):
            pass

    thread = SimpleNamespace(id=1, assistant_state={}, current_plan=None, active_run_id=None)
    user = SimpleNamespace(id=2, username="admin", role=SimpleNamespace(value="admin"))
    message = SimpleNamespace(id=3, assistant_metadata={"run_id": "run-1"}, content="hello")

    agent_chat._run_agent_turn_session(Session(), thread, user, message, [], None)

    assert captured["project_authorization"] is authorization
