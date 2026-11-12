"""Data-growing assistant tool results stay within their share of the evidence budget."""

import json
from datetime import datetime, timedelta, timezone
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


# --- S5: every tool whose payload grows with data stays inside its share of the box -------------
#
# A listing or bulk tool may spend the listing share so two of them coexist in a turn; a detail tool
# may spend the detail share because it is the turn's answer. Shapes come from the real handlers over
# their service seams where the seam is trivial, and from the tool's own bounds where the payload is
# produced by a bounded reader. Each listing is measured at its DEFAULT page: that is the call a model
# makes without thinking, so it must fit whole. A wider page is the caller's choice and degrades by
# naming the steps it omitted. Adding a data-growing tool means adding its row here.
from app.chat.assistant.nodes import _DETAIL_EVIDENCE_SHARE  # noqa: E402
from app.chat.assistant.tools.fetch import MAX_PAYLOAD  # noqa: E402
from app.chat.assistant.tools.search import (  # noqa: E402
    MAX_RESULTS,
    MAX_SNIPPET_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
)
from app.chat.assistant.tools.registry import ProjectReadFileArgs  # noqa: E402


def _one_result(tool, payload):
    return _render_tool_evidence({"tool_results": [
        {"tool": tool, "status": "completed", "arguments": {}, "result": payload},
    ]})


def _project_row(index):
    return SimpleNamespace(
        id=index, owner_id=1, slug=f"project-{index}", name=f"Project {index}",
        purpose="p" * 400, purpose_embedding=[0.0] * 384,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), archived_at=None,
    )


def test_project_listing_stays_within_the_listing_share(monkeypatch):
    from app.chat.assistant.tools.registry import projects

    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.list",
        lambda _session, owner_id=None: [_project_row(index) for index in range(MAX_ITEMS)],
    )
    result = execute_tool(SimpleNamespace(), "project.list", {}, role="admin", owner_id=1)["result"]

    assert len(result) == 10
    assert set(result[0]) == {"id", "slug", "name", "purpose", "created_at"}
    assert len(_one_result("project.list", result)) <= _TOOL_EVIDENCE_LIMIT * _LISTING_EVIDENCE_SHARE


def test_project_find_projects_the_resolved_project_and_keeps_its_envelope(monkeypatch):
    from app.services.projects import ProjectCandidate, ProjectResult

    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.find",
        lambda *_args, **_kwargs: ProjectResult(
            project=_project_row(1),
            candidates=[ProjectCandidate(f"project-{index}", f"Project {index}", 0.9) for index in range(3)],
            requires_approval=False,
        ),
    )
    result = execute_tool(SimpleNamespace(), "project.find", {"query": "project"}, role="admin", owner_id=1)["result"]

    assert set(result) == {"project", "candidates", "requires_approval"}
    assert set(result["project"]) == {"id", "slug", "name", "purpose", "created_at"}
    assert len(_one_result("project.find", result)) <= _TOOL_EVIDENCE_LIMIT * _LISTING_EVIDENCE_SHARE


def test_project_file_listing_stays_within_the_listing_share(monkeypatch):
    files = [
        SimpleNamespace(
            id=index, filename=f"file-{index}.pdf", content_type="application/pdf", size=10_000,
            status="ready", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), url="https://example.test",
        )
        for index in range(MAX_ITEMS)
    ]
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.project_files.owned_project",
        lambda *_args, **_kwargs: SimpleNamespace(id=1, slug="project"),
    )
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.project_files.list_project_files",
        lambda _session, _project_id: files,
    )
    result = execute_tool(SimpleNamespace(), "list_project_files", {}, role="admin", owner_id=1)["result"]

    assert len(result["files"]) == 10
    assert len(_one_result("list_project_files", result)) <= _TOOL_EVIDENCE_LIMIT * _LISTING_EVIDENCE_SHARE


def test_a_project_file_page_stays_within_the_detail_share():
    """The page the tool may ask for, serialized with its cursor ahead of the text, still fits."""
    page_limit = ProjectReadFileArgs(file_id=1).limit
    payload = {
        "file_id": 1,
        "filename": "contrato.pdf",
        "kind": "pdf",
        "chars": page_limit * 4,
        "offset": 0,
        "next_offset": page_limit,
        "truncated": True,
        "limit": page_limit,
        "text": "x" * page_limit,
    }

    assert len(_one_result("read_project_file", payload)) <= _TOOL_EVIDENCE_LIMIT * _DETAIL_EVIDENCE_SHARE


def test_web_search_at_its_result_bound_stays_within_the_detail_share():
    results = [
        {
            "title": "t" * MAX_TITLE_LENGTH,
            "url": "https://example.test/" + "u" * (MAX_URL_LENGTH - 21),
            "snippet": "s" * MAX_SNIPPET_LENGTH,
        }
        for _ in range(MAX_RESULTS)
    ]

    # A search result set is the source for a research turn, like a fetched page: the reader bounds it
    # at 4,000 on its own, and the detail share is what a single source may spend.
    assert len(_one_result("web.search", results)) <= _TOOL_EVIDENCE_LIMIT * _DETAIL_EVIDENCE_SHARE


def test_a_fetched_page_at_its_own_bound_stays_within_the_detail_share():
    payload = {"url": "https://example.test/page", "title": "A page", "text": "x" * MAX_PAYLOAD}

    assert len(_one_result("web.fetch", payload)) <= _TOOL_EVIDENCE_LIMIT * _DETAIL_EVIDENCE_SHARE


def test_customer_search_and_upcoming_appointments_stay_within_the_listing_share(monkeypatch):
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.customers.search_customers",
        lambda _session, _query, _limit: [
            SimpleNamespace(id=index, name=f"Customer {index}", state="active") for index in range(MAX_ITEMS)
        ],
    )
    customers_result = execute_tool(SimpleNamespace(), "customers.search", {"query": "a"}, role="admin")["result"]
    assert len(_one_result("customers.search", customers_result)) <= _TOOL_EVIDENCE_LIMIT * _LISTING_EVIDENCE_SHARE

    appointments = [
        SimpleNamespace(
            id=index, service="instalación de aire acondicionado split muro",
            starts_at=datetime.now(timezone.utc) + timedelta(hours=index + 1),
            ends_at=datetime.now(timezone.utc) + timedelta(hours=index + 2),
            status=SimpleNamespace(value="booked"), customer_id=index, case_id=index,
            technician_id=index, duration_minutes=60, timezone="America/Santiago",
            local_start=datetime(2026, 1, 1), technician_state=None,
            technician_state_at=None, created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
        )
        for index in range(MAX_ITEMS)
    ]
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.scheduling.list_for_range",
        lambda *_args, **_kwargs: [(appointment, None, None, None, None) for appointment in appointments],
    )
    appointments_result = execute_tool(SimpleNamespace(), "appointments.upcoming", {}, role="admin")["result"]
    assert len(_one_result("appointments.upcoming", appointments_result)) <= _TOOL_EVIDENCE_LIMIT * _LISTING_EVIDENCE_SHARE
