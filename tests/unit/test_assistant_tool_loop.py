"""Contracts for narrating a completed panel assistant tool call."""

from types import SimpleNamespace

from app.chat.assistant.graph import build_assistant_graph
from app.chat.assistant.nodes import execute


def _tool_state(**overrides):
    state = {
        "thread_id": 7,
        "run_id": "run-tool-loop",
        "content": "Find Ana",
        "plan": {
            "kind": "tool",
            "tool": "customers.search",
            "arguments": {"query": "Ana"},
            "requires_approval": False,
        },
        "guardrails": {"cost_allowed": True},
        "evidence": [],
    }
    state.update(overrides)
    return state


def _streaming_client(calls, text="Ana is a customer"):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: calls.append(kwargs)
                or [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])]
            )
        )
    )


def test_completed_tool_routes_to_responder_without_a_cycle():
    graph = build_assistant_graph()
    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("execute_tool", "respond_stream") in edges
    assert ("respond_stream", "execute_tool") not in edges


def test_completed_tool_executes_once_and_final_response_is_narrated(monkeypatch):
    calls = []
    handler_calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: handler_calls.append(args) or {
            "tool": "customers.search",
            "status": "completed",
            "result": [{"id": 1, "name": "Ana"}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls))

    first = execute(_tool_state())
    final = execute({**_tool_state(), **first, "on_token": lambda _token: None})

    assert len(handler_calls) == 1
    assert len(calls) == 1
    assert final["response"] == "Ana is a customer"
    assert final["response"] != "Tool customers.search completed."
    assert "Ana" in calls[0]["messages"][-1]["content"]
    assert '"status": "completed"' not in calls[0]["messages"][-1]["content"]


def test_tool_evidence_is_bounded_and_prompt_statement_is_truthful(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.chat.assistant.nodes.execute_tool",
        lambda *args, **kwargs: {
            "tool": "customers.search",
            "status": "completed",
            "result": [{"name": "Ana", "notes": "x" * 10_000}],
        },
    )
    monkeypatch.setattr("app.chat.assistant.nodes.record_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls))

    first = execute(_tool_state())
    execute({**_tool_state(), **first, "on_token": lambda _token: None})

    prompt = calls[0]["messages"][-1]["content"]
    evidence = prompt.split("<tool_evidence>", 1)[1].split("</tool_evidence>", 1)[0]
    assert evidence
    assert len(evidence) <= 4_000
    assert "Ana" in evidence
    assert "Tool customers.search completed." not in prompt
    assert "already run" in prompt


def test_no_tool_prompt_keeps_non_invoking_statement(monkeypatch):
    calls = []
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: _streaming_client(calls, "Text reply"))

    execute(
        {
            "thread_id": 7,
            "run_id": "run-no-tool",
            "content": "Hello",
            "plan": {"kind": "respond", "tool": None, "arguments": {}, "requires_approval": False},
            "context": {"items": []},
            "on_token": lambda _token: None,
        }
    )

    prompt = calls[0]["messages"][-1]["content"]
    assert "cannot invoke" in prompt
    assert "must not emit tool-call markup" in prompt
