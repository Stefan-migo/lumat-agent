"""Retired planning report persistence does not affect agent memory services."""

from app.services import tukulpan


def test_planning_report_writer_is_removed():
    assert not hasattr(tukulpan, "write_agent_report")
