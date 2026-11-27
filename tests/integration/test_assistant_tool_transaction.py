"""Transaction boundaries at the assistant tool dispatch.

The production failure (2026-11-27, thread 65) was a tool that read and then waited longer
than the database's idle-transaction guard: PostgreSQL killed the turn's connection and the
turn only noticed at the next node boundary, as a `PendingRollbackError` on an audit INSERT.
An end-to-end test cannot model that with a compressed guard — the guard kills any session
that waits, including the tool's own — so the invariant is pinned here, at the seam that
decides it: a tool classified as external I/O commits the turn's work (and its own start
row) before the handler runs.
"""

from app.chat.assistant.tools.registry import TOOL_REGISTRY
from app.models import UserRole


class _SpySession:
    """A session that reports whether the turn holds an open transaction."""

    def __init__(self, events: list):
        self.events = events
        self.active = True

    def in_transaction(self) -> bool:
        return self.active

    def commit(self) -> None:
        self.events.append("commit")
        self.active = False

    def add(self, obj) -> None:
        self.events.append(("add", getattr(obj, "action", None)))
        self.active = True


def _tool_state(session, tool: str, arguments: dict) -> dict:
    return {
        "session": session,
        "thread_id": 7,
        "run_id": "run-tool-boundary",
        "actor": "Stefan",
        "actor_role": UserRole.ADMIN.value,
        "user_id": 1,
        "content": "hacelo",
        "guardrails": {"cost_allowed": True},
        "plan": {
            "kind": "tool", "tool": tool, "arguments": arguments, "summary": "probar",
            "requires_approval": False, "follow_up": False, "success_criterion": None,
        },
        "effective": {},
        "attachments": [],
    }


def _plan_and_dispatch(monkeypatch, tool: str, arguments: dict) -> list:
    from app.chat.assistant import nodes as assistant_nodes

    events: list = []
    session = _SpySession(events)

    def fake_execute_tool(*_args, **_kwargs):
        events.append("tool")
        return {"tool": tool, "status": "ok"}

    monkeypatch.setattr(assistant_nodes, "execute_tool", fake_execute_tool)
    assistant_nodes.execute(_tool_state(session, tool, arguments))
    return events


def test_external_io_tool_classification_is_explicit():
    marked = {name for name, definition in TOOL_REGISTRY.items() if definition.external_io}
    assert marked == {
        "chatbot.simulate", "chatbot.eval_regression", "web.search", "web.fetch", "kb.retrieve",
    }
    assert not TOOL_REGISTRY["customers.list"].external_io


def test_marked_tool_releases_the_turn_session_before_dispatch(monkeypatch):
    """S1+S3: the wait happens with no transaction of the turn open, and the start row is durable."""
    events = _plan_and_dispatch(monkeypatch, "chatbot.simulate", {"messages": ["hola"]})

    assert events.index(("add", "internal_chat.execution_started")) < events.index("commit")
    assert events.index("commit") < events.index("tool")


def test_unmarked_tool_keeps_the_turn_transaction_for_the_next_boundary(monkeypatch):
    """The existing contract: a cheap tool records only its completed row, after the handler."""
    events = _plan_and_dispatch(monkeypatch, "customers.list", {"limit": 1})

    assert ("add", "internal_chat.execution_started") not in events
    assert "commit" not in events
    assert "tool" in events
