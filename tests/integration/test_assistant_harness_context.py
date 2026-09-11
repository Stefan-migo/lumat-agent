"""Context assembly contracts for the panel assistant harness."""

from types import SimpleNamespace

from app.chat.assistant import nodes
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
