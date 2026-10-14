"""The planning session report is assembled from the captured items (S8)."""

from app.services.planning import build_report


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
