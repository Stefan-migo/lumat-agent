"""Context assembly contracts for the panel assistant harness."""

from types import SimpleNamespace

from app.chat.assistant import nodes
from app.chat.assistant.graph import run_assistant
from app.services.agent_chat import assemble_context


def test_context_keeps_history_in_created_order_without_memory_projection():
    messages = [
        SimpleNamespace(id=2, author="agent", content="second"),
        SimpleNamespace(id=1, author="admin", content="first"),
    ]
    result = assemble_context(None, 7, messages=messages, attachments=[])

    assert [item["content"] for item in result["items"]] == [
        "first", "second",
    ]
    assert result["meta"]["message_ids"] == [1, 2]
    assert "tukulpan_ids" not in result["meta"]
    assert result["meta"]["scope"] == "panel"
    assert result["meta"]["entity_id"] == "thread:7"


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


def test_assembly_ignores_panel_memory_rows_and_does_not_search(monkeypatch):
    monkeypatch.setattr(
        "app.services.tukulpan.hybrid_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("implicit search")),
    )
    monkeypatch.setattr(
        "app.services.tukulpan.list_for_entity",
        lambda session, *, scope, entity_id: [
            SimpleNamespace(id=1, contenido="panel fact", pin=True),
        ],
    )

    result = assemble_context(SimpleNamespace(execute=lambda *args: None), 7, messages=[], attachments=[])

    assert result["items"] == []
    assert result["meta"]["estimated_tokens"] == 0
    assert result["meta"]["truncated"] is False
    assert "tukulpan_ids" not in result["meta"]


def test_panel_memory_loader_is_deleted():
    assert not hasattr(nodes, "load_panel_context")


def test_assistant_graph_carries_context_metadata_into_evidence():
    context = {
        "items": [{"source": "history", "id": 1, "content": "fact"}],
        "meta": {
            "scope": "panel",
            "entity_id": "thread:7",
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
