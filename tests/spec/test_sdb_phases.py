"""Assistant graph and database dependency contracts."""

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.chat.assistant.graph import build_assistant_graph
def test_graph_has_no_sdb_phase_nodes_and_preserves_normal_path():
    graph = build_assistant_graph()

    assert not any(name.startswith("sdb_") for name in graph.nodes)
    assert all(name in graph.nodes for name in (
        "plan_llm", "guardrails", "execute_tool", "tool_loop_head",
        "verify_effects", "respond_stream",
    ))


def test_db_commit_uncertainty_is_bounded_without_retry(monkeypatch):
    from app.panel import deps

    class Session:
        commits = 0
        rollbacks = 0

        def commit(self):
            self.commits += 1
            raise ConnectionError("database connection lost")

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            pass

    session = Session()
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)
    database = deps.get_db()
    next(database)

    with pytest.raises(HTTPException) as caught:
        next(database)

    assert caught.value.status_code == 500
    assert "recovery" in caught.value.detail
    assert session.commits == 1
    assert session.rollbacks == 1


def test_db_preserves_request_validation_errors(monkeypatch):
    from app.panel import deps

    class Session:
        rollbacks = 0
        closes = 0

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closes += 1

    session = Session()
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)
    database = deps.get_db()
    next(database)
    validation_error = RequestValidationError([{"loc": ("body",), "msg": "invalid", "type": "value_error"}])

    with pytest.raises(RequestValidationError) as caught:
        database.throw(validation_error)

    assert caught.value is validation_error
    assert session.rollbacks == 1
    assert session.closes == 1
