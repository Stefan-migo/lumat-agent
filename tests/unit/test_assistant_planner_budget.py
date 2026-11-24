"""Planner budget and direction: the chain must see the file it read and still reach the write."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from app.chat.assistant.budgets import PROJECT_READ_FILE_PAGE_LIMIT, _TOOL_EVIDENCE_LIMIT
from app.chat.assistant.nodes import (
    MAX_ASSISTANT_TOOL_STEPS,
    _audit_arguments,
    _coalesce_file_reads,
    _render_tool_evidence,
    _tool_step_limit,
    guardrails,
    tool_loop_head,
)
from app.services.agent_chat import assemble_context

FILE_BYTES = 5_899


def _read_result(text: str, offset: int, next_offset: int | None, *, file_id: int = 3) -> dict:
    return {
        "tool": "read_project_file",
        "status": "completed",
        "arguments": {"file_id": file_id, "offset": offset, "limit": len(text)},
        "result": {
            "file_id": file_id, "filename": "herramientas-probadas-hilo-84.md", "kind": "md",
            "text": text, "chars": len(text), "offset": offset, "next_offset": next_offset,
        },
    }


def _paged_reads(page_chars: int = 5_000, pages: int = 2, *, file_id: int = 3) -> list[dict]:
    """The same file read in several steps, each page distinguishable by its letter."""
    results: list[dict] = []
    offset = 0
    for index in range(pages):
        text = chr(ord("A") + index) * page_chars
        next_offset = offset + page_chars if index < pages - 1 else None
        results.append(_read_result(text, offset, next_offset, file_id=file_id))
        offset += page_chars
    return results


def _one_page_per_read() -> list[dict]:
    """Two steps over one file, the shape production burned six steps on."""
    return _paged_reads()


def test_two_pages_of_one_file_stay_visible_together():
    """S1: paging must not make the earlier half vanish from the evidence."""
    results = _one_page_per_read()

    rendered = _render_tool_evidence({"tool_results": results})

    assert "A" * 64 in rendered, "the first page was evicted from the evidence"
    assert "B" * 64 in rendered, "the second page is missing"
    assert len(rendered) <= _TOOL_EVIDENCE_LIMIT


def test_coalescing_keeps_single_reads_untouched():
    """S1 preserve: one read of one file renders exactly as before."""
    single = [_read_result("contenido", 0, None)]

    assert _coalesce_file_reads(single) == single


def test_coalescing_does_not_merge_different_files():
    """S1: two files are two documents, however small."""
    results = [
        _read_result("uno", 0, None, file_id=3),
        _read_result("dos", 0, None, file_id=10),
    ]

    merged = _coalesce_file_reads(results)

    assert len(merged) == 2
    assert [item["result"]["text"] for item in merged] == ["uno", "dos"]


def test_evidence_budget_holds_a_real_project_file():
    """S2: the measured 5,899-byte file fits in one page, and the budget holds the page."""
    assert PROJECT_READ_FILE_PAGE_LIMIT >= FILE_BYTES
    assert _TOOL_EVIDENCE_LIMIT >= 12_000

    whole_file = _read_result("F" * FILE_BYTES, 0, None)
    rendered = _render_tool_evidence({"tool_results": [whole_file]})

    assert rendered.count("F") >= FILE_BYTES, "the whole page must survive the evidence budget"


def test_a_document_bigger_than_the_budget_is_cut_at_the_end_not_the_middle():
    """S1: when the joined document does not fit, the head survives and the tail is marked."""
    results = _paged_reads(page_chars=9_000, pages=2)

    rendered = _render_tool_evidence({"tool_results": results})

    assert "A" * 64 in rendered
    assert len(rendered) <= _TOOL_EVIDENCE_LIMIT
    assert "characters dropped" in rendered, "the cut must be labeled, not silent"


def test_a_write_request_keeps_its_last_step_for_the_write():
    """S3: a chain of reads cannot consume the step a requested write needs."""
    reads = _one_page_per_read()

    state = {
        "content": "escribe el resumen final en el archivo del proyecto",
        "tool_results": reads,
        "tool_steps": _tool_step_limit() - 1,
        "session": None,
        "thread_id": 1,
        "plan": {"kind": "tool", "tool": "read_project_file", "arguments": {"file_id": 3}, "follow_up": True},
    }

    result = tool_loop_head(state)

    assert result["status"] == "completed"
    assert result.get("execution_stall") == "write_pending_after_reads"


def test_a_read_only_request_may_use_every_step():
    """S3 preserve: a request that is not a write keeps the full chain."""
    state = {
        "content": "resumime el archivo del proyecto",
        "tool_results": _one_page_per_read(),
        "tool_steps": _tool_step_limit() - 1,
        "session": None,
        "thread_id": 1,
        "plan": {"kind": "tool", "tool": "read_project_file", "arguments": {"file_id": 3}, "follow_up": True},
    }

    assert tool_loop_head(state)["status"] == "planned"


def test_a_third_read_of_the_same_file_is_refused_even_with_a_new_offset():
    """S4: pagination changes the offset, so identity of the call must not be the guard."""
    reads = _one_page_per_read()

    state = {
        "content": "escribe el resumen final",
        "tool_results": reads,
        "tool_steps": 2,
        "session": None,
        "thread_id": 1,
        "plan": {
            "kind": "tool", "tool": "read_project_file",
            "arguments": {"file_id": 3, "offset": 100, "limit": 50}, "follow_up": True,
        },
        "guardrails": {},
        "planner": {"valid": True},
        "effective": {"tools_whitelist": ["read_project_file"], "skills_index": []},
    }

    result = guardrails(state)

    assert result["status"] == "responding"
    assert result["execution_stall"] == "repeated_file_read"
    assert result["plan"]["tool"] is None


def test_a_second_read_of_the_same_file_is_still_allowed():
    """S4 preserve: two pages are legitimate; the guard starts at the third."""
    state = {
        "content": "resumime el archivo",
        "tool_results": _one_page_per_read()[:1],
        "tool_steps": 1,
        "session": None,
        "thread_id": 1,
        "plan": {"kind": "tool", "tool": "read_project_file", "arguments": {"file_id": 3, "offset": 9_000}, "follow_up": True},
        "guardrails": {},
        "planner": {"valid": True},
        "effective": {"tools_whitelist": ["read_project_file"], "skills_index": []},
    }

    result = guardrails(state)

    assert result["status"] != "responding"
    assert result.get("execution_stall") != "repeated_file_read"


def test_step_limit_comes_from_settings(monkeypatch):
    """S6: the cap is tunable without a release."""
    monkeypatch.setattr(
        "app.chat.assistant.nodes.get_settings",
        lambda: SimpleNamespace(assistant_tool_step_limit=11),
    )

    assert _tool_step_limit() == 11
    assert MAX_ASSISTANT_TOOL_STEPS == 8


def test_step_limit_falls_back_when_settings_cannot_be_read(monkeypatch):
    """S6 preserve: a state built without settings keeps a working bound."""

    def _boom():
        raise RuntimeError("no settings")

    monkeypatch.setattr("app.chat.assistant.nodes.get_settings", _boom)

    assert _tool_step_limit() == MAX_ASSISTANT_TOOL_STEPS


def test_attachments_are_injected_before_history():
    """S7: the file the operator just attached outranks the thread history."""
    attachment = {"content": "contenido del adjunto", "id": 9, "filename": "informe.pdf"}
    history = [
        SimpleNamespace(id=1, author="admin", content="mensaje viejo uno", created_at=None),
        SimpleNamespace(id=2, author="admin", content="mensaje viejo dos", created_at=None),
    ]

    context = assemble_context(
        None, thread_id=1, messages=history, attachments=[attachment], budget=25
    )

    sources = [item["source"] for item in context["items"]]
    assert sources[0] == "attachment"
    assert sources[1:] == ["history", "history"]
    assert "contenido del adjunto" in context["items"][0]["content"]
    assert 'id="9"' in context["items"][0]["content"]
    assert "informe.pdf" in context["items"][0]["content"]


def test_a_truncated_attachment_says_so():
    """S7: a planner reading a partial document must know it is partial."""
    attachment = {"content": "X" * 400, "id": 9, "filename": "informe.pdf"}

    context = assemble_context(None, thread_id=1, messages=[], attachments=[attachment], budget=10)

    assert "truncado" in context["items"][0]["content"]
    assert context["meta"]["truncated"] is True


def test_audit_trace_carries_a_digest_and_cursor_keys_but_no_content():
    """S8: a repeat must be visible in production without storing the operator's data."""
    arguments = {"file_id": 3, "offset": 0, "limit": 2000, "query": "Marcela Fuentes", "phone": "+56912345678"}

    trace = _audit_arguments(arguments)

    assert trace["file_id"] == 3 and trace["offset"] == 0 and trace["limit"] == 2000
    assert trace["arguments_sha256"] == hashlib.sha256(
        json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    assert "query" not in trace and "phone" not in trace
    assert "Marcela" not in json.dumps(trace) and "+56912345678" not in json.dumps(trace)
