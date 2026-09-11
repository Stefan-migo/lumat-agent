"""Context assembly contracts for the panel assistant harness."""

from types import SimpleNamespace

from app.chat.assistant import nodes
from app.chat.assistant.graph import run_assistant
from app.services.agent_chat import assemble_context


def test_context_keeps_history_in_created_order_and_pinned_first(monkeypatch):
    messages = [
        SimpleNamespace(id=2, author="agent", content="second"),
        SimpleNamespace(id=1, author="admin", content="first"),
    ]
    monkeypatch.setattr(nodes, "load_panel_context", lambda session, thread_id: {
        "pinned": [{"id": "pin-1", "content": "pinned fact"}],
        "panel": [{"id": "panel-1", "content": "panel fact"}],
    })

    result = assemble_context(None, 7, messages=messages, attachments=[])

    assert [item["content"] for item in result["items"]] == [
        "pinned fact", "panel fact", "first", "second",
    ]
    assert result["meta"]["message_ids"] == [1, 2]
    assert result["meta"]["tukulpan_ids"] == ["pin-1", "panel-1"]


def test_context_truncates_attachments_after_history():
    messages = [SimpleNamespace(id=1, author="admin", content="history")]
    attachments = [
        {"id": 10, "filename": "one.txt", "content": "attachment one"},
        {"id": 11, "filename": "two.txt", "content": "attachment two"},
    ]

    result = assemble_context(None, 7, messages=messages, attachments=attachments, budget=5)

    assert [item["content"] for item in result["items"]] == ["history", "attachment o"]
    assert result["meta"]["attachment_ids"] == [10]
    assert result["meta"]["truncated"] is True


def test_context_retains_newest_history_rows_when_history_exceeds_budget():
    messages = [
        SimpleNamespace(id=1, author="admin", content="old message"),
        SimpleNamespace(id=2, author="agent", content="new message"),
    ]

    result = assemble_context(None, 7, messages=messages, attachments=[], budget=3)

    assert [item["content"] for item in result["items"]] == ["new message"]
    assert result["meta"]["message_ids"] == [2]


def test_tukulpan_seam_is_panel_and_pinned_only(monkeypatch):
    seen = {}

    def fake_loader(session, thread_id):
        seen["args"] = (session, thread_id)
        return {"pinned": [{"id": "pin"}], "panel": [{"id": "panel"}], "private": [{"id": "secret"}]}

    monkeypatch.setattr(nodes, "load_panel_context", fake_loader)
    result = assemble_context("session", 9, messages=[], attachments=[])

    assert seen["args"] == ("session", 9)
    assert result["meta"]["tukulpan_ids"] == ["pin", "panel"]
    assert "secret" not in str(result)


def test_panel_projection_uses_canonical_scope_and_preserves_newest_rows(monkeypatch):
    seen = {}

    def fake_list(session, *, scope, entity_id):
        seen.update(scope=scope, entity_id=entity_id)
        return [
            SimpleNamespace(id=3, contenido="new", pin=False),
            SimpleNamespace(id=2, contenido="pinned", pin=True),
            SimpleNamespace(id=1, contenido="old", pin=False),
        ]

    monkeypatch.setattr("app.services.tukulpan.list_for_entity", fake_list)

    result = nodes.load_panel_context(SimpleNamespace(execute=lambda *args: None), 12)

    assert seen == {"scope": "panel", "entity_id": "thread:12"}
    assert [row["id"] for row in result["pinned"] + result["panel"]] == ["2", "3", "1"]


def test_assembly_does_not_search_and_reports_fixed_budget_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.services.tukulpan.hybrid_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("implicit search")),
    )
    monkeypatch.setattr(nodes, "load_panel_context", lambda session, thread_id: {
        "pinned": [{"id": "pin-1", "content": "pinned"}],
        "panel": [{"id": "panel-1", "content": "x" * 20_000}],
    })

    result = assemble_context(None, 7, messages=[], attachments=[])

    assert result["meta"]["estimated_tokens"] <= 4_000
    assert result["meta"]["truncated"] is True
    assert result["meta"]["tukulpan_ids"] == ["pin-1"]


def test_panel_loader_never_falls_back_to_hybrid_search(monkeypatch):
    monkeypatch.setattr(
        "app.services.tukulpan.hybrid_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("implicit search")),
    )
    monkeypatch.setattr(
        "app.services.tukulpan.list_for_entity",
        lambda session, *, scope, entity_id: [
            SimpleNamespace(id=7, contenido="panel fact", pin=False)
        ],
    )

    result = nodes.load_panel_context(SimpleNamespace(execute=lambda *args: None), 42)

    assert result == {"pinned": [], "panel": [{"id": "7", "content": "panel fact"}]}


def test_assistant_graph_carries_projection_metadata_into_evidence():
    context = {
        "items": [{"source": "tukulpan", "id": "memory-1", "content": "fact"}],
        "meta": {
            "tukulpan_ids": ["memory-1"],
            "message_ids": [],
            "attachment_ids": [],
            "estimated_tokens": 1,
            "truncated": False,
        },
    }

    result = run_assistant(
        thread_id=7,
        user_id=1,
        content="hello",
        run_id="run-1",
        session=None,
        context=context,
    )

    assert result["context_meta"] == context["meta"]
    assert result["evidence"][-1]["context_meta"] == context["meta"]
