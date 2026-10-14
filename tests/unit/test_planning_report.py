"""The planning session report is assembled from the captured items (S8)."""

from app.services.planning import build_report, handoff_candidate, minimum_met, report_gaps


def test_report_is_substantive_markdown_not_topic_json():
    cortex = {
        "topic": "Presupuesto 2026",
        "decisions": [{"title": "Stack", "content": "Use Postgres"}],
        "notes": [
            {"kind": "objective", "content": "Decide the 2026 budget"},
            {"kind": "risk", "content": "Vendor lock-in"},
            {"kind": "next_step", "content": "Draft the numbers"},
        ],
    }

    report = build_report(cortex)

    assert report.startswith("# Planning session report: Presupuesto 2026")
    assert "Decide the 2026 budget" in report
    assert "**Stack** — Use Postgres" in report
    assert "Vendor lock-in" in report
    assert "Draft the numbers" in report
    assert '{"topic"' not in report


def test_report_marks_empty_sections():
    report = build_report({"topic": "Vacío"})

    assert "## Decisions" in report
    assert "_Not captured._" in report


def test_gaps_list_the_missing_checklist_items():
    cortex = {
        "topic": "Presupuesto 2026",
        "decisions": [{"title": "Stack", "content": "Use Postgres"}],
        "notes": [{"kind": "objective", "content": "Decide the 2026 budget"}],
    }

    assert report_gaps(cortex) == ["risks", "next_steps"]
    assert minimum_met(cortex) is True


def test_minimum_is_the_objective_and_at_least_one_decision():
    assert minimum_met({"topic": "T", "notes": [{"kind": "objective", "content": "O"}]}) is False
    assert minimum_met({"topic": "T"}) is False
    assert report_gaps({"topic": "T"}) == ["objective", "decisions", "risks", "next_steps"]


def test_report_includes_a_gaps_section():
    report = build_report({"topic": "T"})

    assert "## Gaps" in report
    assert "Objective" in report


def test_handoff_is_offered_only_with_a_captured_next_step():
    assert handoff_candidate({"topic": "T"}) is None
    assert handoff_candidate({"topic": "T", "notes": [{"kind": "objective", "content": "O"}]}) is None
    assert handoff_candidate({"topic": "T", "notes": [{"kind": "next_step", "content": "   "}]}) is None

    proposal = handoff_candidate(
        {
            "topic": "T",
            "notes": [
                {"kind": "next_step", "content": "Draft the numbers"},
                {"kind": "objective", "content": "O"},
                {"kind": "next_step", "content": "Review them"},
            ],
        }
    )

    assert proposal == {"actions": ["Draft the numbers", "Review them"]}

