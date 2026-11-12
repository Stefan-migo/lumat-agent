"""Data-growing assistant tool results stay within their share of the evidence budget."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.chat.assistant.nodes import _LISTING_EVIDENCE_SHARE, _TOOL_EVIDENCE_LIMIT, _render_tool_evidence
from app.chat.assistant.tools.registry import MAX_ITEMS, execute_tool


@pytest.mark.parametrize("tool_name", ["conversations.list", "conversations.search"])
def test_conversation_tool_projection_stays_within_evidence_share_and_has_no_raw_rows(monkeypatch, tool_name):
    conversations = [
        (
            SimpleNamespace(
                id=index, wa_phone=f"+569{index:08d}", state=SimpleNamespace(value="bot"),
                summary="Needs repair",
                last_message_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                captured_data={"private": "must not leak"},
            ),
            f"Ana {index}",
        )
        for index in range(MAX_ITEMS)
    ]
    monkeypatch.setattr(
        "app.services.conversations.list_conversations",
        lambda _session, _query, limit: conversations[:limit],
    )
    result = execute_tool(
        SimpleNamespace(), tool_name,
        {"limit": MAX_ITEMS, **({"query": "Customer"} if tool_name.endswith("search") else {})},
        role="admin",
    )
    rendered = _render_tool_evidence({"tool_results": [{
        "tool": tool_name, "status": "completed", "arguments": {}, "result": result["result"],
    }]})

    assert len(rendered) <= _TOOL_EVIDENCE_LIMIT * _LISTING_EVIDENCE_SHARE
    assert result["result"]["fields"] == [
        "id", "customer_name", "phone", "state", "summary", "last_message_at",
    ]
    assert len(result["result"]["rows"]) == MAX_ITEMS
    serialized = json.dumps(result["result"])
    assert "captured_data" not in serialized
    assert "must not leak" not in serialized
    assert not any(hasattr(row, "__table__") for row in result["result"]["rows"])
