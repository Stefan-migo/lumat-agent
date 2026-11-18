"""The project approval decision contract: what is published, answered, and bound."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.approval import (
    ApprovalDecisionError,
    approved_project_binding,
    consume_approval,
    issue_approval,
    validate_execution,
    validate_project_decision,
)
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool

CANDIDATE = {"slug": "gas", "name": "Gas", "similarity": 0.91}
CREATE_ARGUMENTS = {"slug": "gas-new", "name": "Gas New", "purpose": "gas service"}


def _issued(tool="project.create", arguments=None, candidates=None) -> dict:
    return issue_approval({"tool": tool, "arguments": arguments or CREATE_ARGUMENTS}, candidates=candidates)


def _bound_consumed(tool="project.create", arguments=None, candidates=None, decision=None) -> dict:
    """A consumed approval exactly as `approve_plan` leaves it after an answered decision."""
    arguments = arguments or CREATE_ARGUMENTS
    approval = _issued(tool, arguments, candidates)
    assert consume_approval(approval, approval["token"]) is True
    binding = approved_project_binding(approval, decision)
    approval["project_payload"] = binding["payload"]
    approval["project_sha256"] = binding["sha256"]
    return approval


def test_create_approval_offers_only_consent_before_the_tool_ran():
    """S1: before the tool runs there is no conflict to inspect, so the owner is asked to proceed."""
    approval = _issued()

    assert approval["project_decision"] == {
        "operation": "create",
        "options": ["create_distinct"],
        "candidates": [],
    }


def test_create_approval_offers_the_conflict_the_service_found():
    """S4: the informed gate offers exactly the candidate the server found."""
    approval = _issued(candidates=[CANDIDATE])

    assert approval["project_decision"]["options"] == ["selected_slug", "create_anyway"]
    assert approval["project_decision"]["candidates"] == [CANDIDATE]


def test_find_approval_offers_only_the_candidates_it_can_select():
    """S3: a find approval is answerable only with one of its own candidates."""
    approval = _issued("project.find", {"query": "gas service"}, [CANDIDATE])

    assert approval["project_decision"] == {
        "operation": "find",
        "options": ["selected_slug"],
        "candidates": [CANDIDATE],
    }


def test_find_approval_without_candidates_publishes_no_question():
    approval = _issued("project.find", {"query": "gas service"})

    assert "project_decision" not in approval


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("project.rename", {"project": "gas", "name": "Gas Service"}),
        ("project.archive", {"project": "gas"}),
        ("project.merge", {"source": "gas", "target": "ops"}),
        ("settings.update", {"key": "tone.style", "value": "formal"}),
    ],
)
def test_tools_that_take_no_decision_publish_no_question(tool, arguments):
    """S6: the tools that never read a decision are not asked to answer one."""
    assert "project_decision" not in issue_approval({"tool": tool, "arguments": arguments})


def test_unanswered_decision_is_refused_and_nothing_is_consumed():
    """S2: an unanswered approval stays pending and says so in its own words."""
    approval = _issued()

    with pytest.raises(ApprovalDecisionError, match="project decision required"):
        validate_project_decision(approval["project_decision"], None)
    with pytest.raises(ApprovalDecisionError, match="project decision required"):
        validate_project_decision(approval["project_decision"], {})
    assert approval["status"] == "pending"


@pytest.mark.parametrize(
    ("candidates", "decision", "reason"),
    [
        ([], {"create_anyway": True}, "not offered"),
        ([], {"selected_slug": "gas"}, "not offered"),
        ([], {"create_distinct": False}, "not offered"),
        ([CANDIDATE], {"selected_slug": "other"}, "did not offer"),
        ([CANDIDATE], {"create_distinct": True}, "not offered"),
        ([CANDIDATE], {"selected_slug": "gas", "create_anyway": True}, "not offered"),
    ],
)
def test_a_decision_the_approval_did_not_offer_is_refused(candidates, decision, reason):
    """S2, S3: the answer must belong to the question this approval asked."""
    approval = _issued(candidates=candidates)

    with pytest.raises(ApprovalDecisionError, match=reason):
        validate_project_decision(approval["project_decision"], decision)


def test_only_the_bound_decision_passes_execution_validation():
    """S1: the digest proves the write that runs is the one the owner answered."""
    approval = _issued()
    assert consume_approval(approval, approval["token"]) is True
    plan = {"tool": "project.create", "arguments": CREATE_ARGUMENTS}

    # Consumed but unanswered: the execution boundary must still refuse it.
    assert validate_execution(plan, approval) is True
    assert validate_execution({**plan, "project_payload": approval["project_payload"]}, approval) is True

    binding = approved_project_binding(approval, {"create_distinct": True})
    approval["project_payload"] = binding["payload"]
    approval["project_sha256"] = binding["sha256"]

    assert validate_execution({**plan, "project_payload": binding["payload"]}, approval) is True
    with pytest.raises(ToolValidationError, match="approval does not match exact tool arguments"):
        execute_tool(
            SimpleNamespace(),
            "project.create",
            CREATE_ARGUMENTS,
            approval={**approval, "project_sha256": "0" * 64},
            owner_id=1,
            role="admin",
        )


def test_execute_project_create_refuses_an_unanswered_approval(monkeypatch):
    """S1, S2: the reported production failure, reproduced at the boundary."""
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.create",
        lambda *args, **kwargs: pytest.fail("the service must not run"),
    )
    approval = _issued()
    assert consume_approval(approval, approval["token"]) is True

    with pytest.raises(ToolValidationError, match="missing an explicit decision"):
        execute_tool(
            SimpleNamespace(), "project.create", CREATE_ARGUMENTS, approval=approval, owner_id=1, role="admin"
        )


def test_execute_project_create_uses_the_bound_decision(monkeypatch):
    """S1: the answered decision travels to the service unchanged."""
    seen = []

    def create(session, slug, name, purpose, *, owner_id=None, _approval=None):
        seen.append(_approval)
        return SimpleNamespace(slug=slug)

    monkeypatch.setattr("app.chat.assistant.tools.registry.projects.create", create)
    approval = _bound_consumed(decision={"create_distinct": True})

    result = execute_tool(
        SimpleNamespace(), "project.create", CREATE_ARGUMENTS, approval=approval, owner_id=1, role="admin"
    )

    assert result["status"] == "completed"
    assert seen[0].operation == "create"
    assert seen[0].decision == {"create_distinct": True}


def test_execute_project_find_refuses_a_decision_that_is_not_a_selection(monkeypatch):
    """S3: find only reads a namespace the owner selected."""
    monkeypatch.setattr(
        "app.chat.assistant.tools.registry.projects.find",
        lambda *args, **kwargs: pytest.fail("the service must not run"),
    )
    approval = _bound_consumed("project.find", {"query": "gas service"}, [CANDIDATE], {"create_distinct": True})

    with pytest.raises(ToolValidationError, match="missing an explicit decision"):
        execute_tool(
            SimpleNamespace(),
            "project.find",
            {"query": "gas service"},
            approval=approval,
            owner_id=1,
            role="admin",
        )


def test_execute_project_find_selects_the_offered_candidate(monkeypatch):
    """S3: the selected slug is the one the service receives."""
    from app.services.projects import ProjectCandidate, ProjectResult

    seen = []

    def find(session, query, *, owner_id=None, _approval=None):
        seen.append(_approval)
        if _approval is None:
            return ProjectResult(None, [ProjectCandidate("gas", "Gas", 0.91)], requires_approval=True)
        return ProjectResult("gas", [ProjectCandidate("gas", "Gas", 0.91)])

    monkeypatch.setattr("app.chat.assistant.tools.registry.projects.find", find)
    approval = _bound_consumed("project.find", {"query": "gas service"}, [CANDIDATE], {"selected_slug": "gas"})

    result = execute_tool(
        SimpleNamespace(),
        "project.find",
        {"query": "gas service"},
        approval=approval,
        owner_id=1,
        role="admin",
    )

    assert result["status"] == "completed"
    assert result["result"]["project"] == "gas"
    assert seen[0].decision == {"selected_slug": "gas"}
